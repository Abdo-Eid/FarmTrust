"""Evaluation against the held-out FarmTrust ML test set."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score, brier_score_loss, f1_score, precision_score, recall_score


TEST_SET_WARNING = """
   ╔══════════════════════════════════════════════════════════════════╗
   ║  ⚠  TEST SET IS RULE-BASED PROXY — NOT GROUND TRUTH  ⚠         ║
   ║  Results are indicative only.                                    ║
   ║  Replace data/ml/labels/test_set.csv with real manual           ║
   ║  annotations before reporting to lenders or stakeholders.        ║
   ╚══════════════════════════════════════════════════════════════════╝
   """

LABEL_TO_INDEX = {
    "active": 0,
    "bare": 1,
    "sparse": 2,
    "uncertain": 3,
    "intermittent": 2,
}


def load_test_set(path: str | Path = "data/ml/labels/test_set.csv") -> list[dict[str, str]]:
    print(TEST_SET_WARNING)
    test_path = Path(path)
    if not test_path.exists():
        raise FileNotFoundError(f"Missing test set: {test_path}")
    with test_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    active_true = (y_true == 0).astype(int)
    active_prob = y_prob[:, 0] if y_prob.size else np.asarray([], dtype=float)
    return {
        "precision_active": float(precision_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)),
        "recall_active": float(recall_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)),
        "f1_active": float(f1_score(y_true, y_pred, labels=[0], average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "false_active_rate": false_active_rate(y_true, y_pred),
        "brier_score_active": float(brier_score_loss(active_true, active_prob)) if len(active_true) else 0.0,
        "ece": expected_calibration_error(y_true, y_prob),
    }


def print_report(metrics: dict[str, float]) -> None:
    print("FarmTrust ML Evaluation")
    for key in (
        "precision_active",
        "recall_active",
        "f1_active",
        "macro_f1",
        "balanced_accuracy",
        "false_active_rate",
        "brier_score_active",
        "ece",
    ):
        print(f"{key}: {metrics.get(key, 0.0):.4f}")

    if metrics.get("precision_active", 0.0) < 0.88:
        raise AssertionError("precision_active < 0.88")
    if metrics.get("false_active_rate", 1.0) > 0.06:
        raise AssertionError("false_active_rate > 0.06")
    print("PASS")


def false_active_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    negatives = y_true != 0
    if int(negatives.sum()) == 0:
        return 0.0
    false_active = (y_pred == 0) & negatives
    return float(false_active.sum() / negatives.sum())


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    if y_prob.size == 0:
        return 0.0
    confidences = y_prob.max(axis=1)
    predictions = y_prob.argmax(axis=1)
    accuracies = predictions == y_true
    ece = 0.0
    for lower in np.linspace(0.0, 1.0, n_bins, endpoint=False):
        upper = lower + 1.0 / n_bins
        mask = (confidences > lower) & (confidences <= upper)
        if mask.any():
            ece += float(mask.mean() * abs(accuracies[mask].mean() - confidences[mask].mean()))
    return ece


def main() -> int:
    rows = load_test_set()
    if not rows:
        raise ValueError("Test set is empty")
    print(f"Loaded test_set.csv rows: {len(rows)}")
    print("FAIL: evaluation predictions are not available for the proxy test set yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
