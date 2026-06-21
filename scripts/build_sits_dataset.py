"""Build the FarmTrust agricultural-cycle SITS dataset for Kaggle upload."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.ml.normalization import compute_stats
from farmtrust_core.ml.sequence_builder import MAX_SEQ_LEN, SequenceBuilder
from farmtrust_core.ml.weak_labeler import WeakLabeler


def _find_aoi_ids(data_root: Path) -> list[str]:
    paths = sorted((data_root / "preprocess").glob("*/ndvi_smoothed.csv"))
    return [path.parent.name for path in paths]


def _labels_for_sequence(sequence: dict[str, Any], labels: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    lookup = {
        (str(row.aoi_id), str(row.timestamp)): int(row.label)
        for row in labels.itertuples(index=False)
    }
    cycle_labels: list[np.ndarray] = []
    cycle_weak_labels: list[np.ndarray] = []
    aoi_id = str(sequence["aoi_id"])

    for timestamps in sequence["timestamps"]:
        labels_row = np.full(MAX_SEQ_LEN, -1, dtype=np.int8)
        weak_row = np.full(MAX_SEQ_LEN, -1, dtype=np.int8)
        for index, timestamp in enumerate(timestamps):
            if not timestamp:
                continue
            label = lookup.get((aoi_id, timestamp), -1)
            labels_row[index] = label
            weak_row[index] = -1 if label == 3 else label
        cycle_labels.append(labels_row)
        cycle_weak_labels.append(weak_row)

    return np.stack(cycle_labels), np.stack(cycle_weak_labels)


def _load_or_generate_labels(data_root: Path, aoi_id: str) -> pd.DataFrame:
    return WeakLabeler(data_root=data_root).generate(aoi_id)


def _print_manifest(
    *,
    parcel_count: int,
    labels: np.ndarray,
    attention_mask: np.ndarray,
    output_path: Path,
) -> None:
    real_labels = labels[labels >= 0]
    distribution = Counter(int(value) for value in real_labels.tolist())
    lengths = attention_mask.sum(axis=1)
    size_mb = output_path.stat().st_size / 1_000_000
    print("SITS dataset manifest")
    print(f"  parcels: {parcel_count}")
    print(f"  cycles: {attention_mask.shape[0]}")
    print(f"  label_distribution: {dict(sorted(distribution.items()))}")
    print(f"  mean_sequence_length: {float(lengths.mean()):.2f}")
    print(f"  output: {output_path}")
    print(f"  output_size_mb: {size_mb:.3f}")


def build_dataset(data_root: Path, output_path: Path) -> dict[str, np.ndarray]:
    aoi_ids = _find_aoi_ids(data_root)
    if not aoi_ids:
        raise ValueError(f"No preprocessed AOIs found under {data_root / 'preprocess'}")

    builder = SequenceBuilder(data_root=data_root)
    feature_blocks: list[np.ndarray] = []
    mask_blocks: list[np.ndarray] = []
    doy_blocks: list[np.ndarray] = []
    label_blocks: list[np.ndarray] = []
    weak_label_blocks: list[np.ndarray] = []
    cycle_aoi_ids: list[str] = []
    cycle_ids: list[str] = []
    cycle_metadata: list[dict[str, Any]] = []

    for aoi_id in aoi_ids:
        sequence = builder.build(aoi_id)
        labels = _load_or_generate_labels(data_root, aoi_id)
        cycle_labels, cycle_weak_labels = _labels_for_sequence(sequence, labels)

        feature_blocks.append(sequence["features"])
        mask_blocks.append(sequence["attention_mask"])
        doy_blocks.append(sequence["doy"])
        label_blocks.append(cycle_labels)
        weak_label_blocks.append(cycle_weak_labels)

        for metadata in sequence["cycle_metadata"]:
            cycle_aoi_ids.append(aoi_id)
            cycle_ids.append(str(metadata["cycle_id"]))
            cycle_metadata.append(metadata)

    features = np.concatenate(feature_blocks, axis=0).astype(np.float32)
    attention_mask = np.concatenate(mask_blocks, axis=0).astype(bool)
    doy = np.concatenate(doy_blocks, axis=0).astype(np.int16)
    labels_array = np.concatenate(label_blocks, axis=0).astype(np.int8)
    weak_labels = np.concatenate(weak_label_blocks, axis=0).astype(np.int8)

    training_features = features[attention_mask]
    compute_stats(training_features)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        features=features,
        attention_mask=attention_mask,
        doy=doy,
        labels=labels_array,
        weak_labels=weak_labels,
        aoi_ids=np.asarray(cycle_aoi_ids, dtype=object),
        cycle_ids=np.asarray(cycle_ids, dtype=object),
        cycle_metadata=np.asarray(cycle_metadata, dtype=object),
    )
    _print_manifest(
        parcel_count=len(aoi_ids),
        labels=labels_array,
        attention_mask=attention_mask,
        output_path=output_path,
    )
    return {
        "features": features,
        "attention_mask": attention_mask,
        "doy": doy,
        "labels": labels_array,
        "weak_labels": weak_labels,
        "aoi_ids": np.asarray(cycle_aoi_ids, dtype=object),
        "cycle_ids": np.asarray(cycle_ids, dtype=object),
        "cycle_metadata": np.asarray(cycle_metadata, dtype=object),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FarmTrust SITS .npz dataset for Kaggle.")
    parser.add_argument("--data-root", default="data", help="Root artifact directory")
    parser.add_argument("--output", default="data/ml/export/sits_dataset.npz", help="Output .npz path")
    args = parser.parse_args()

    build_dataset(data_root=Path(args.data_root), output_path=Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
