"""Create a rule-based proxy parcel test set from high-coverage AOI artifacts."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DATA_ROOT = Path("data")
OUTPUT_PATH = DATA_ROOT / "ml" / "labels" / "test_set.csv"
LABEL_SOURCE = "rule_based_proxy — not manually annotated ground truth"

CONFIDENCE_NOTES = {
    "active": "High-confidence proxy: >=2 good confirmed seasons",
    "intermittent": "Medium-confidence proxy: 1 season only",
    "sparse": "Low-confidence proxy: weak seasons only",
    "bare": "Medium-confidence proxy: 0 seasons, good coverage",
}

FIELDNAMES = [
    "aoi_id",
    "label",
    "label_source",
    "usable_observation_count",
    "season_count",
    "max_gap_days",
    "gap_risk",
    "confidence_note",
]


def main() -> int:
    candidates = _find_candidate_aois()
    rows: list[dict[str, Any]] = []
    coverage_pass_count = 0
    ambiguous_count = 0

    for aoi_id in candidates:
        quality = _read_json(DATA_ROOT / "preprocess" / aoi_id / "quality_metrics.json")
        seasons_payload = _read_json(DATA_ROOT / "seasonal" / aoi_id / "season_windows.json")

        if not _passes_coverage_gate(quality, seasons_payload):
            continue
        coverage_pass_count += 1

        label = _assign_label(quality, seasons_payload)
        if label is None:
            ambiguous_count += 1
            continue

        rows.append(
            {
                "aoi_id": aoi_id,
                "label": label,
                "label_source": LABEL_SOURCE,
                "usable_observation_count": int(quality.get("usable_observation_count", 0)),
                "season_count": int(seasons_payload.get("season_count", len(seasons_payload.get("seasons", [])))),
                "max_gap_days": float(quality.get("max_gap_days", 0.0)),
                "gap_risk": str(quality.get("gap_risk", "")),
                "confidence_note": CONFIDENCE_NOTES[label],
            }
        )

    _print_summary(candidates, coverage_pass_count, ambiguous_count, rows)

    if len(rows) < 5:
        print(
            "WARNING: Test set has fewer than 5 parcels.\n"
            "Run more AOIs through the pipeline before evaluating."
        )
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote proxy test set: {OUTPUT_PATH}")
    return 0


def _find_candidate_aois() -> list[str]:
    preprocess_root = DATA_ROOT / "preprocess"
    seasonal_root = DATA_ROOT / "seasonal"
    if not preprocess_root.exists() or not seasonal_root.exists():
        return []

    aoi_ids: list[str] = []
    for quality_path in sorted(preprocess_root.glob("*/quality_metrics.json")):
        aoi_id = quality_path.parent.name
        season_path = seasonal_root / aoi_id / "season_windows.json"
        if season_path.exists():
            aoi_ids.append(aoi_id)
    return aoi_ids


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _passes_coverage_gate(quality: dict[str, Any], seasons_payload: dict[str, Any]) -> bool:
    # PROXY GATE — Egypt-calibrated thresholds
    # gap_risk field removed: Egypt winter cloud gaps (90-150 days) are
    # normal and cause false "high" risk ratings in the existing pipeline.
    # We use usable_observation_count and gap_ratio as quality proxies instead.
    # Production gate: recalibrate after collecting 100+ manually labeled AOIs.
    seasons = seasons_payload.get("seasons", [])
    season_count = int(seasons_payload.get("season_count", len(seasons)))
    return (
        int(quality.get("usable_observation_count", 0)) >= 10
        and float(quality.get("gap_ratio", 1.0)) <= 0.50
        and season_count >= 0
    )


def _assign_label(quality: dict[str, Any], seasons_payload: dict[str, Any]) -> str | None:
    del quality
    seasons = seasons_payload.get("seasons", [])
    season_count = int(seasons_payload.get("season_count", len(seasons)))
    quality_labels = [str(season.get("quality_label", "")).lower() for season in seasons]
    confirmation_levels = [str(season.get("confirmation_level", "")).lower() for season in seasons]

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


def _print_summary(
    candidates: list[str],
    coverage_pass_count: int,
    ambiguous_count: int,
    rows: list[dict[str, Any]],
) -> None:
    distribution = Counter(row["label"] for row in rows)
    print("Proxy test set summary")
    print(f"Total AOIs found: {len(candidates)}")
    print(f"AOIs passing coverage gate: {coverage_pass_count}")
    print(f"AOIs skipped (ambiguous): {ambiguous_count}")
    print(f"AOIs written to test set: {len(rows)}")
    print("Label distribution:")
    for label in ("active", "intermittent", "sparse", "bare"):
        print(f"  {label}: {distribution.get(label, 0)}")


if __name__ == "__main__":
    raise SystemExit(main())
