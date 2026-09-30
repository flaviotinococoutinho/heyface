from datetime import UTC, datetime

from app.animals.recognition import local_match_count
from app.domain.representations import ANIMAL
from app.errors import DomainError
from app.policies import SEARCH
from app.retrieval.calibration import CalibratedFusion
from app.retrieval.collection import VectorCollection, point_id


def public_animal(point):
    return {
        k: point["payload"][k]
        for k in (
            "id",
            "name",
            "species",
            "sex",
            "breed",
            "color",
            "pattern",
            "representation",
            "updated_at",
        )
    }


class AnimalRepository(VectorCollection):
    def initialize(self):
        result = self.request("GET", self.path + "/exists")
        if not result["exists"]:
            self.request(
                "PUT",
                self.path,
                json={
                    "vectors": {"size": ANIMAL.dimensions, "distance": "Cosine"},
                    "hnsw_config": {
                        "m": SEARCH.hnsw_connections,
                        "ef_construct": SEARCH.hnsw_construction_ef,
                    },
                    "optimizers_config": {"indexing_threshold": SEARCH.indexing_threshold_kib},
                    "on_disk_payload": True,
                },
            )
        vectors = self.request("GET", self.path)["config"]["params"]["vectors"]
        if vectors.get("size") != ANIMAL.dimensions or vectors.get("distance") != "Cosine":
            raise RuntimeError("Incompatible animal collection")
        for field, schema in {
            "tenant_id": {"type": "keyword", "is_tenant": True},
            "species": "keyword",
            "id": "uuid",
        }.items():
            self.request(
                "PUT",
                self.path + "/index?wait=true",
                json={"field_name": field, "field_schema": schema},
            )

    def enroll_animal(self, tenant, body, vector, local, metadata):
        payload = body.animal.model_dump(exclude={"consent"}) | {
            "id": str(body.animal_id),
            "tenant_id": tenant,
            "local": local,
            "representation": metadata,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        point = {"id": point_id(tenant, str(body.animal_id)), "payload": payload, "vector": vector}
        self.request("PUT", self.path + "/points?wait=true", json={"points": [point]})
        return public_animal(point)

    def query_animals(self, tenant, body, vector, local):
        fusion = (
            CalibratedFusion.load(tenant, body.species) if body.method == "wildfusion" else None
        )
        result = self.request(
            "POST",
            self.path + "/points/query",
            json={
                "query": vector,
                "filter": {
                    "must": [
                        {"key": "tenant_id", "match": {"value": tenant}},
                        {"key": "species", "match": {"value": body.species}},
                    ]
                },
                "limit": body.candidate_limit if fusion else body.limit,
                "with_payload": True,
                "with_vector": False,
                "params": {"exact": body.exact, "hnsw_ef": body.hnsw_ef},
            },
        )
        matches = []
        for point in result["points"]:
            global_score = point["score"]
            local_score = local_match_count(local, point["payload"]["local"]) if fusion else None
            score = fusion.score(global_score, local_score) if fusion else global_score
            matches.append(
                {
                    "animal": public_animal(point),
                    "score": score,
                    "components": {"global_cosine": global_score, "local_matches": local_score},
                }
            )
        return sorted(matches, key=lambda m: m["score"], reverse=True)[: body.limit]

    def delete_animal(self, tenant, animal_id):
        identity = point_id(tenant, str(animal_id))
        points = self.request(
            "POST",
            self.path + "/points",
            json={"ids": [identity], "with_payload": True, "with_vector": False},
        )
        if not points or points[0]["payload"].get("tenant_id") != tenant:
            raise DomainError("person_not_found", 404)
        self.request("POST", self.path + "/points/delete?wait=true", json={"points": [identity]})
