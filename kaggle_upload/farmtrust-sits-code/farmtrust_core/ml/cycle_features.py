"""Cycle-level feature aggregation for classical activity models."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from farmtrust_core.ml.reliability import RELIABILITY_FEATURE_NAMES, load_reliability_features
from farmtrust_core.ml.sequence_builder import FEATURE_NAMES, SequenceBuilder
from farmtrust_core.ml.weak_labeler import WeakLabeler


AGGREGATIONS = ("mean", "std", "min", "max", "delta")
CLASSICAL_FEATURE_NAMES = [
    f"{feature}_{aggregation}"
    for feature in FEATURE_NAMES
    for aggregation in AGGREGATIONS
] + RELIABILITY_FEATURE_NAMES


def build_cycle_feature_table(data_root: str | Path = "data") -> pd.DataFrame:
    """Build one row per AOI agricultural cycle with weak cycle labels."""
    root = Path(data_root)
    aoi_ids = sorted(path.parent.name for path in (root / "preprocess").glob("*/ndvi_smoothed.csv"))
    if not aoi_ids:
        raise ValueError(f"No preprocessed AOIs found under {root / 'preprocess'}")

    builder = SequenceBuilder(data_root=root)
    labeler = WeakLabeler(data_root=root)
    rows: list[dict[str, Any]] = []
    for aoi_id in aoi_ids:
        sequence = builder.build(aoi_id)
        weak_labels = labeler.generate(aoi_id)
        label_lookup = {
            str(row.timestamp): int(row.label)
            for row in weak_labels.itertuples(index=False)
        }
        reliability = load_reliability_features(root, aoi_id)

        for cycle_index, metadata in enumerate(sequence["cycle_metadata"]):
            mask = sequence["attention_mask"][cycle_index]
            values = sequence["features"][cycle_index][mask]
            timestamps = [timestamp for timestamp in sequence["timestamps"][cycle_index] if timestamp]
            label = _cycle_label([label_lookup.get(timestamp, -1) for timestamp in timestamps])
            if label == -1:
                continue
            row = {
                "aoi_id": aoi_id,
                "cycle_id": metadata["cycle_id"],
                "label": int(label),
                "label_name": _label_name(label),
                "observation_count": int(mask.sum()),
            }
            row.update(_aggregate_features(values))
            row.update(reliability)
            rows.append(row)

    if not rows:
        raise ValueError("No labeled agricultural cycles available for classical ML training")
    return pd.DataFrame(rows)


def _aggregate_features(values: np.ndarray) -> dict[str, float]:
    features: dict[str, float] = {}
    for index, name in enumerate(FEATURE_NAMES):
        column = values[:, index].astype(np.float32)
        features[f"{name}_mean"] = float(np.mean(column))
        features[f"{name}_std"] = float(np.std(column))
        features[f"{name}_min"] = float(np.min(column))
        features[f"{name}_max"] = float(np.max(column))
        features[f"{name}_delta"] = float(column[-1] - column[0]) if len(column) > 1 else 0.0
    return features


def _cycle_label(labels: list[int]) -> int:
    usable = [label for label in labels if label >= 0]
    if not usable:
        return -1
    counts = Counter(usable)
    for priority_label in (0, 1, 2, 3):
        if counts.get(priority_label, 0) == max(counts.values()):
            return priority_label
    return counts.most_common(1)[0][0]


def _label_name(label: int) -> str:
    return {0: "active", 1: "bare", 2: "sparse", 3: "uncertain"}.get(label, "no_label")
