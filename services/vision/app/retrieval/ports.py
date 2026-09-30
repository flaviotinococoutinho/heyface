from typing import Protocol


class JsonStore(Protocol):
    def request(self, method: str, path: str, **kwargs) -> dict: ...


class VisualEncoder(Protocol):
    def extract(self, encoded: str) -> tuple[list[float], dict]: ...
