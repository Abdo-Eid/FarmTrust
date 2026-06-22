"""Run the interval-based land assessment for one AOI."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.scoring import build_land_assessment, write_land_assessment


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the land assessment from preprocess and activity-window outputs."
    )
    parser.add_argument("--aoi-id", required=True, help="AOI identifier")
    parser.add_argument("--ingest-dir", default=None, help="Directory containing run_metadata.json")
    parser.add_argument("--preprocess-dir", default=None, help="Directory containing ndvi_smoothed.csv and quality_metrics.json")
    parser.add_argument("--seasonal-dir", default=None, help="Directory containing season_windows.json activity-window output")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/assessment/<aoi_id>)")
    args = parser.parse_args()

    aoi_id = args.aoi_id
    ingest_dir = Path(args.ingest_dir) if args.ingest_dir else Path("data") / aoi_id
    preprocess_dir = Path(args.preprocess_dir) if args.preprocess_dir else Path("data") / "preprocess" / aoi_id
    seasonal_dir = Path(args.seasonal_dir) if args.seasonal_dir else Path("data") / "seasonal" / aoi_id
    output_dir = Path(args.output_dir) if args.output_dir else Path("data") / "assessment" / aoi_id

    run_metadata_path = ingest_dir / "run_metadata.json"
    smoothed_csv_path = preprocess_dir / "ndvi_smoothed.csv"
    quality_metrics_path = preprocess_dir / "quality_metrics.json"
    season_payload_path = seasonal_dir / "season_windows.json"

    for path in (run_metadata_path, smoothed_csv_path, quality_metrics_path, season_payload_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    logging.info("Ingest directory: %s", ingest_dir)
    logging.info("Preprocess directory: %s", preprocess_dir)
    logging.info("Activity-window directory: %s", seasonal_dir)
    logging.info("Output directory: %s", output_dir)

    payload = build_land_assessment(
        run_metadata_path=run_metadata_path,
        smoothed_csv_path=smoothed_csv_path,
        quality_metrics_path=quality_metrics_path,
        season_payload_path=season_payload_path,
    )
    output_path = write_land_assessment(output_dir=output_dir, payload=payload)

    logging.info("Wrote land assessment to: %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
