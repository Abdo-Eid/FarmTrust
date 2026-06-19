"""Run vegetation activity-window detection for one AOI."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.seasonal import build_season_payload, write_season_payload


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _resolve_input_dir(aoi_id: str | None, input_dir: str | None) -> Path:
    if input_dir:
        return Path(input_dir)
    if aoi_id:
        return Path("data") / "preprocess" / aoi_id
    raise ValueError("Either --aoi-id or --input-dir is required")


def _load_aoi_id_from_quality_metrics(metrics_path: Path, fallback: str) -> str:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return str(metrics.get("aoi_id") or fallback)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect vegetation activity windows from preprocessing outputs."
    )
    parser.add_argument("--aoi-id", default=None, help="AOI identifier (default input dir: data/preprocess/<aoi_id>)")
    parser.add_argument("--input-dir", default=None, help="Directory containing ndvi_smoothed.csv and quality_metrics.json")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/seasonal/<aoi_id>)")
    args = parser.parse_args()

    input_dir = _resolve_input_dir(args.aoi_id, args.input_dir)
    smoothed_csv_path = input_dir / "ndvi_smoothed.csv"
    quality_metrics_path = input_dir / "quality_metrics.json"

    if not smoothed_csv_path.exists():
        raise FileNotFoundError(f"Missing smoothed NDVI CSV: {smoothed_csv_path}")
    if not quality_metrics_path.exists():
        raise FileNotFoundError(f"Missing quality metrics JSON: {quality_metrics_path}")

    aoi_id = args.aoi_id or _load_aoi_id_from_quality_metrics(
        quality_metrics_path,
        fallback=input_dir.name,
    )
    output_dir = Path(args.output_dir) if args.output_dir else Path("data") / "seasonal" / aoi_id

    logging.info("Input directory: %s", input_dir)
    logging.info("Output directory: %s", output_dir)

    payload = build_season_payload(
        smoothed_csv_path=smoothed_csv_path,
        quality_metrics_path=quality_metrics_path,
    )
    output_path = write_season_payload(output_dir=output_dir, payload=payload)

    logging.info("Wrote vegetation activity windows to: %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
