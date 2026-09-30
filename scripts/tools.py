"""Small Docker entrypoint; each operation owns its data and report."""

import argparse
import base64
import csv
import hashlib
import json
import os
import secrets
import shutil
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path("/workspace")
API_URL = os.getenv("API_URL", "http://localhost:8088/api/v1")
COLLECTIONS = ("heyface_people_v1", "heyface_animals_dinov2_sift_v1")
DEMO_NAMESPACE = uuid.UUID("8b916070-ac91-4bc7-953b-c0fe03465b29")


def client(token=None):
    token = token or (ROOT / ".secrets/demo-token.txt").read_text().strip()
    return httpx.Client(base_url=API_URL, headers={"Authorization": "Bearer " + token}, timeout=90)


def image(name):
    return base64.b64encode((ROOT / "web/public/brand" / name).read_bytes()).decode()


def demo():
    with client() as api:
        payload = {
            "person_id": str(uuid.uuid5(DEMO_NAMESPACE, "person")),
            "image_base64": image("heyface.png"),
            "person": {
                "name": "Alex Exemplo",
                "sex": "unspecified",
                "birth_date": "1990-05-18",
                "state": "ES",
                "city": "Vitória",
                "consent": True,
            },
        }
        response = api.post("/people", json=payload)
        response.raise_for_status()
        payload = {
            "animal_id": str(uuid.uuid5(DEMO_NAMESPACE, "animal")),
            "image_base64": image("animal.png"),
            "animal": {"name": "Luna Exemplo", "species": "cat", "consent": True},
            "single_subject_confirmed": True,
        }
        api.post("/animals", json=payload).raise_for_status()
    print(
        "Dois cadastros de exemplo estão prontos. Abra a interface, "
        "conecte sua chave e use uma imagem de exemplo."
    )


def smoke():
    registry_path = ROOT / ".secrets/access/keys.json"
    credentials = {name: secrets.token_urlsafe(32) for name in ("first", "second", "reader")}
    hashes = {
        name: hashlib.sha256(token.encode()).hexdigest() for name, token in credentials.items()
    }
    tenant = "smoke-" + uuid.uuid4().hex[:12]
    registry = json.loads(registry_path.read_text())
    for name, key in hashes.items():
        registry[key] = {
            "tenant": tenant if name != "second" else tenant + "-other",
            "scopes": ["read"] if name == "reader" else ["read", "write", "delete"],
        }

    def publish(data):
        temporary = registry_path.with_suffix(".pending")
        temporary.write_text(json.dumps(data))
        temporary.chmod(0o644)
        temporary.replace(registry_path)

    publish(registry)
    checks = []
    identity, animal_id = str(uuid.uuid4()), str(uuid.uuid4())
    calibration_path = ROOT / ".local/calibrations" / tenant / "cat.json"
    first, second, reader = [client(credentials[name]) for name in ("first", "second", "reader")]

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        print("PASS", name, flush=True)

    try:
        check(httpx.get(API_URL + "/people").status_code == 401, "authentication required")
        check(reader.post("/people", json={}).status_code == 403, "read-only access")
        check(first.get("/health/ready").status_code == 200, "services and models ready")
        payload = {
            "person_id": identity,
            "image_base64": image("heyface.png"),
            "person": {
                "name": "João Exemplo",
                "sex": "unspecified",
                "birth_date": "1990-01-01",
                "state": "ES",
                "city": "Vitória",
                "consent": True,
            },
        }
        response = first.post("/people", json=payload)
        check(
            response.status_code == 201,
            "real face enrollment " + str(response.status_code),
        )
        result = first.post(
            "/search", json={"image_base64": payload["image_base64"], "filters": {}}
        )
        check(
            result.status_code == 200 and bool(result.json()["matches"]),
            "empty JSON filter object",
        )
        import io

        from PIL import Image

        blank = io.BytesIO()
        Image.new("RGB", (160, 160), "white").save(blank, format="PNG")
        no_face = base64.b64encode(blank.getvalue()).decode()
        for method in ("facenet", "sface"):
            invalid = first.post("/search", json={"image_base64": no_face, "method": method})
            check(
                invalid.status_code == 422 and invalid.json()["error"]["code"] == "no_face",
                method + " rejects image without face",
            )
        for method in ("facenet", "sface"):
            query = {
                "image_base64": payload["image_base64"],
                "method": method,
                "exact": True,
                "filters": {"city": "vitoria", "name": "joao"},
            }
            response = first.post("/search", json=query)
            response.raise_for_status()
            matches = response.json()["matches"]
            check(
                bool(matches)
                and matches[0]["person"]["id"] == identity
                and matches[0]["score"] > 0.99,
                method + " actual self-match and normalized filters",
            )
            query["filters"] = {"state": "RJ"}
            check(
                first.post("/search", json=query).json()["matches"] == [],
                method + " filters before ranking",
            )
        check(
            second.get("/people/" + identity).status_code == 404,
            "cross-tenant detail isolation",
        )
        check(
            second.get("/people", headers={"X-Tenant-Id": tenant}).json()["items"] == [],
            "spoofed tenant ignored",
        )
        check(
            second.delete("/people/" + identity).status_code == 404,
            "cross-tenant delete isolation",
        )
        check(
            first.get(
                "/people",
                params={"birth_date_from": "1989-01-01", "birth_date_to": "1991-01-01"},
            ).json()["items"][0]["id"]
            == identity,
            "birth date range",
        )
        for files in (
            {"image_base64": (None, payload["image_base64"])},
            {
                "image": (
                    "sample.png",
                    (ROOT / "web/public/brand/heyface.png").read_bytes(),
                    "image/png",
                )
            },
        ):
            result = first.post("/search", files=files)
            check(
                result.status_code == 200 and bool(result.json()["matches"]),
                "multipart image transport",
            )
        for locale, message in [("en", "base64"), ("pt-BR", "base64")]:
            bad = first.post(
                "/search",
                json={"image_base64": "not-valid!"},
                headers={"Accept-Language": locale},
            )
            check(
                bad.status_code == 422 and message in bad.json()["error"]["message"],
                "localized validation " + locale,
            )
        check(
            first.post(
                "/people",
                json=payload | {"person": payload["person"] | {"consent": False}},
            ).status_code
            == 422,
            "explicit enrollment consent",
        )
        animal_payload = {
            "animal_id": animal_id,
            "animal": {"name": "Example", "species": "cat", "consent": True},
            "image_base64": image("animal.png"),
            "single_subject_confirmed": True,
        }
        check(
            first.post("/animals", json=animal_payload).status_code == 201,
            "animal pattern enrollment",
        )
        animal_query = {
            "image_base64": animal_payload["image_base64"],
            "species": "cat",
            "single_subject_confirmed": True,
        }
        matches = first.post("/animals/search", json=animal_query).json()["matches"]
        check(
            bool(matches)
            and matches[0]["animal"]["id"] == animal_id
            and matches[0]["score"] > 0.99,
            "animal actual self-match",
        )
        check(
            second.post("/animals/search", json=animal_query).json()["matches"] == [],
            "animal tenant isolation",
        )
        check(
            first.post("/animals/search", json=animal_query | {"species": "dog"}).json()["matches"]
            == [],
            "animal species isolation",
        )
        check(
            first.post("/animals/search", json=animal_query | {"method": "wildfusion"}).status_code
            == 409,
            "fusion requires calibration",
        )
        from app.domain.representations import ANIMAL

        calibration_path.parent.mkdir(parents=True, exist_ok=True)
        calibration_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "model": ANIMAL.version,
                    "species": "cat",
                    "global_weight": 0.5,
                    "global_curve": {"x": [-1, 1], "y": [0, 1]},
                    "local_curve": {"x": [0, 256], "y": [0, 1]},
                }
            )
        )
        fusion = first.post("/animals/search", json=animal_query | {"method": "wildfusion"})
        check(
            fusion.status_code == 200 and fusion.json()["matches"][0]["animal"]["id"] == animal_id,
            "fusion reranking with isolated contract fixture",
        )
        check(first.delete("/people/" + identity).status_code == 204, "person deletion")
        check(
            first.get("/people/" + identity).status_code == 404,
            "deleted person no longer retrievable",
        )
        check(first.delete("/animals/" + animal_id).status_code == 204, "animal deletion")
    finally:
        if calibration_path.exists():
            calibration_path.unlink()
        # Only records and credentials created by this test are cleaned up.
        first.delete("/people/" + identity)
        first.delete("/animals/" + animal_id)
        for api in (first, second, reader):
            api.close()
        registry = json.loads(registry_path.read_text())
        for key in hashes.values():
            registry.pop(key, None)
        publish(registry)
    (ROOT / ".local/smoke.json").write_text(
        json.dumps({"checks": checks, "count": len(checks)}, indent=2)
    )
    print(f"{len(checks)} integration checks passed.")


def benchmark(points=3000, queries=40):
    import numpy as np

    from app.config import settings
    from app.retrieval.qdrant import Qdrant

    database = Qdrant(settings)
    name = "heyface_benchmark_" + uuid.uuid4().hex[:12]
    path = "/collections/" + name
    dimension, neighbors = 512, 10
    rng = np.random.default_rng(42)
    vectors = rng.normal(size=(points, dimension)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    database.request(
        "PUT",
        path,
        json={
            "vectors": {"size": dimension, "distance": "Cosine"},
            "hnsw_config": {"m": 16, "ef_construct": 128, "full_scan_threshold": 10},
            "optimizers_config": {"indexing_threshold": 1000},
        },
    )
    for offset in range(0, points, 100):
        database.request(
            "PUT",
            path + "/points?wait=true",
            json={
                "points": [
                    {"id": index, "vector": vectors[index].tolist()}
                    for index in range(offset, min(points, offset + 100))
                ]
            },
        )
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        info = database.request("GET", path)
        if info.get("indexed_vectors_count", 0) >= points:
            break
        time.sleep(1)
    query_vectors = rng.normal(size=(queries, dimension)).astype(np.float32)
    report = {
        "collection": name,
        "points": points,
        "dimensions": dimension,
        "k": neighbors,
        "queries": queries,
        "seed": 42,
        "indexed_vectors": info.get("indexed_vectors_count", 0),
        "dataset": "synthetic_normal_distribution",
        "results": [],
    }

    def run(vector, exact, ef):
        start = time.perf_counter()
        result = database.request(
            "POST",
            path + "/points/query",
            json={
                "query": vector.tolist(),
                "limit": neighbors,
                "with_payload": False,
                "with_vector": False,
                "params": {"exact": exact, "hnsw_ef": ef},
            },
        )
        return {p["id"] for p in result["points"]}, (time.perf_counter() - start) * 1000

    ground_truth, exact_times = zip(
        *(run(vector, True, 128) for vector in query_vectors), strict=True
    )
    report["exact_p95_ms"] = float(np.percentile(exact_times, 95))
    for ef in (32, 64, 128, 256):
        observed = [run(vector, False, ef) for vector in query_vectors]
        recall = np.mean(
            [
                len(ids & expected) / neighbors
                for (ids, _), expected in zip(observed, ground_truth, strict=True)
            ]
        )
        times = [elapsed for _, elapsed in observed]
        report["results"].append(
            {
                "hnsw_ef": ef,
                "recall_at_k": float(recall),
                "p50_ms": float(np.percentile(times, 50)),
                "p95_ms": float(np.percentile(times, 95)),
            }
        )
    report["scope"] = (
        "Index behavior only; does not measure recognition accuracy or compare databases."
    )
    target = ROOT / ".local/benchmark.json"
    target.write_text(json.dumps(report, indent=2))
    database.close()
    print(json.dumps(report, indent=2))


def backup():
    from app.config import settings
    from app.retrieval.qdrant import Qdrant

    stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    directory = ROOT / ".local/backups" / stamp
    directory.mkdir(parents=True, mode=0o700)
    database = Qdrant(settings)
    for collection in COLLECTIONS:
        snapshot = database.request("POST", f"/collections/{collection}/snapshots")
        response = database.client.get(f"/collections/{collection}/snapshots/{snapshot['name']}")
        response.raise_for_status()
        (directory / (collection + ".snapshot")).write_bytes(response.content)
    shutil.copy2(ROOT / ".env", directory / ".env")
    shutil.copytree(ROOT / ".secrets", directory / "secrets")
    shutil.copytree(ROOT / ".local/calibrations", directory / "calibrations")
    manifest = {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*")
        if p.is_file()
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for relative, expected in manifest.items():
        if hashlib.sha256((directory / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Backup checksum verification failed")
    database.close()
    print("Backup checksums verified:", directory.relative_to(ROOT))


def run_calibration(path, tenant, species):
    from app.animals.contracts import AnimalSearch
    from app.domain.contracts import validate_tenant
    from app.retrieval.tuning import calibrate

    validate_tenant(tenant)
    AnimalSearch(image_base64="abcd", species=species, single_subject_confirmed=True)
    with Path(path).open() as stream:
        rows = list(csv.DictReader(stream))
    result = calibrate(rows, species)
    directory = ROOT / ".local/calibrations" / tenant
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (species + ".json")
    if target.exists():
        shutil.copy2(
            target,
            directory / (species + "." + time.strftime("%Y%m%d-%H%M%S") + ".bak.json"),
        )
    temporary = target.with_suffix(".pending")
    temporary.write_text(json.dumps(result, indent=2))
    temporary.replace(target)
    print("Calibration saved:", target.relative_to(ROOT))
    print(json.dumps(result["holdout"], indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["demo", "smoke", "benchmark", "backup", "calibrate", "score-pairs"],
    )
    parser.add_argument("--points", type=int, default=3000)
    parser.add_argument("--queries", type=int, default=40)
    parser.add_argument("--scores")
    parser.add_argument("--pairs")
    parser.add_argument("--tenant", default="local")
    parser.add_argument("--species", default="cat")
    args = parser.parse_args()
    if args.command == "benchmark":
        if not 1000 <= args.points <= 100000 or not 10 <= args.queries <= 1000:
            parser.error("Use 1000..100000 points and 10..1000 queries")
        benchmark(args.points, args.queries)
    elif args.command == "score-pairs":
        from pair_scores import score_pairs

        if not args.pairs or not args.scores:
            parser.error("--pairs and --scores are required")
        score_pairs(Path(args.pairs), Path(args.scores), ROOT)
    elif args.command == "calibrate":
        if not args.scores:
            parser.error("--scores CSV is required")
        run_calibration(args.scores, args.tenant, args.species)
    else:
        {"demo": demo, "smoke": smoke, "backup": backup}[args.command]()


if __name__ == "__main__":
    main()
