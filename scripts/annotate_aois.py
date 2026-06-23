"""
Interactive terminal annotation tool for Egypt AOIs.

Shows NDVI timeline and detected season windows per AOI.
Saves labels to data/ml/labels/manual_annotations.csv.

Usage:
  python scripts/annotate_aois.py
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

DATA_ROOT = Path("data")
TEST_SET_PATH = DATA_ROOT / "ml" / "labels" / "test_set.csv"
ANNOTATIONS_PATH = DATA_ROOT / "ml" / "labels" / "manual_annotations.csv"

LABEL_CHOICES = {
    "1": "active",
    "2": "intermittent",
    "3": "sparse",
    "4": "bare",
    "5": "skip",
}


@dataclass(frozen=True)
class SeasonWindow:
    season_id: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    quality_label: str
    confirmation_level: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate AOI activity labels from NDVI timelines.")
    parser.add_argument("--data-root", default="data", help="Root artifact directory")
    parser.add_argument("--dry-run", action="store_true", help="Display the first pending AOI and exit")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    test_set = _load_test_set(data_root / "ml" / "labels" / "test_set.csv")
    annotations_path = data_root / "ml" / "labels" / "manual_annotations.csv"
    annotations = _load_annotations(annotations_path)

    pending_rows = [row for row in test_set if row["aoi_id"] not in annotations]
    rows_to_show = pending_rows if pending_rows else test_set

    if args.dry_run:
        if not rows_to_show:
            print("No AOIs found in test set.")
            return 0
        _display_aoi(rows_to_show[0], data_root)
        print("DRY RUN: no annotation written.")
        return 0

    for row in rows_to_show:
        aoi_id = row["aoi_id"]
        if aoi_id in annotations and annotations[aoi_id] != "skip":
            continue

        _display_aoi(row, data_root)
        choice = _prompt_for_label()
        if choice == "q":
            break
        annotations[aoi_id] = LABEL_CHOICES[choice]
        _write_annotations(annotations_path, annotations)

    total = len(test_set)
    annotated = sum(1 for label in annotations.values() if label != "skip")
    skipped = sum(1 for label in annotations.values() if label == "skip")
    print(f"Annotated: {annotated}/{total} AOIs")
    print(f"Skipped:   {skipped} AOIs")
    print("Run: python scripts/merge_annotations.py to apply labels")
    return 0


def _load_test_set(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Test set not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_annotations(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return {
            str(row["aoi_id"]): str(row["manual_label"])
            for row in rows
            if row.get("aoi_id") and row.get("manual_label")
        }


def _write_annotations(path: Path, annotations: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["aoi_id", "manual_label", "annotated_at"])
        writer.writeheader()
        for aoi_id, label in sorted(annotations.items()):
            writer.writerow({"aoi_id": aoi_id, "manual_label": label, "annotated_at": now})


def _display_aoi(test_row: dict[str, str], data_root: Path) -> None:
    aoi_id = test_row["aoi_id"]
    quality = _read_json(data_root / "preprocess" / aoi_id / "quality_metrics.json")
    season_payload = _read_json(data_root / "seasonal" / aoi_id / "season_windows.json")
    seasons = _parse_seasons(season_payload)
    observations = _load_usable_observations(data_root / "preprocess" / aoi_id / "ndvi_smoothed.csv")

    print("\n" + "=" * 96)
    print(f"AOI: {aoi_id}")
    print(
        "usable_obs={usable}  seasons={seasons}  gap_risk={gap_risk}  max_gap_days={max_gap:.1f}".format(
            usable=int(quality.get("usable_observation_count", test_row.get("usable_observation_count", 0))),
            seasons=int(season_payload.get("season_count", len(seasons))),
            gap_risk=str(quality.get("gap_risk", test_row.get("gap_risk", ""))),
            max_gap=float(quality.get("max_gap_days", test_row.get("max_gap_days", 0.0))),
        )
    )
    print(f"proxy_label={test_row.get('label', '')}  source={test_row.get('label_source', '')}")
    print(f"quality_labels={_quality_summary(seasons)}")
    print("-" * 96)
    print("Detected activity windows")
    if seasons:
        for season in seasons:
            print(
                f"  {season.season_id}: {season.start_date.date()} -> {season.end_date.date()} "
                f"quality={season.quality_label} confirmation={season.confirmation_level}"
            )
    else:
        print("  none")
    print("-" * 96)
    print("NDVI timeline (usable observations)")
    print(f"{'date':<12} {'ndvi':>7} {'evi':>7} {'ndmi':>7}  season_window")
    for row in observations:
        marker = _season_marker(row["timestamp"], seasons)
        print(
            f"{row['timestamp'].date().isoformat():<12} "
            f"{_fmt_float(row['ndvi']):>7} "
            f"{_fmt_float(row['evi']):>7} "
            f"{_fmt_float(row['ndmi']):>7}  "
            f"{marker}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_seasons(payload: dict[str, Any]) -> list[SeasonWindow]:
    seasons: list[SeasonWindow] = []
    for index, item in enumerate(payload.get("seasons", []), start=1):
        start = pd.to_datetime(item.get("start_date"), errors="coerce", utc=True)
        end = pd.to_datetime(item.get("end_date"), errors="coerce", utc=True)
        if pd.isna(start) or pd.isna(end):
            continue
        seasons.append(
            SeasonWindow(
                season_id=str(item.get("season_id") or f"season_{index:02d}"),
                start_date=start,
                end_date=end,
                quality_label=str(item.get("quality_label", "")),
                confirmation_level=str(item.get("confirmation_level", "")),
            )
        )
    return seasons


def _load_usable_observations(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"NDVI timeline not found: {path}")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    usable = df[df["is_usable"].astype(str).str.lower().isin({"true", "1"})].copy()
    usable = usable.dropna(subset=["timestamp"]).sort_values("timestamp")
    rows: list[dict[str, Any]] = []
    for item in usable.itertuples(index=False):
        rows.append(
            {
                "timestamp": item.timestamp,
                "ndvi": getattr(item, "ndvi_smoothed", None),
                "evi": getattr(item, "evi_smoothed", None),
                "ndmi": getattr(item, "ndmi_smoothed", None),
            }
        )
    return rows


def _quality_summary(seasons: list[SeasonWindow]) -> str:
    if not seasons:
        return "none"
    parts = [f"{season.quality_label}/{season.confirmation_level}" for season in seasons]
    return ", ".join(parts)


def _season_marker(timestamp: pd.Timestamp, seasons: list[SeasonWindow]) -> str:
    hits = [
        season.season_id
        for season in seasons
        if season.start_date.normalize() <= timestamp.normalize() <= season.end_date.normalize()
    ]
    if not hits:
        return ""
    return "[SEASON] " + ",".join(hits)


def _fmt_float(value: Any) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "nan"
    return f"{float(number):.3f}"


def _prompt_for_label() -> str:
    print("\nChoose ground-truth label:")
    print("[1] active       - 2+ confirmed crop seasons visible")
    print("[2] intermittent - 1 season or irregular activity")
    print("[3] sparse       - weak vegetation only, no clear cycle")
    print("[4] bare         - no vegetation activity at all")
    print("[5] skip         - not sure, come back later")
    print("[q] quit         - save and exit")
    while True:
        choice = input("> ").strip().lower()
        if choice in LABEL_CHOICES or choice == "q":
            return choice
        print("Invalid choice. Enter 1, 2, 3, 4, 5, or q.")


if __name__ == "__main__":
    raise SystemExit(main())
