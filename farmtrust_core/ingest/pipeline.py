"""AOI ingestion orchestrator: STAC search → dedup → parallel download → CSV + index output."""

from __future__ import annotations

import csv
import json
import logging
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class PipelineCancelledError(Exception):
    """Raised when the pipeline is cancelled by the user."""

import numpy as np
import planetary_computer as pc
import pystac_client

from farmtrust_core.ingest.config import default_dates, geometry_to_bbox, normalize_geometry
from farmtrust_core.ingest.dedup import normalize_spacecraft, pre_deduplicate_items
from farmtrust_core.ingest.processor import SceneResult, process_one_scene
from farmtrust_core.ingest.scene_index import load_scenes_index, save_scenes_index, should_skip_scene
from farmtrust_core.ingest.utils import compute_fingerprint, safe_write_text, utc_now_iso


def write_outputs(
    output_dir: Path,
    aoi_id: str,
    bbox: List[float],
    start_date: str,
    end_date: str,
    max_cloud: float,
    force_rerun: bool,
    limit_items: Optional[int],
    log_signed_hrefs: bool,
    deduplicate: bool = True,
    max_workers: int = 4,
    geometry: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> None:
    """Run full ingestion for one AOI: STAC search → dedup → download chips → compute indices → write outputs.

    Outputs written to output_dir:
      chips/<item_id>/        — per-scene band GeoTIFFs + manifest
      indices_timeseries.csv  — one row per processed scene
      scenes_index.json       — persistent registry for cache/skip logic
      run_metadata.json       — run config + scene counts for auditability

    With deduplicate=True (default), only the best scene per (date, spacecraft) is downloaded.
    Pass deduplicate=False (--no-dedupe) to process all STAC results for debugging.
    """
    logger = logging.getLogger(__name__)
    normalized_geometry = normalize_geometry(geometry) if geometry else None
    if normalized_geometry:
        bbox = geometry_to_bbox(normalized_geometry)

    if output_dir.exists() and force_rerun:
        logger.info(f"Clearing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    chips_root = output_dir / "chips"
    chips_root.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "indices_timeseries.csv"
    index_path = output_dir / "scenes_index.json"
    metadata_path = output_dir / "run_metadata.json"

    invalid_scl_classes = {0, 1, 3, 7, 8, 9, 10, 11}

    # Compute fingerprint to detect config changes that would invalidate cached chips
    fingerprint_payload = {
        "aoi_id": aoi_id,
        "bbox": bbox,
        "geometry": normalized_geometry,
        "start_date": start_date,
        "end_date": end_date,
        "max_cloud": float(max_cloud),
        "invalid_scl_classes": sorted(list(invalid_scl_classes)),
        "script": "ingest_aoi.v2.json-index.no-cache-dir.always-download-chips",
    }
    fingerprint = compute_fingerprint(fingerprint_payload)

    # Load / init global index
    scenes_index = load_scenes_index(index_path)
    scenes_index.setdefault("aoi_id", aoi_id)
    scenes_index.setdefault("bbox", bbox)
    scenes_index["fingerprint"] = fingerprint  # current run fingerprint (for reference)

    minx, miny, maxx, maxy = bbox
    # Store AOI geometry so downstream code can load it for coverage calculations.
    scenes_index.setdefault("aoi_geometry", normalized_geometry or {
        "type": "Polygon",
        "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
    })

    logger.info(f"Fetching Sentinel-2 scenes from {start_date} to {end_date}")
    # Planetary Computer URLs are signed SAS tokens; modifier=pc.sign_inplace auto-renews them during iteration
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        query={"eo:cloud_cover": {"lt": float(max_cloud)}},
    )

    items = sorted(list(search.items()), key=lambda x: x.datetime)
    if limit_items is not None:
        items = items[: int(limit_items)]

    logger.info(f"Found {len(items)} scenes (before dedup)")

    # Reduce download set before any I/O by filtering duplicate dates/spacecraft and high cloud cover
    if deduplicate:
        items = pre_deduplicate_items(items, logger)
        logger.info(f"After pre-dedup: {len(items)} scenes to process")

    headers = [
        "item_id",
        "timestamp",
        "mgrs_tile",
        "eo_cloud_cover",
        "valid_fraction",
        "ndvi_mean",
        "ndvi_p95",
        "evi_mean",
        "evi_p95",
        "ndmi_mean",
        "ndmi_p95",
        "ndwi_mean",
        "ndwi_p95",
        "mndwi_mean",
        "mndwi_p95",
    ]

    # Separate cache hits (no download needed) from scenes that require processing
    cached_items = []
    items_to_process = []
    for item in items:
        chip_dir = chips_root / item.id
        chip_dir.mkdir(parents=True, exist_ok=True)
        if should_skip_scene(scenes_index, item.id, chip_dir, fingerprint):
            cached_items.append(item)
        else:
            items_to_process.append(item)

    logger.info(
        f"{len(cached_items)} cached (skip), {len(items_to_process)} to download "
        f"(workers={max_workers})"
    )

    total_scenes = len(cached_items) + len(items_to_process)

    # Lock protects the two shared resources: scenes_index dict and CSV file handle
    index_lock = threading.Lock()
    rows_written = 0

    def _write_result(result: SceneResult) -> None:
        """Persist one scene result under the index lock. Called from main thread only."""
        nonlocal rows_written
        if result.scene_record:
            scenes_index["scenes"][result.item_id] = result.scene_record
            save_scenes_index(index_path, scenes_index)
        if result.csv_row:
            writer.writerow(result.csv_row)
            handle.flush()
            rows_written += 1

    # Write CSV header immediately; stream row-by-row with flush so partial results are visible before run finishes
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        handle.flush()

        # Cache hits: read stats from scenes_index and write CSV rows sequentially (instant, no I/O)
        for cache_idx, item in enumerate(cached_items):
            if cancel_check and cancel_check():
                raise PipelineCancelledError("Pipeline cancelled by user")
            item_id = item.id
            scene = scenes_index["scenes"][item_id]
            # Backfill platform fields for scenes processed before this feature was added
            if "platform" not in scene:
                scene["platform"] = item.properties.get("platform", "unknown")
                scene["spacecraft"] = normalize_spacecraft(scene["platform"])
                save_scenes_index(index_path, scenes_index)
            stats = scene.get("stats", {})
            row = [
                item_id,
                scene.get("timestamp"),
                scene.get("mgrs_tile", "unknown"),
                scene.get("eo_cloud_cover", -1),
                scene.get("valid_fraction", float("nan")),
                stats.get("ndvi_mean", float("nan")),
                stats.get("ndvi_p95", float("nan")),
                stats.get("evi_mean", float("nan")),
                stats.get("evi_p95", float("nan")),
                stats.get("ndmi_mean", float("nan")),
                stats.get("ndmi_p95", float("nan")),
                stats.get("ndwi_mean", float("nan")),
                stats.get("ndwi_p95", float("nan")),
                stats.get("mndwi_mean", float("nan")),
                stats.get("mndwi_p95", float("nan")),
            ]
            writer.writerow(row)
            handle.flush()
            rows_written += 1
            logger.info(f"Skipping {item_id} (chips already exist for this config)")
            if on_progress:
                on_progress(cache_idx + 1, total_scenes)

        # New scenes: submit all to thread pool, collect results as they complete
        scenes_downloaded = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_one_scene,
                    item, bbox, chips_root, output_dir, fingerprint,
                    invalid_scl_classes, log_signed_hrefs, logger, normalized_geometry,
                ): item
                for item in items_to_process
            }
            for future in as_completed(futures):
                if cancel_check and cancel_check():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise PipelineCancelledError("Pipeline cancelled by user")
                result = future.result()
                logger.info(f"Completed {result.item_id} → {result.status}")
                # Write to shared state under lock (index + CSV)
                with index_lock:
                    _write_result(result)
                scenes_downloaded += 1
                if on_progress:
                    on_progress(len(cached_items) + scenes_downloaded, total_scenes)

    # Run metadata
    run_metadata = {
        "aoi_id": aoi_id,
        "bbox": bbox,
        "geometry": normalized_geometry,
        "start_date": start_date,
        "end_date": end_date,
        "max_cloud": float(max_cloud),
        "mode": "download-chips+stats",
        "deduplication_applied": deduplicate,
        "created_at": utc_now_iso(),
        "scene_count": int(sum(1 for s in scenes_index.get("scenes", {}).values() if s.get("status") == "ok")),
        "invalid_scl_classes": sorted(list(invalid_scl_classes)),
        "outputs": {
            "chips_root": str(chips_root.as_posix()),
            "csv": str(csv_path.as_posix()),
            "scenes_index": str(index_path.as_posix()),
        },
        "fingerprint": fingerprint,
        "notes": "Canonical chips dataset + global JSON index caching (skip if chips exist for same fingerprint).",
    }
    logging.getLogger(__name__).info(f"Writing metadata to: {metadata_path}")
    safe_write_text(metadata_path, json.dumps(run_metadata, indent=2, sort_keys=True))
