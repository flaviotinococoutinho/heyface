"""Offline score calibration. Never fits or changes a model during a query."""

import hashlib
import json

import numpy as np
from scipy.optimize import differential_evolution
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from app.domain.representations import ANIMAL
from app.retrieval.calibration import calibrated_score

TUNING_SEED = 42
MAX_GENERATIONS = 40
POPULATION_SIZE = 10
MINIMUM_SPLIT_PAIRS = 4


def validate_splits(rows: list[dict]) -> dict[str, list[dict]]:
    splits = {
        name: [row for row in rows if row["split"] == name]
        for name in ("calibration", "validation", "test")
    }
    if sum(map(len, splits.values())) != len(rows):
        raise ValueError("Unknown split")
    seen_identities = set()
    seen_pairs = set()
    image_identities = {}
    for name, group in splits.items():
        if len(group) < MINIMUM_SPLIT_PAIRS or {int(row["label"]) for row in group} != {0, 1}:
            raise ValueError(f"{name}: include positive and negative labeled pairs")
        identities = {str(row[key]) for row in group for key in ("identity_a", "identity_b")}
        if identities & seen_identities:
            raise ValueError("Identity leakage between calibration, validation and test")
        seen_identities |= identities
        for row in group:
            for side in ("a", "b"):
                image, identity = row["image_" + side], row["identity_" + side]
                if not str(image).strip() or not str(identity).strip():
                    raise ValueError("Images and identities must be explicit")
                if image in image_identities and image_identities[image] != identity:
                    raise ValueError("One image cannot have conflicting identities")
                image_identities[image] = identity
            pair = tuple(sorted((row["image_a"], row["image_b"])))
            if pair in seen_pairs or pair[0] == pair[1]:
                raise ValueError("Duplicate pair or self-match would bias evaluation")
            seen_pairs.add(pair)
            if int(row["label"]) != int(row["identity_a"] == row["identity_b"]):
                raise ValueError("Label disagrees with the known identities")
            if not all(np.isfinite(float(row[key])) for key in ("global_score", "local_score")):
                raise ValueError("Scores must be finite")
    return splits


def fit_curve(scores, labels) -> dict:
    model = IsotonicRegression(out_of_bounds="clip").fit(scores, labels)
    x, y = model.X_thresholds_, model.y_thresholds_
    if len(x) < 2:
        raise ValueError("Calibration requires at least two distinct scores")
    # Average x coordinates of isotonic plateaus, then interpolate monotonically.
    levels = np.unique(y)
    if len(levels) < 2:
        raise ValueError("Scores contain no usable calibration signal")
    centers = [float(np.mean(x[y == level])) for level in levels]
    return {"x": centers, "y": levels.tolist()}


def tune_weights(scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
    def normalize(weights):
        return weights / weights.sum() if weights.sum() else np.ones(len(weights)) / len(weights)

    def loss(weights):
        return float(np.mean((scores @ normalize(weights) - labels) ** 2))

    result = differential_evolution(
        loss,
        [(0, 1)] * scores.shape[1],
        seed=TUNING_SEED,
        maxiter=MAX_GENERATIONS,
        popsize=POPULATION_SIZE,
        workers=1,
        polish=True,
    )
    uniform = np.ones(scores.shape[1]) / scores.shape[1]
    return normalize(result.x) if loss(result.x) < loss(uniform) else uniform


def calibrate(rows: list[dict], species: str) -> dict:
    splits = validate_splits(rows)
    training = splits["calibration"]
    columns = ("global_score", "local_score")
    curves = [
        fit_curve([float(row[column]) for row in training], [int(row["label"]) for row in training])
        for column in columns
    ]

    def matrix(group):
        return np.array(
            [
                [
                    calibrated_score(float(row[column]), curve)
                    for column, curve in zip(columns, curves, strict=True)
                ]
                for row in group
            ]
        )

    validation_labels = np.array([int(row["label"]) for row in splits["validation"]])
    weights = tune_weights(matrix(splits["validation"]), validation_labels)
    test_labels = np.array([int(row["label"]) for row in splits["test"]])
    test_scores = matrix(splits["test"]) @ weights
    baseline_scores = matrix(splits["test"]).mean(axis=1)
    return {
        "schema_version": 1,
        "model": ANIMAL.version,
        "species": species,
        "global_curve": curves[0],
        "local_curve": curves[1],
        "global_weight": float(weights[0]),
        "optimizer": {
            "name": "differential_evolution",
            "seed": TUNING_SEED,
            "selection_split": "validation",
            "objective": "brier_loss",
        },
        "dataset_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
        "holdout": {
            "pairs": len(test_labels),
            "brier": float(brier_score_loss(test_labels, test_scores)),
            "roc_auc": float(roc_auc_score(test_labels, test_scores)),
            "equal_weights_brier": float(brier_score_loss(test_labels, baseline_scores)),
        },
    }
