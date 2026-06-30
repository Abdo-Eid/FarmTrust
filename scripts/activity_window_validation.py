"""Emit a CSV view for validating detected vegetation activity windows."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _window_ids_for_date(row_date: datetime, windows: list[dict[str, Any]]) -> list[str]:
    matched: list[str] = []
    for window in windows:
        start = _parse_date(str(window["start_date"]))
        end = _parse_date(str(window["end_date"]))
        if start.date() <= row_date.date() <= end.date():
            matched.append(str(window["season_id"]))
    return matched


def _boundary_markers_for_date(row_date: datetime, windows: list[dict[str, Any]]) -> list[str]:
    markers: list[str] = []
    for window in windows:
        window_id = str(window["season_id"])
        date_text = row_date.date().isoformat()
        for field, marker in (
            ("start_date", "start"),
            ("peak_date", "peak"),
            ("end_date", "end"),
        ):
            if str(window.get(field)) == date_text:
                markers.append(f"{window_id}:{marker}")
    return markers


def _gap_marker(row_time: datetime, previous_usable_time: datetime | None) -> tuple[str, str]:
    if previous_usable_time is None:
        return "", "false"
    gap_days = (row_time - previous_usable_time).total_seconds() / 86400.0
    if gap_days <= 0:
        return "0.00", "false"
    return f"{gap_days:.2f}", str(gap_days > 10.0).lower()


def build_validation_rows(
    *,
    smoothed_csv_path: Path,
    quality_metrics_path: Path,
    season_windows_path: Path,
) -> list[dict[str, str]]:
    rows = _read_rows(smoothed_csv_path)
    quality_metrics = _read_json(quality_metrics_path)
    season_payload = _read_json(season_windows_path)
    windows = list(season_payload.get("seasons", []))
    long_gaps = list(quality_metrics.get("long_gap_windows", []))

    output: list[dict[str, str]] = []
    previous_usable_time: datetime | None = None
    for row in rows:
        row_time = _parse_timestamp(row["timestamp"])
        is_usable = row.get("is_usable", "").strip().lower() == "true"
        gap_after_previous_days, long_gap_after_previous = _gap_marker(row_time, previous_usable_time)
        in_long_gap = "false"
        for gap in long_gaps:
            start = gap.get("start_timestamp")
            end = gap.get("end_timestamp")
            if isinstance(start, str) and isinstance(end, str):
                if _parse_timestamp(start) <= row_time <= _parse_timestamp(end):
                    in_long_gap = "true"
                    break

        output.append(
            {
                "timestamp": row["timestamp"],
                "is_usable": str(is_usable).lower(),
                "valid_fraction": row.get("valid_fraction", ""),
                "ndvi_raw": row.get("ndvi_raw", ""),
                "ndvi_p95_raw": row.get("ndvi_p95_raw", ""),
                "ndvi_spread_raw": row.get("ndvi_spread_raw", ""),
                "ndvi_smoothed": row.get("ndvi_smoothed", ""),
                "evi_raw": row.get("evi_raw", ""),
                "evi_smoothed": row.get("evi_smoothed", ""),
                "ndmi_raw": row.get("ndmi_raw", ""),
                "ndmi_smoothed": row.get("ndmi_smoothed", ""),
                "ndwi_raw": row.get("ndwi_raw", ""),
                "ndwi_smoothed": row.get("ndwi_smoothed", ""),
                "mndwi_raw": row.get("mndwi_raw", ""),
                "mndwi_smoothed": row.get("mndwi_smoothed", ""),
                "gap_after_previous_usable_days": gap_after_previous_days,
                "long_gap_after_previous": long_gap_after_previous,
                "inside_long_gap_window": in_long_gap,
                "activity_window_ids": "|".join(_window_ids_for_date(row_time, windows)),
                "activity_window_boundary_markers": "|".join(_boundary_markers_for_date(row_time, windows)),
            }
        )
        if is_usable:
            previous_usable_time = row_time

    return output


def write_validation_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "timestamp",
        "is_usable",
        "valid_fraction",
        "ndvi_raw",
        "ndvi_p95_raw",
        "ndvi_spread_raw",
        "ndvi_smoothed",
        "evi_raw",
        "evi_smoothed",
        "ndmi_raw",
        "ndmi_smoothed",
        "ndwi_raw",
        "ndwi_smoothed",
        "mndwi_raw",
        "mndwi_smoothed",
        "gap_after_previous_usable_days",
        "long_gap_after_previous",
        "inside_long_gap_window",
        "activity_window_ids",
        "activity_window_boundary_markers",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write activity-window validation CSV from existing preprocess and seasonal artifacts."
    )
    parser.add_argument("--aoi-id", required=True, help="AOI identifier")
    parser.add_argument("--preprocess-dir", default=None, help="Directory containing ndvi_smoothed.csv and quality_metrics.json")
    parser.add_argument("--seasonal-dir", default=None, help="Directory containing season_windows.json")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/validation/<aoi_id>)")
    args = parser.parse_args()

    preprocess_dir = Path(args.preprocess_dir) if args.preprocess_dir else Path("data") / "preprocess" / args.aoi_id
    seasonal_dir = Path(args.seasonal_dir) if args.seasonal_dir else Path("data") / "seasonal" / args.aoi_id
    output_dir = Path(args.output_dir) if args.output_dir else Path("data") / "validation" / args.aoi_id

    rows = build_validation_rows(
        smoothed_csv_path=preprocess_dir / "ndvi_smoothed.csv",
        quality_metrics_path=preprocess_dir / "quality_metrics.json",
        season_windows_path=seasonal_dir / "season_windows.json",
    )
    output_path = output_dir / "activity_window_validation.csv"
    write_validation_csv(rows, output_path)
    print(f"Wrote activity-window validation CSV to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
