"""Run the Phase A multi-metric preprocessing baseline for one AOI."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.preprocess import build_preprocess_artifacts, write_preprocess_outputs


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _resolve_input_dir(aoi_id: str | None, input_dir: str | None) -> Path:
    if input_dir:
        return Path(input_dir)
    if aoi_id:
        return Path("data") / aoi_id
    raise ValueError("Either --aoi-id or --input-dir is required")


def _load_aoi_id_from_metadata(metadata_path: Path, fallback: str) -> str:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return str(metadata.get("aoi_id") or fallback)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preprocess NDVI/EVI/NDMI/NDWI time-series from ingestion outputs."
    )
    parser.add_argument("--aoi-id", default=None, help="AOI identifier (default input dir: data/<aoi_id>)")
    parser.add_argument("--input-dir", default=None, help="Directory containing indices_timeseries.csv and run_metadata.json")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: data/preprocess/<aoi_id>)")
    parser.add_argument(
        "--valid-fraction-threshold",
        type=float,
        default=0.90,
        help="Minimum valid_fraction for a usable observation",
    )
    args = parser.parse_args()

    input_dir = _resolve_input_dir(args.aoi_id, args.input_dir)
    csv_path = input_dir / "indices_timeseries.csv"
    metadata_path = input_dir / "run_metadata.json"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing ingestion CSV: {csv_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata JSON: {metadata_path}")

    aoi_id = args.aoi_id or _load_aoi_id_from_metadata(metadata_path, fallback=input_dir.name)
    output_dir = Path(args.output_dir) if args.output_dir else Path("data") / "preprocess" / aoi_id

    logging.info("Input directory: %s", input_dir)
    logging.info("Output directory: %s", output_dir)
    logging.info("Valid fraction threshold: %.2f", args.valid_fraction_threshold)

    artifacts = build_preprocess_artifacts(
        csv_path=csv_path,
        metadata_path=metadata_path,
        valid_fraction_threshold=float(args.valid_fraction_threshold),
    )
    output_paths = write_preprocess_outputs(
        output_dir=output_dir,
        processed_observations=artifacts["processed_observations"],
        quality_metrics=artifacts["quality_metrics"],
    )

    logging.info("Wrote smoothed metric series to: %s", output_paths["csv_path"])
    logging.info("Wrote quality metrics to: %s", output_paths["metrics_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
