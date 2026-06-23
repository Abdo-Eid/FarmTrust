"""Diagnose FarmTrust SITS-BERT predictions across all local AOIs."""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

try:
    from farmtrust_core.ml.inference import FarmTrustPredictor  # type: ignore[attr-defined]
except ImportError:
    FarmTrustPredictor = None  # type: ignore[assignment]

from farmtrust_core.ml.inference import CLASS_NAMES, _predict_probabilities
from farmtrust_core.ml.normalization import apply_normalization, load_stats
from farmtrust_core.ml.sequence_builder import SequenceBuilder

DATA_ROOT = Path("data")
MODEL_DIR = Path("models")
TEST_SET_PATH = DATA_ROOT / "ml" / "labels" / "test_set.csv"
DATASET_V2_PATH = DATA_ROOT / "ml" / "export" / "sits_dataset_v2.npz"
MODEL_CARD_PATH = MODEL_DIR / "model_card.json"
MODEL_PATH = MODEL_DIR / "sits_bert_finetuned.pt"


def main() -> int:
    print("FarmTrust prediction diagnosis")
    print(f"FarmTrustPredictor available: {'yes' if FarmTrustPredictor is not None else 'no'}")
    print()
    rows = _load_truth_rows()
    aoi_ids = _all_aoi_ids()
    model_card = _load_model_card()
    stats = load_stats(MODEL_DIR / "normalization_stats.json")
    builder = SequenceBuilder(data_root=DATA_ROOT)

    predictions: list[str] = []
    active_probs: list[float] = []
    print("aoi_id | true_label | raw_probs[active,bare,sparse,uncertain] | predicted_label")
    print("-" * 108)
    for aoi_id in aoi_ids:
        sequence = builder.build(aoi_id)
        features = apply_normalization(sequence["features"], stats)
        probs = _predict_probabilities(features, sequence, MODEL_PATH)
        mean_probs = _mean_real_probabilities(probs, sequence["attention_mask"])
        predicted_index = int(np.argmax(mean_probs))
        predicted_label = CLASS_NAMES[predicted_index]
        true_label = rows.get(aoi_id, "unlabeled")
        predictions.append(predicted_label)
        active_probs.append(float(mean_probs[0]))
        print(
            f"{aoi_id} | {true_label} | "
            f"[{mean_probs[0]:.4f}, {mean_probs[1]:.4f}, {mean_probs[2]:.4f}, {mean_probs[3]:.4f}] | "
            f"{predicted_label}"
        )

    distribution = collections.Counter(predictions)
    all_same = len(distribution) == 1
    print()
    print("Prediction distribution:", dict(distribution))
    print(f"Are all predictions the same class? {'yes' if all_same else 'no'}")
    print("Model optimal_threshold from model_card.json:", model_card.get("optimal_threshold", "not set"))
    print("What threshold would change predictions?")
    print(_threshold_change_summary(np.asarray(active_probs, dtype=float)))
    print()
    _print_training_distribution()
    print()
    _print_model_card_diagnosis(model_card)
    return 0


def _load_truth_rows() -> dict[str, str]:
    if not TEST_SET_PATH.exists():
        return {}
    df = pd.read_csv(TEST_SET_PATH)
    return {str(row.aoi_id): str(row.label) for row in df.itertuples(index=False)}


def _all_aoi_ids() -> list[str]:
    return sorted(path.name for path in (DATA_ROOT / "preprocess").iterdir() if path.is_dir())


def _load_model_card() -> dict[str, Any]:
    if not MODEL_CARD_PATH.exists():
        return {}
    return json.loads(MODEL_CARD_PATH.read_text(encoding="utf-8"))


def _mean_real_probabilities(probabilities: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    real = probabilities[attention_mask.astype(bool)]
    if real.size == 0:
        return np.zeros(len(CLASS_NAMES), dtype=float)
    return real.mean(axis=0)


def _threshold_change_summary(active_probs: np.ndarray) -> str:
    if len(active_probs) == 0:
        return "No active probabilities available."
    unique = np.unique(np.round(active_probs, 6))
    min_prob = float(active_probs.min())
    max_prob = float(active_probs.max())
    count_at_040 = int((active_probs >= 0.40).sum())
    count_at_065 = int((active_probs >= 0.65).sum())
    count_at_080 = int((active_probs >= 0.80).sum())
    return (
        f"active probability range is {min_prob:.4f} to {max_prob:.4f}; "
        f"AOIs above thresholds: >=0.40: {count_at_040}, >=0.65: {count_at_065}, >=0.80: {count_at_080}. "
        f"Unique active probabilities rounded to 6 decimals: {unique.tolist()}"
    )


def _print_training_distribution() -> None:
    d = np.load(DATASET_V2_PATH, allow_pickle=True)
    labels = d["weak_labels"].flatten()
    labels = labels[labels != -1]
    counts = collections.Counter(labels.tolist())
    print("Training label distribution:", counts)
    print("Total labeled observations:", len(labels))
    print("Class balance (pct):")
    for key, value in sorted(counts.items()):
        print(f"  class {key}: {value / len(labels) * 100:.1f}%")


def _print_model_card_diagnosis(model_card: dict[str, Any]) -> None:
    print("models/model_card.json:")
    print(json.dumps(model_card, indent=2))
    val_precision = model_card.get("val_precision_active")
    improved = isinstance(val_precision, (int, float)) and float(val_precision) > 0.0
    print(f"did val_precision_active improve above 0 during training? {'yes' if improved else 'no'}")
    print("optimal_threshold:", model_card.get("optimal_threshold", "not set"))


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
