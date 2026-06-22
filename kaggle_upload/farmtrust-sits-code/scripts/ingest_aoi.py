"""
Sentinel-2 AOI ingestion CLI entry point.

Delegates all logic to farmtrust_core.ingest.pipeline. See that module for
the full pipeline: STAC search → dedup → parallel download → CSV + index output.

Canonical dataset layout:
  data/<aoi_id>/
    chips/
      <item_id>/
        SCL.tif
        B02.tif
        B03.tif
        B04.tif
        B08.tif
        B11.tif
        manifest.json
    indices_timeseries.csv
    scenes_index.json
    run_metadata.json
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from farmtrust_core.ingest.config import (
    default_dates,
    geometry_to_bbox,
    load_config,
    normalize_bbox,
    normalize_geometry,
    parse_bbox,
    parse_geometry,
)
from farmtrust_core.ingest.pipeline import write_outputs


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Sentinel-2 scenes: download AOI chips (default), compute indices, write CSV + global index."
    )
    parser.add_argument("--config", default=None, help="Path to JSON config file")
    parser.add_argument("--aoi-id", required=False, help="Stable identifier for the AOI")
    parser.add_argument("--bbox", required=False, type=parse_bbox, help="min_lon,min_lat,max_lon,max_lat in EPSG:4326")
    parser.add_argument("--geometry", required=False, type=parse_geometry, help="GeoJSON Polygon JSON string or file path")
    parser.add_argument("--start-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--max-cloud", type=float, default=None, help="Cloud cover threshold (0-100)")
    parser.add_argument("--output-dir", default=None, help="Override output directory (default: data/<aoi_id>)")
    parser.add_argument("--force-rerun", action="store_true", help="Clear existing output and rerun ingestion")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--limit-items", type=int, default=None, help="Limit number of scenes (for testing)")
    parser.add_argument("--log-signed-hrefs", action="store_true", help="Log signed asset hrefs (very verbose)")
    parser.add_argument("--no-dedupe", action="store_true",
                        help="Skip pre-download deduplication; emit all scenes (raw mode)")
    parser.add_argument("--workers", type=int, default=None,
                        help="Parallel download workers (default: 4; set 1 to disable parallelism)")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger(__name__).debug("Debug logging enabled")

    config = load_config(args.config)

    aoi_id = args.aoi_id or config.get("aoi_id")
    bbox_raw = args.bbox or config.get("bbox")
    geometry_raw = args.geometry or config.get("geometry")

    if not aoi_id or (bbox_raw is None and geometry_raw is None):
        raise ValueError("aoi_id and either bbox or geometry are required (via args or config)")

    geometry = normalize_geometry(geometry_raw) if geometry_raw is not None else None
    if geometry is not None:
        bbox = geometry_to_bbox(geometry)
    elif bbox_raw is not None:
        bbox = bbox_raw if isinstance(bbox_raw, list) else normalize_bbox(bbox_raw)
    else:
        raise ValueError("bbox or geometry is required")

    start_date = args.start_date or config.get("start_date")
    end_date = args.end_date or config.get("end_date")
    if not start_date or not end_date:
        start_date, end_date = default_dates()
        logging.getLogger(__name__).info(f"Using default dates: {start_date} to {end_date}")
    else:
        logging.getLogger(__name__).info(f"Using provided dates: {start_date} to {end_date}")

    max_cloud = args.max_cloud if args.max_cloud is not None else config.get("max_cloud", 30.0)
    output_dir_value = args.output_dir or config.get("output_dir")
    output_dir = Path(output_dir_value) if output_dir_value else Path("data") / aoi_id

    logging.getLogger(__name__).info(f"Output directory: {output_dir}")
    logging.getLogger(__name__).info(f"Force rerun: {args.force_rerun}")
    logging.getLogger(__name__).info(f"Max cloud cover: {max_cloud}")
    if args.limit_items is not None:
        logging.getLogger(__name__).info(f"Limit items: {args.limit_items}")

    write_outputs(
        output_dir=output_dir,
        aoi_id=aoi_id,
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud=float(max_cloud),
        force_rerun=args.force_rerun,
        limit_items=args.limit_items,
        log_signed_hrefs=args.log_signed_hrefs,
        deduplicate=not args.no_dedupe,
        max_workers=args.workers if args.workers is not None else config.get("workers", 4),
        geometry=geometry,
    )

    logging.getLogger(__name__).info(f"Ingestion complete for {aoi_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
