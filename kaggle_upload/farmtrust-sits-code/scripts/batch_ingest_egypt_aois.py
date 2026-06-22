"""Batch ingest real Egypt agricultural AOIs through the existing pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


DATA_ROOT = Path("data")
TEMP_CONFIG_DIR = Path(".tmp") / "batch_ingest_egypt_aois"
START_DATE = "2020-01-01"
END_DATE = "2024-12-31"
MAX_CLOUD = 30


def bbox_to_polygon(bbox: list[float]) -> dict[str, Any]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }


def build_aois() -> list[dict[str, Any]]:
    raw_aois = [
        (
            "aoi_demo_02",
            "Demo-region offset east",
            [31.0403, 30.594356, 31.063848, 30.616635],
        ),
        (
            "aoi_demo_03",
            "Demo-region offset west",
            [30.9403, 30.594356, 30.963848, 30.616635],
        ),
        (
            "aoi_demo_04",
            "Demo-region offset north",
            [30.9903, 30.644356, 31.013848, 30.666635],
        ),
        (
            "aoi_demo_05",
            "Demo-region offset south",
            [30.9903, 30.544356, 31.013848, 30.566635],
        ),
        (
            "aoi_demo_06",
            "Demo-region offset northeast",
            [31.0903, 30.694356, 31.113848, 30.716635],
        ),
        (
            "aoi_demo_07",
            "Demo-region offset northwest",
            [30.8903, 30.694356, 30.913848, 30.716635],
        ),
        (
            "aoi_demo_08",
            "Demo-region offset southeast",
            [31.0903, 30.494356, 31.113848, 30.516635],
        ),
        (
            "aoi_demo_09",
            "Demo-region offset southwest",
            [30.8903, 30.494356, 30.913848, 30.516635],
        ),
        (
            "aoi_demo_10",
            "Demo-region offset far east",
            [31.1903, 30.644356, 31.213848, 30.666635],
        ),
        (
            "aoi_demo_11",
            "Demo-region offset far west",
            [30.7903, 30.544356, 30.813848, 30.566635],
        ),
    ]
    return [
        {
            "aoi_id": aoi_id,
            "governorate": governorate,
            "bbox": bbox,
            "geometry": bbox_to_polygon(bbox),
        }
        for aoi_id, governorate, bbox in raw_aois
    ]


def write_temp_config(aoi: dict[str, Any]) -> Path:
    TEMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    aoi_id = str(aoi["aoi_id"])
    config = {
        "aoi_id": aoi_id,
        "bbox": aoi["bbox"],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "max_cloud": MAX_CLOUD,
        "output_dir": str(DATA_ROOT / aoi_id).replace("\\", "/"),
    }
    path = TEMP_CONFIG_DIR / f"{aoi_id}.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def summarize_failure(result: subprocess.CompletedProcess[str]) -> str:
    lines = []
    if result.stderr:
        lines.extend(result.stderr.splitlines())
    if result.stdout:
        lines.extend(result.stdout.splitlines())
    lines = [line.strip() for line in lines if line.strip()]
    if not lines:
        return f"exit code {result.returncode}"
    return lines[-1]


def run_stage(stage: str, command: list[str]) -> tuple[bool, str]:
    print(f"RUN {stage}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return True, ""
    return False, summarize_failure(result)


def run_aoi(aoi: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    aoi_id = str(aoi["aoi_id"])
    config_path = write_temp_config(aoi)

    stages = [
        ("ingest", ["uv", "run", "ingest-aoi", "--config", str(config_path)]),
        ("preprocess", [sys.executable, "scripts/preprocess_timeseries.py", "--aoi-id", aoi_id]),
        ("seasonal", [sys.executable, "scripts/seasonal_analysis.py", "--aoi-id", aoi_id]),
        ("land_assessment", [sys.executable, "scripts/land_assessment.py", "--aoi-id", aoi_id]),
    ]

    for stage, command in stages:
        ok, error = run_stage(stage, command)
        if not ok:
            print(f"FAILED {aoi_id} {stage}: {error}", flush=True)
            return False, stage, error

    print(f"SUCCESS {aoi_id}", flush=True)
    return True, None, None


def main() -> int:
    aois = build_aois()
    succeeded: list[str] = []
    failed_by_stage = {
        "ingest": 0,
        "preprocess": 0,
        "seasonal": 0,
        "land_assessment": 0,
    }

    print("Batch ingest Egypt AOIs", flush=True)
    print(f"AOIs to process: {len(aois)}", flush=True)
    print(f"Date range: {START_DATE} to {END_DATE}", flush=True)
    print(f"Max cloud: {MAX_CLOUD}", flush=True)

    for index, aoi in enumerate(aois, start=1):
        aoi_id = str(aoi["aoi_id"])
        governorate = str(aoi["governorate"])
        print(f"\n[{index}/{len(aois)}] {aoi_id} - {governorate}", flush=True)
        ok, failed_stage, _error = run_aoi(aoi)
        if ok:
            succeeded.append(aoi_id)
        elif failed_stage:
            failed_by_stage[failed_stage] += 1

    print("\nBatch ingest summary", flush=True)
    print(f"AOIs succeeded all 4 stages: {len(succeeded)}", flush=True)
    for stage, count in failed_by_stage.items():
        print(f"Failed at {stage}: {count}", flush=True)
    print("Succeeded AOI IDs:", flush=True)
    if succeeded:
        for aoi_id in succeeded:
            print(f"  {aoi_id}", flush=True)
    else:
        print("  none", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
