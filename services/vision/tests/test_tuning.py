import copy

import numpy as np
import pytest

from app.retrieval.calibration import CalibrationCurve
from app.retrieval.tuning import calibrate, tune_weights, validate_splits


def labeled_pairs():
    rows = []
    for split in ("calibration", "validation", "test"):
        for index, label in enumerate((0, 0, 1, 1)):
            identity = f"{split}-{index}"
            rows.append(
                {
                    "split": split,
                    "image_a": identity + "-a",
                    "image_b": identity + "-b",
                    "identity_a": identity,
                    "identity_b": identity if label else identity + "-other",
                    "label": label,
                    "global_score": 0.2 + label * 0.6 + index * 0.01,
                    "local_score": 2 + label * 20 + index,
                }
            )
    return rows


def test_calibration_is_reproducible_and_reports_untouched_holdout():
    rows = labeled_pairs()
    original = copy.deepcopy(rows)
    first = calibrate(rows, "cat")
    assert first == calibrate(rows, "cat")
    assert rows == original
    assert first["holdout"]["pairs"] == 4
    assert "equal_weights_brier" in first["holdout"]
    assert first["optimizer"]["selection_split"] == "validation"


@pytest.mark.parametrize(
    "change", ["identity_leak", "self_match", "wrong_label", "non_finite", "duplicate_pair"]
)
def test_evaluation_rejects_leakage_and_invalid_ground_truth(change):
    rows = labeled_pairs()
    if change == "identity_leak":
        rows[4]["identity_a"] = rows[0]["identity_a"]
    if change == "self_match":
        rows[0]["image_b"] = rows[0]["image_a"]
    if change == "wrong_label":
        rows[0]["label"] = 1
    if change == "non_finite":
        rows[0]["global_score"] = float("nan")
    if change == "duplicate_pair":
        rows[1].update({key: rows[0][key] for key in ("image_a", "image_b")})
    with pytest.raises(ValueError):
        validate_splits(rows)


def test_optimizer_can_discard_a_misleading_signal():
    scores = np.array([[0.1, 0.9], [0.9, 0.1], [0.2, 0.8], [0.8, 0.2]])
    labels = np.array([0, 1, 0, 1])
    weights = tune_weights(scores, labels)
    assert np.isclose(weights.sum(), 1)
    assert weights[0] > 0.99
    assert np.mean((scores @ weights - labels) ** 2) < np.mean((scores.mean(axis=1) - labels) ** 2)


@pytest.mark.parametrize(
    "x,y", [((0, 0), (0, 1)), ((0, 1), (1, 0)), ((0, 1), (0, 2)), ((0, float("nan")), (0, 1))]
)
def test_calibration_curve_rejects_invalid_coordinates(x, y):
    with pytest.raises(ValueError):
        CalibrationCurve(x, y)
