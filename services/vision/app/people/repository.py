from datetime import UTC, datetime

from app.domain.contracts import normalize
from app.domain.representations import HUMAN_SPACES
from app.errors import DomainError
from app.people.contracts import Filters, Person
from app.policies import SEARCH
from app.retrieval.collection import VectorCollection, point_id


def build_filter(tenant: str, filters: Filters) -> dict:
    must = [{"key": "tenant_id", "match": {"value": tenant}}]
    for field in ("sex", "state", "city", "birth_date"):
        value = getattr(filters, field)
        if value is not None:
            key = f"{field}_normalized" if field in {"state", "city"} else field
            value = normalize(value) if field in {"state", "city"} else str(value)
            must.append({"key": key, "match": {"value": value}})
    if filters.name:
        for token in normalize(filters.name).split():
            must.append({"key": "name_tokens", "match": {"value": token}})
    bounds = {}
    if filters.birth_date_from:
        bounds["gte"] = filters.birth_date_from.toordinal()
    if filters.birth_date_to:
        bounds["lte"] = filters.birth_date_to.toordinal()
    if bounds:
        must.append({"key": "birth_ordinal", "range": bounds})
    return {"must": must}


def public_person(point: dict) -> dict:
    payload = point["payload"]
    return {
        k: payload[k]
        for k in (
            "id",
            "name",
            "sex",
            "birth_date",
            "state",
            "city",
            "face",
            "consent_recorded_at",
            "updated_at",
        )
    }


class PersonRepository(VectorCollection):
    def initialize(self):
        result = self.request("GET", self.path + "/exists")
        if not result["exists"]:
            self.request(
                "PUT",
                self.path,
                json={
                    "vectors": {
                        space.name: {"size": space.dimensions, "distance": "Cosine"}
                        for space in HUMAN_SPACES
                    },
                    "hnsw_config": {
                        "m": SEARCH.hnsw_connections,
                        "ef_construct": SEARCH.hnsw_construction_ef,
                    },
                    "optimizers_config": {"indexing_threshold": SEARCH.indexing_threshold_kib},
                    "on_disk_payload": True,
                },
            )
        info = self.request("GET", self.path)
        vectors = info["config"]["params"]["vectors"]
        for space in HUMAN_SPACES:
            name, size = space.name, space.dimensions
            if (
                vectors.get(name, {}).get("size") != size
                or vectors[name].get("distance") != "Cosine"
            ):
                raise RuntimeError("Incompatible collection. Migrate; never mix embedding models.")
        fields = {
            "tenant_id": {"type": "keyword", "is_tenant": True},
            "id": "uuid",
            "name_tokens": "keyword",
            "sex": "keyword",
            "state_normalized": "keyword",
            "city_normalized": "keyword",
            "birth_date": "keyword",
            "birth_ordinal": "integer",
        }
        for field, schema in fields.items():
            self.request(
                "PUT",
                self.path + "/index?wait=true",
                json={"field_name": field, "field_schema": schema},
            )

    def enroll(
        self,
        tenant: str,
        person_id: str,
        person: Person,
        vector: dict[str, list[float]],
        face: dict,
    ) -> dict:
        now = datetime.now(UTC).isoformat()
        payload = person.model_dump(mode="json", exclude={"consent"}) | {
            "id": person_id,
            "tenant_id": tenant,
            "face": face,
            "name_tokens": normalize(person.name).split(),
            "state_normalized": normalize(person.state),
            "city_normalized": normalize(person.city),
            "birth_ordinal": person.birth_date.toordinal(),
            "consent_recorded_at": now,
            "updated_at": now,
        }
        point = {"id": point_id(tenant, person_id), "vector": vector, "payload": payload}
        self.request("PUT", self.path + "/points?wait=true", json={"points": [point]})
        return public_person(point)

    def search(self, tenant: str, vector: list[float], query) -> list[dict]:
        body = {
            "query": vector,
            "using": query.method,
            "filter": build_filter(tenant, query.filters),
            "limit": query.limit,
            "with_payload": True,
            "with_vector": False,
            "params": {"hnsw_ef": query.hnsw_ef, "exact": query.exact},
        }
        if query.min_score is not None:
            body["score_threshold"] = query.min_score
        result = self.request("POST", self.path + "/points/query", json=body)
        return [
            {"person": public_person(p), "score": p["score"], "distance": max(0, 1 - p["score"])}
            for p in result["points"]
        ]

    def list(self, tenant: str, query) -> dict:
        body = {
            "filter": build_filter(tenant, query.filters),
            "limit": query.limit,
            "with_payload": True,
            "with_vector": False,
        }
        if query.cursor:
            body["offset"] = str(query.cursor)
        result = self.request("POST", self.path + "/points/scroll", json=body)
        return {
            "items": [public_person(p) for p in result["points"]],
            "next_cursor": result["next_page_offset"],
        }

    def get(self, tenant: str, person_id: str) -> dict:
        result = self.request(
            "POST",
            self.path + "/points",
            json={"ids": [point_id(tenant, person_id)], "with_payload": True, "with_vector": False},
        )
        if not result or result[0]["payload"].get("tenant_id") != tenant:
            raise DomainError("person_not_found", 404)
        return public_person(result[0])

    def delete(self, tenant: str, person_id: str):
        self.get(tenant, person_id)
        self.request(
            "POST",
            self.path + "/points/delete?wait=true",
            json={"points": [point_id(tenant, person_id)]},
        )
