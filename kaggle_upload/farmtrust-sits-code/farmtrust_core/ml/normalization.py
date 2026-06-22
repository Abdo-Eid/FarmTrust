"""Computes and applies Z-score normalization statistics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from farmtrust_core.ml.sequence_builder import FEATURE_NAMES


def compute_stats(features: np.ndarray, output_path: str | Path = "models/normalization_stats.json") -> dict[str, Any]:
    """Compute feature-wise Z-score statistics and save them as JSON."""
    array = np.asarray(features, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] != len(FEATURE_NAMES):
        raise ValueError(f"Expected features with shape (N, {len(FEATURE_NAMES)}), got {array.shape}")
    array = np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0)
    std = array.std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    stats = {
        "mean": array.mean(axis=0).astype(float).tolist(),
        "std": std.astype(float).tolist(),
        "feature_names": FEATURE_NAMES,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def apply_normalization(features: np.ndarray, stats: dict[str, Any]) -> np.ndarray:
    """Apply Z-score normalization, sanitize bad values, and clip to [-5, 5]."""
    _assert_stats(stats)
    array = np.asarray(features, dtype=np.float32)
    mean = np.asarray(stats["mean"], dtype=np.float32)
    std = np.asarray(stats["std"], dtype=np.float32)
    std = np.where(std < 1e-6, 1.0, std)
    normalized = (np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0) - mean) / std
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(normalized, -5.0, 5.0).astype(np.float32)


def load_stats(path: str | Path) -> dict[str, Any]:
    stats = json.loads(Path(path).read_text(encoding="utf-8"))
    _assert_stats(stats)
    return stats


def _assert_stats(stats: dict[str, Any]) -> None:
    missing = [key for key in ("mean", "std", "feature_names") if key not in stats]
    if missing:
        raise AssertionError(f"Normalization stats missing keys: {missing}")
    if list(stats["feature_names"]) != FEATURE_NAMES:
        raise AssertionError("Normalization feature_names do not match ML feature order")
    if len(stats["mean"]) != len(FEATURE_NAMES) or len(stats["std"]) != len(FEATURE_NAMES):
        raise AssertionError("Normalization mean/std length does not match feature count")
