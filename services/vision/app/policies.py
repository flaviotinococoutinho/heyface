"""Operational knobs; embedding dimensions and identities live in the domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePolicy:
    max_encoded_characters: int = 7_000_000
    max_bytes: int = 5 * 1024 * 1024
    max_pixels: int = 16_000_000
    max_detection_dimension: int = 1024
    minimum_face_size: int = 40
    facenet_confidence: float = 0.95
    yunet_confidence: float = 0.90
    facenet_crop_size: int = 160
    animal_crop_size: int = 224
    local_image_dimension: int = 512
    local_feature_limit: int = 256
    local_descriptor_size: int = 128
    local_ratio_threshold: float = 0.75
    inference_slots: int = 1
    inference_queue_seconds: float = 0.05
    torch_threads: int = 2


@dataclass(frozen=True)
class SearchPolicy:
    human_limit: int = 50
    animal_limit: int = 20
    default_limit: int = 10
    page_limit: int = 100
    default_page_size: int = 25
    candidate_limit: int = 100
    default_candidates: int = 40
    hnsw_ef_min: int = 32
    hnsw_ef_max: int = 1024
    hnsw_ef: int = 128
    hnsw_connections: int = 16
    hnsw_construction_ef: int = 128
    indexing_threshold_kib: int = 1000
    storage_timeout_seconds: int = 15


IMAGE = ImagePolicy()
SEARCH = SearchPolicy()
