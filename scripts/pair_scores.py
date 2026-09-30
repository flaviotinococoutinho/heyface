"""Build calibrated-fusion inputs from locally authorized, labeled image pairs."""

import csv
from functools import lru_cache
from pathlib import Path

from app.animals.recognition import AnimalRecognition, local_match_count
from app.config import settings
from app.retrieval.tuning import validate_splits

IMAGE_CACHE_SIZE = 128
PAIR_COLUMNS = ("image_a", "image_b", "identity_a", "identity_b", "label", "split")
SCORE_COLUMNS = (*PAIR_COLUMNS, "global_score", "local_score")


def score_pairs(source: Path, destination: Path, root: Path):
    if destination.exists():
        raise ValueError("Choose a new score filename to preserve the previous experiment")
    with source.open() as stream:
        pairs = list(csv.DictReader(stream))
    validate_splits([row | {"global_score": 0, "local_score": 0} for row in pairs])
    engine = AnimalRecognition(settings)

    @lru_cache(maxsize=IMAGE_CACHE_SIZE)
    def extract(name):
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("Images must exist inside the workspace")
        return engine.extract(path.read_bytes())

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".pending")
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SCORE_COLUMNS)
        writer.writeheader()
        for pair in pairs:
            first, first_local, _ = extract(pair["image_a"])
            second, second_local, _ = extract(pair["image_b"])
            cosine = sum(a * b for a, b in zip(first, second, strict=True))
            row = {column: pair[column] for column in PAIR_COLUMNS}
            writer.writerow(
                row
                | {
                    "global_score": cosine,
                    "local_score": local_match_count(first_local, second_local),
                }
            )
    temporary.replace(destination)
    print(f"Scored {len(pairs)} pairs. No calibration was fitted or enabled.")
