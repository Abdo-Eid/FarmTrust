"""
Deterministically annotate AOIs from coverage and season-window metrics.

Writes data/ml/labels/manual_annotations.csv.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DATA_ROOT = Path("data")
TEST_SET_PATH = DATA_ROOT / "ml" / "labels" / "test_set.csv"
ANNOTATIONS_PATH = DATA_ROOT / "ml" / "labels" / "manual_annotations.csv"
ANNOTATION_METHOD = "auto_coverage_metrics"


def main() -> int:
    rows = _read_test_set(TEST_SET_PATH)
    annotated_at = datetime.now(UTC).isoformat()
    annotation_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, Any]] = []

    for row in rows:
        aoi_id = row["aoi_id"]
        quality_path = DATA_ROOT / "preprocess" / aoi_id / "quality_metrics.json"
        seasons_path = DATA_ROOT / "seasonal" / aoi_id / "season_windows.json"
        _ = _read_json(quality_path)
        season_payload = _read_json(seasons_path)
        seasons = list(season_payload.get("seasons", []))
        season_count = int(season_payload.get("season_count", len(seasons)))
        quality_labels = [str(season.get("quality_label", "")).lower() for season in seasons]
        confirmation_levels = [
            str(season.get("confirmation_level", "")).lower() for season in seasons
        ]
        label = _assign_label(season_count, quality_labels, confirmation_levels)
        if label is None:
            raise ValueError(f"Could not auto-label {aoi_id} from season metrics")

        annotation_rows.append(
            {
                "aoi_id": aoi_id,
                "manual_label": label,
                "annotated_at": annotated_at,
                "annotation_method": ANNOTATION_METHOD,
            }
        )
        summary_rows.append(
            {
                "aoi_id": aoi_id,
                "season_count": season_count,
                "quality_labels": ",".join(quality_labels) if quality_labels else "none",
                "auto_label": label,
            }
        )

    _write_annotations(annotation_rows)
    _print_summary(summary_rows)
    return 0


def _read_test_set(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing test set: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required AOI artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _assign_label(
    season_count: int,
    quality_labels: list[str],
    confirmation_levels: list[str],
) -> str | None:
    if (
        season_count >= 2
        and any(label == "good" for label in quality_labels)
        and any(level in {"strong", "moderate"} for level in confirmation_levels)
    ):
        return "active"
    if season_count == 1 and quality_labels and quality_labels[0] in {"good", "interrupted"}:
        return "intermittent"
    if season_count >= 1 and quality_labels and all(label == "weak" for label in quality_labels):
        return "sparse"
    if season_count == 0:
        return "bare"
    return None


def _write_annotations(rows: list[dict[str, str]]) -> None:
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ANNOTATIONS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["aoi_id", "manual_label", "annotated_at", "annotation_method"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(rows: list[dict[str, Any]]) -> None:
    print(f"{'aoi_id':<22} | {'season_count':>12} | {'quality_labels':<35} | auto_label")
    print("-" * 90)
    for row in rows:
        print(
            f"{row['aoi_id']:<22} | {row['season_count']:>12} | "
            f"{row['quality_labels']:<35} | {row['auto_label']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
