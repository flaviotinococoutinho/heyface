import httpx

from app.errors import DomainError
from app.policies import SEARCH


class Qdrant:
    def __init__(self, settings):
        self.client = httpx.Client(
            base_url=settings.qdrant_url,
            timeout=SEARCH.storage_timeout_seconds,
            headers={"api-key": settings.qdrant_key},
        )

    def request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()["result"]
        except (httpx.HTTPError, ValueError, KeyError):
            raise DomainError("storage_unavailable", 503) from None

    def close(self):
        self.client.close()
