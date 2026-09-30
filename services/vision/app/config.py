import os
from dataclasses import dataclass

from app.domain.representations import FACENET
from app.policies import IMAGE


@dataclass(frozen=True)
class Settings:
    qdrant_url: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    qdrant_key: str = os.getenv("QDRANT_API_KEY", "")
    service_token: str = os.getenv("VISION_SERVICE_TOKEN", "")
    collection: str = "heyface_people_v1"
    model_path: str = os.getenv("MODEL_PATH", "/models/facenet-vggface2.pt")
    max_image_bytes: int = IMAGE.max_bytes
    max_pixels: int = IMAGE.max_pixels
    max_dimension: int = IMAGE.max_detection_dimension
    dimensions: int = FACENET.dimensions
    model_version: str = FACENET.version


settings = Settings()
