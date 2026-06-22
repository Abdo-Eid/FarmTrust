"""Single-scene download, index computation, and chip writing — thread-safe worker."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import planetary_computer as pc
from rasterio.enums import Resampling

from farmtrust_core.ingest.indices import (
    compute_evi,
    compute_mndwi,
    compute_ndmi,
    compute_ndvi,
    compute_ndwi,
)
from farmtrust_core.ingest.utils import safe_write_text, utc_now_iso
from farmtrust_core.ingest.window_read import (
    ChipGrid,
    polygon_mask_for_grid,
    read_window_with_grid,
    reproject_to_grid,
    write_geotiff,
)
from farmtrust_core.ingest.dedup import normalize_spacecraft


@dataclass
class SceneResult:
    """Return value from process_one_scene — carries everything the main thread needs to persist."""
    item_id: str
    status: str  # "ok" | "empty_aoi" | "error"
    scene_record: Optional[Dict[str, Any]] = None
    csv_row: Optional[List[Any]] = None
    error: Optional[str] = None


def process_one_scene(
    item: Any,
    bbox: List[float],
    chips_root: Path,
    output_dir: Path,
    fingerprint: str,
    invalid_scl_classes: set,
    log_signed_hrefs: bool,
    logger: logging.Logger,
    geometry: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> SceneResult:
    """Download, compute indices, and write chips for one scene. Thread-safe.

    All writes go to chips_root/<item_id>/ which is unique per scene, so no
    cross-thread file conflicts. Shared state (scenes_index, CSV) is NOT touched
    here — the caller holds a lock and writes results after this returns.

    Retries up to max_retries times with exponential backoff (1s, 2s, ...) and
    re-signs the item before each retry to refresh expired SAS tokens.
    """
    item_id = item.id
    chip_dir = chips_root / item_id
    chip_dir.mkdir(parents=True, exist_ok=True)

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            # Re-sign on every attempt — SAS tokens expire and are cheap to refresh
            pc.sign_inplace(item)
            if log_signed_hrefs:
                for k, a in item.assets.items():
                    logger.info(f"signed_href[{item_id}][{k}] = {a.href}")

            if attempt > 0:
                wait = 2 ** (attempt - 1)  # 1s, 2s, 4s, ...
                logger.info(f"Retry {attempt}/{max_retries - 1} for {item_id} (backoff {wait}s)")
                time.sleep(wait)

            # 1) Read SCL window (defines canonical chip grid)
            scl_arr_raw, scl_crs, scl_transform = read_window_with_grid(item.assets["SCL"].href, bbox)
            if scl_arr_raw.size == 0 or scl_transform is None:
                logger.warning(f"Empty SCL window for {item_id}, skipping")
                return SceneResult(
                    item_id=item_id,
                    status="empty_aoi",
                    scene_record={
                        "item_id": item_id,
                        "status": "empty_aoi",
                        "fingerprint": fingerprint,
                        "timestamp": item.datetime.isoformat() if item.datetime else None,
                        "updated_at": utc_now_iso(),
                    },
                )

            grid = ChipGrid(
                crs_wkt=scl_crs.to_wkt(),
                transform=scl_transform,
                width=int(scl_arr_raw.shape[1]),
                height=int(scl_arr_raw.shape[0]),
            )

            scl_arr = scl_arr_raw.astype(np.uint8)
            invalid_mask = np.isin(scl_arr, list(invalid_scl_classes))
            aoi_mask = polygon_mask_for_grid(geometry, grid) if geometry else np.ones(scl_arr.shape, dtype=bool)
            valid_mask = (~invalid_mask) & aoi_mask
            denominator = int(aoi_mask.sum())
            if denominator <= 0:
                logger.warning(f"Polygon does not overlap chip grid for {item_id}, skipping")
                return SceneResult(
                    item_id=item_id,
                    status="empty_aoi",
                    scene_record={
                        "item_id": item_id,
                        "status": "empty_aoi",
                        "fingerprint": fingerprint,
                        "timestamp": item.datetime.isoformat() if item.datetime else None,
                        "updated_at": utc_now_iso(),
                    },
                )
            valid_fraction = float(valid_mask.sum() / denominator)

            # 2) Read other bands and reproject to SCL grid
            def read_band_to_grid(asset_key: str, resampling: Resampling) -> np.ndarray:
                arr_raw, crs, transform = read_window_with_grid(item.assets[asset_key].href, bbox)
                if arr_raw.size == 0 or transform is None:
                    return np.full((grid.height, grid.width), np.nan, dtype=np.float32)
                arr_raw = arr_raw.astype(np.float32)
                # Sentinel reflectance bands are typically int (scaled by 10000)
                return reproject_to_grid(
                    src_arr=arr_raw,
                    src_crs=crs,
                    src_transform=transform,
                    dst_grid=grid,
                    resampling=resampling,
                    src_nodata=None,
                    dst_nodata=np.nan,
                    dst_dtype=np.float32,
                )

            b02 = read_band_to_grid("B02", Resampling.bilinear) / 10000.0
            b03 = read_band_to_grid("B03", Resampling.bilinear) / 10000.0
            b04 = read_band_to_grid("B04", Resampling.bilinear) / 10000.0
            b08 = read_band_to_grid("B08", Resampling.bilinear) / 10000.0
            b11 = read_band_to_grid("B11", Resampling.bilinear) / 10000.0

            scl_arr = np.where(aoi_mask, scl_arr, 0).astype(np.uint8)
            b02 = np.where(aoi_mask, b02, np.nan)
            b03 = np.where(aoi_mask, b03, np.nan)
            b04 = np.where(aoi_mask, b04, np.nan)
            b08 = np.where(aoi_mask, b08, np.nan)
            b11 = np.where(aoi_mask, b11, np.nan)

            # 3) Compute indices
            ndvi_mean, ndvi_p95 = compute_ndvi(b04, b08, valid_mask)
            evi_mean, evi_p95 = compute_evi(b02, b04, b08, valid_mask)
            ndmi_mean, ndmi_p95 = compute_ndmi(b08, b11, valid_mask)
            ndwi_mean, ndwi_p95 = compute_ndwi(b03, b08, valid_mask)
            mndwi_mean, mndwi_p95 = compute_mndwi(b03, b11, valid_mask)

            mgrs_tile = item.properties.get("mgrs:grid_cell", "unknown")
            eo_cloud_cover = item.properties.get("eo:cloud_cover", -1)

            # 4) Write chips — isolated to chip_dir, no lock needed
            write_geotiff(chip_dir / "SCL.tif", scl_arr, grid, dtype="uint8", nodata=None)
            write_geotiff(chip_dir / "B02.tif", b02, grid, dtype="float32", nodata=np.nan)
            write_geotiff(chip_dir / "B03.tif", b03, grid, dtype="float32", nodata=np.nan)
            write_geotiff(chip_dir / "B04.tif", b04, grid, dtype="float32", nodata=np.nan)
            write_geotiff(chip_dir / "B08.tif", b08, grid, dtype="float32", nodata=np.nan)
            write_geotiff(chip_dir / "B11.tif", b11, grid, dtype="float32", nodata=np.nan)

            # 5) Per-scene manifest (local integrity)
            manifest = {
                "schema": "g15f.scene_manifest.v1",
                "item_id": item_id,
                "timestamp": item.datetime.isoformat() if item.datetime else None,
                "mgrs_tile": mgrs_tile,
                "eo_cloud_cover": eo_cloud_cover,
                "aoi_bbox_epsg4326": bbox,
                "aoi_geometry": geometry,
                "chip_grid": {
                    "crs_wkt": grid.crs_wkt,
                    "width": grid.width,
                    "height": grid.height,
                    # transform isn't JSON-serializable by default; store a friendly tuple
                    "transform_gdal": list(grid.transform.to_gdal()) if hasattr(grid.transform, "to_gdal") else None,
                },
                "files": {
                    "SCL": "SCL.tif", "B02": "B02.tif", "B03": "B03.tif",
                    "B04": "B04.tif", "B08": "B08.tif", "B11": "B11.tif",
                },
                "created_at": utc_now_iso(),
            }
            safe_write_text(chip_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))

            # 6) Build scene record and CSV row to return to caller
            scene_record = {
                "item_id": item_id,
                "timestamp": item.datetime.isoformat() if item.datetime else None,
                "mgrs_tile": mgrs_tile,
                "platform": item.properties.get("platform", "unknown"),
                "spacecraft": normalize_spacecraft(item.properties.get("platform", "unknown")),
                "eo_cloud_cover": eo_cloud_cover,
                "valid_fraction": valid_fraction,
                "fingerprint": fingerprint,
                "status": "ok",
                "chip_dir": str(chip_dir.relative_to(output_dir).as_posix()),
                "paths": {
                    "SCL": str((chip_dir / "SCL.tif").relative_to(output_dir).as_posix()),
                    "B02": str((chip_dir / "B02.tif").relative_to(output_dir).as_posix()),
                    "B03": str((chip_dir / "B03.tif").relative_to(output_dir).as_posix()),
                    "B04": str((chip_dir / "B04.tif").relative_to(output_dir).as_posix()),
                    "B08": str((chip_dir / "B08.tif").relative_to(output_dir).as_posix()),
                    "B11": str((chip_dir / "B11.tif").relative_to(output_dir).as_posix()),
                    "manifest": str((chip_dir / "manifest.json").relative_to(output_dir).as_posix()),
                },
                "stats": {
                    "ndvi_mean": ndvi_mean, "ndvi_p95": ndvi_p95,
                    "evi_mean": evi_mean, "evi_p95": evi_p95,
                    "ndmi_mean": ndmi_mean, "ndmi_p95": ndmi_p95,
                    "ndwi_mean": ndwi_mean, "ndwi_p95": ndwi_p95,
                    "mndwi_mean": mndwi_mean, "mndwi_p95": mndwi_p95,
                },
                "updated_at": utc_now_iso(),
            }
            csv_row = [
                item_id, item.datetime.isoformat(), mgrs_tile, eo_cloud_cover, valid_fraction,
                ndvi_mean, ndvi_p95, evi_mean, evi_p95,
                ndmi_mean, ndmi_p95, ndwi_mean, ndwi_p95,
                mndwi_mean, mndwi_p95,
            ]
            return SceneResult(item_id=item_id, status="ok", scene_record=scene_record, csv_row=csv_row)

        except Exception as e:
            last_exc = e

    # All retries exhausted
    logger.warning(f"Failed {item_id} after {max_retries} attempts: {last_exc}")
    return SceneResult(
        item_id=item_id,
        status="error",
        error=str(last_exc),
        scene_record={
            "item_id": item_id,
            "status": "error",
            "error": str(last_exc),
            "fingerprint": fingerprint,
            "timestamp": item.datetime.isoformat() if item.datetime else None,
            "updated_at": utc_now_iso(),
        },
    )
