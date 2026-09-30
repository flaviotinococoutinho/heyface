import json
from dataclasses import dataclass
from functools import cached_property
from itertools import pairwise
from math import isfinite
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from app.domain.representations import ANIMAL
from app.errors import DomainError

CALIBRATION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CalibrationCurve:
    x: tuple[float, ...]
    y: tuple[float, ...]

    def __post_init__(self):
        if len(self.x) < 2 or len(self.x) != len(self.y):
            raise ValueError("Calibration needs aligned coordinates")
        if not all(isfinite(v) for v in self.x + self.y):
            raise ValueError("Calibration coordinates must be finite")
        if any(a >= b for a, b in pairwise(self.x)):
            raise ValueError("Calibration input must increase strictly")
        if any(a > b for a, b in pairwise(self.y)) or not all(0 <= y <= 1 for y in self.y):
            raise ValueError("Calibration probabilities must be monotone and bounded")

    @classmethod
    def from_document(cls, document):
        return cls(tuple(map(float, document["x"])), tuple(map(float, document["y"])))

    @cached_property
    def _interpolator(self):
        return PchipInterpolator(self.x, self.y)

    def score(self, raw: float) -> float:
        if not isfinite(raw):
            raise ValueError("Similarity must be finite")
        value = self._interpolator(np.clip(raw, self.x[0], self.x[-1]))
        return float(np.clip(value, 0, 1))


def calibrated_score(raw: float, curve: dict) -> float:
    return CalibrationCurve.from_document(curve).score(raw)


class CalibratedFusion:
    def __init__(self, document: dict):
        if (
            document.get("model") != ANIMAL.version
            or document.get("schema_version") != CALIBRATION_SCHEMA_VERSION
        ):
            raise ValueError("Calibration is incompatible with the representation contract")
        self.weight = float(document["global_weight"])
        if not isfinite(self.weight) or not 0 <= self.weight <= 1:
            raise ValueError("Invalid fusion weight")
        self.global_curve = CalibrationCurve.from_document(document["global_curve"])
        self.local_curve = CalibrationCurve.from_document(document["local_curve"])

    @classmethod
    def load(cls, tenant: str, species: str):
        path = Path("/calibrations") / tenant / f"{species}.json"
        try:
            document = json.loads(path.read_text())
            if document.get("species") != species:
                raise ValueError("Wrong species")
            return cls(document)
        except (OSError, ValueError, KeyError, TypeError):
            raise DomainError("calibration_required", 409) from None

    def score(self, global_score: float, local_score: float) -> float:
        return self.weight * self.global_curve.score(global_score) + (
            1 - self.weight
        ) * self.local_curve.score(local_score)
