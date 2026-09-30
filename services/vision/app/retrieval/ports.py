from typing import Protocol


class JsonStore(Protocol):
    def request(self, method: str, path: str, **kwargs) -> dict: ...


class VisualEncoder(Protocol):
    def extract(self, content: bytes) -> tuple[list[float], dict]: ...
