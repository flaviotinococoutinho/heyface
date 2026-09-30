from uuid import UUID, uuid5

from app.retrieval.ports import JsonStore

POINT_NAMESPACE = UUID("82c5f4d0-99e4-4c50-87e8-095d3d92703b")
ANIMAL_COLLECTION = "heyface_animals_dinov2_sift_v1"


def point_id(tenant: str, identity: str) -> str:
    return str(uuid5(POINT_NAMESPACE, f"{tenant}:{identity}"))


class VectorCollection:
    """Shared storage mechanics; person and animal rules stay in their adapters."""

    def __init__(self, transport: JsonStore, name: str):
        self.transport = transport
        self.path = f"/collections/{name}"

    def request(self, method: str, path: str, **kwargs):
        return self.transport.request(method, path, **kwargs)

    def healthy(self):
        self.request("GET", self.path)
