"""
Merge manual AOI annotations into test and weak-label CSV files.

Usage:
  python scripts/merge_annotations.py
  python scripts/merge_annotations.py --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DATA_ROOT = Path("data")
ANNOTATIONS_PATH = DATA_ROOT / "ml" / "labels" / "manual_annotations.csv"
TEST_SET_PATH = DATA_ROOT / "ml" / "labels" / "test_set.csv"
WEAK_LABELS_PATH = DATA_ROOT / "ml" / "labels" / "weak_labels.csv"

LABEL_TO_ID = {
    "active": 0,
    "bare": 1,
    "intermittent": 2,
    "sparse": 2,
    "uncertain": 3,
}
ID_TO_LABEL = {
    0: "active",
    1: "bare",
    2: "sparse",
    3: "uncertain",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge manual annotations into FarmTrust ML labels.")
    parser.add_argument("--data-root", default="data", help="Root artifact directory")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing files")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    annotations_path = data_root / "ml" / "labels" / "manual_annotations.csv"
    test_set_path = data_root / "ml" / "labels" / "test_set.csv"
    weak_labels_path = data_root / "ml" / "labels" / "weak_labels.csv"

    annotations = _load_annotations(annotations_path)
    test_set = _read_csv(test_set_path, "test set")
    weak_labels = _read_csv(weak_labels_path, "weak labels")

    valid_annotations = annotations[annotations["manual_label"].isin(LABEL_TO_ID)]
    annotation_lookup = dict(zip(valid_annotations["aoi_id"], valid_annotations["manual_label"], strict=False))

    updated_test_set, test_changed, test_unchanged = _merge_test_set(test_set, annotation_lookup)
    updated_weak_labels, weak_changed = _merge_weak_labels(weak_labels, annotation_lookup)

    print(f"Manual annotations loaded: {len(valid_annotations)}")
    print(f"test_set.csv updated: {test_changed} rows changed to manual_annotation")
    print(f"test_set.csv unchanged: {test_unchanged} rows still rule_based_proxy")
    print(f"weak_labels.csv overridden: {weak_changed} observations across {len(annotation_lookup)} AOIs")

    if args.dry_run:
        print("DRY RUN: no files written.")
        return 0

    updated_test_set.to_csv(test_set_path, index=False)
    updated_weak_labels.to_csv(weak_labels_path, index=False)
    return 0


def _read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return pd.read_csv(path)


def _load_annotations(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["aoi_id", "manual_label", "annotated_at"])
    annotations = pd.read_csv(path)
    required = {"aoi_id", "manual_label", "annotated_at"}
    missing = required - set(annotations.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    annotations = annotations.copy()
    annotations["aoi_id"] = annotations["aoi_id"].astype(str)
    annotations["manual_label"] = annotations["manual_label"].astype(str).str.strip().str.lower()
    annotations = annotations.drop_duplicates(subset=["aoi_id"], keep="last")
    unknown = sorted(set(annotations["manual_label"]) - set(LABEL_TO_ID) - {"skip"})
    if unknown:
        raise ValueError(f"Unknown manual labels in {path}: {unknown}")
    return annotations[annotations["manual_label"] != "skip"].reset_index(drop=True)


def _merge_test_set(test_set: pd.DataFrame, annotations: dict[str, str]) -> tuple[pd.DataFrame, int, int]:
    updated = test_set.copy()
    updated["aoi_id"] = updated["aoi_id"].astype(str)
    mask = updated["aoi_id"].isin(annotations)
    changed = int(mask.sum())
    if changed:
        updated.loc[mask, "label"] = updated.loc[mask, "aoi_id"].map(annotations)
        updated.loc[mask, "label_source"] = "manual_annotation"
    unchanged = int((updated["label_source"] != "manual_annotation").sum())
    return updated, changed, unchanged


def _merge_weak_labels(weak_labels: pd.DataFrame, annotations: dict[str, str]) -> tuple[pd.DataFrame, int]:
    updated = weak_labels.copy()
    updated["aoi_id"] = updated["aoi_id"].astype(str)
    mask = updated["aoi_id"].isin(annotations)
    changed = int(mask.sum())
    if changed:
        mapped_labels = updated.loc[mask, "aoi_id"].map(lambda aoi_id: LABEL_TO_ID[annotations[str(aoi_id)]])
        updated.loc[mask, "label"] = mapped_labels.astype(int)
        updated.loc[mask, "label_name"] = mapped_labels.map(ID_TO_LABEL)
        updated.loc[mask, "weak_confidence"] = 0.95
    return updated, changed


if __name__ == "__main__":
    raise SystemExit(main())
