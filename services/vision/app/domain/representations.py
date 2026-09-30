from dataclasses import dataclass
from math import fsum, isfinite, sqrt

UNIT_NORM_TOLERANCE = 1e-5


@dataclass(frozen=True)
class VectorSpace:
    name: str
    dimensions: int
    version: str

    def normalize(self, values) -> "Embedding":
        values = tuple(float(value) for value in values)
        if len(values) != self.dimensions or not all(isfinite(value) for value in values):
            raise ValueError("Vector does not belong to this embedding space")
        magnitude = sqrt(fsum(value * value for value in values))
        if magnitude == 0:
            raise ValueError("A zero vector has no cosine similarity")
        return Embedding(self, tuple(value / magnitude for value in values))


@dataclass(frozen=True)
class Embedding:
    space: VectorSpace
    values: tuple[float, ...]

    def __post_init__(self):
        if len(self.values) != self.space.dimensions:
            raise ValueError("Invalid embedding dimension")
        if not all(isfinite(v) for v in self.values):
            raise ValueError("Embedding must be finite")
        norm = fsum(v * v for v in self.values)
        if abs(norm - 1) > UNIT_NORM_TOLERANCE:
            raise ValueError("Embedding must be normalized")


FACENET = VectorSpace("facenet", 512, "facenet-vggface2-mtcnn-160-v1")
SFACE = VectorSpace("sface", 128, "sface-yunet-2021dec-2023mar-v1")
ANIMAL = VectorSpace("dinov2", 384, "dinov2-small-224-sift256-v1")
HUMAN_SPACES = (FACENET, SFACE)
