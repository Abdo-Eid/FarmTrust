"""
Sentinel-2 AOI ingestion: downloads AOI chips (default behavior), computes indices,
and maintains a global JSON index for true caching.

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
import csv
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds
from rasterio.warp import reproject

from farmtrust_core.ingest.config import default_dates, load_config, normalize_bbox, parse_bbox
from farmtrust_core.ingest.indices import (
    compute_evi,
    compute_mndwi,
    compute_ndmi,
    compute_ndvi,
    compute_ndwi,
)
from farmtrust_core.ingest.utils import compute_fingerprint, safe_write_text, utc_now_iso


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# -------------------------
# Geospatial utilities
# -------------------------

def bbox_to_scene_crs(bbox_lonlat: List[float], dst_crs: str, src_crs: str = "EPSG:4326") -> List[float]:
    """Transform bbox from lon/lat to scene CRS."""
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    minx, miny = transformer.transform(bbox_lonlat[0], bbox_lonlat[1])
    maxx, maxy = transformer.transform(bbox_lonlat[2], bbox_lonlat[3])
    return [min(minx, maxx), min(miny, maxy), max(minx, maxx), max(miny, maxy)]


@dataclass(frozen=True)
class ChipGrid:
    """Defines the canonical grid for AOI chips, based on the SCL band of each scene.
     The SCL band is used as the reference for the grid because it defines valid/invalid pixels
     and has the same resolution as the main Sentinel-2 bands (10m). By reprojecting all bands
     to this grid, we ensure that the mask aligns correctly with the indices.

     The grid is defined by its CRS (in WKT), affine transform, width, and height. This allows
     for flexible handling of different scenes that may have varying resolutions or alignments,
     while still maintaining a consistent reference frame for the AOI chips.
    
    wkt means "Well-Known Text" and is a standard format for representing coordinate reference systems (CRS) in geospatial applications.
    """
    crs_wkt: str
    transform: Any
    width: int
    height: int


def read_window_with_grid(asset_href: str, bbox_lonlat: List[float]) -> Tuple[np.ndarray, Any, Any]:
    """
    Read AOI window from COG asset.
    Returns: (array, crs, window_transform)
    """
    with rasterio.open(asset_href) as src:
        if src.crs is None:
            raise ValueError("Asset has no CRS")

        bbox_scene = bbox_to_scene_crs(bbox_lonlat, src.crs.to_string())
        window = from_bounds(*bbox_scene, transform=src.transform)
        window = window.round_offsets().round_lengths()

        if window.width <= 0 or window.height <= 0:
            return np.array([]), src.crs, None

        window = window.intersection(Window(0, 0, src.width, src.height))
        if window.width <= 0 or window.height <= 0:
            return np.array([]), src.crs, None

        arr = src.read(1, window=window)
        win_transform = src.window_transform(window)
        return arr, src.crs, win_transform


def reproject_to_grid(
    src_arr: np.ndarray,
    src_crs: Any,
    src_transform: Any,
    dst_grid: ChipGrid,
    resampling: Resampling,
    src_nodata: Optional[float] = None,
    dst_nodata: Optional[float] = None,
    dst_dtype: Optional[np.dtype] = None,
) -> np.ndarray:
    """
    Reproject / resample src array to dst grid.
    """
    if dst_dtype is None:
        dst_dtype = src_arr.dtype

    dst = np.full((dst_grid.height, dst_grid.width), dst_nodata if dst_nodata is not None else 0, dtype=dst_dtype)

    reproject(
        source=src_arr,
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=src_nodata,
        dst_transform=dst_grid.transform,
        dst_crs=dst_grid.crs_wkt,
        dst_nodata=dst_nodata,
        resampling=resampling,
    )
    return dst


def write_geotiff(path: Path, arr: np.ndarray, grid: ChipGrid, dtype: str, nodata: Optional[float] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=grid.height,
        width=grid.width,
        count=1,
        dtype=dtype,
        crs=grid.crs_wkt,
        transform=grid.transform,
        nodata=nodata,
        tiled=True,
        compress="deflate",
        predictor=2 if np.dtype(dtype).kind == "f" else 1,
    ) as dst:
        dst.write(arr.astype(dtype), 1)


# -------------------------
# Global JSON index (canonical)
# -------------------------

def load_scenes_index(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"schema": "g15f.scenes_index.v1", "created_at": utc_now_iso(), "updated_at": utc_now_iso(), "scenes": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "scenes" not in data:
        raise ValueError(f"Invalid scenes_index.json format: {path}")
    if not isinstance(data["scenes"], dict):
        raise ValueError("scenes_index.json 'scenes' must be an object keyed by item_id")
    return data


def save_scenes_index(path: Path, index: Dict[str, Any]) -> None:
    index["updated_at"] = utc_now_iso()
    safe_write_text(path, json.dumps(index, indent=2, sort_keys=True))


def chips_complete(chip_dir: Path) -> bool:
    expected = ["SCL.tif", "B02.tif", "B03.tif", "B04.tif", "B08.tif", "B11.tif", "manifest.json"]
    return all((chip_dir / f).exists() for f in expected)


def should_skip_scene(index: Dict[str, Any], item_id: str, chip_dir: Path, fingerprint: str) -> bool:
    """
    Skip if:
      - chip files exist AND
      - index contains scene with same fingerprint AND
      - status == "ok"
    """
    scene = index.get("scenes", {}).get(item_id)
    if not scene:
        return False
    if scene.get("fingerprint") != fingerprint:
        return False
    if scene.get("status") != "ok":
        return False
    return chips_complete(chip_dir)


# -------------------------
# Main ingestion
# -------------------------

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
) -> None:
    logger = logging.getLogger(__name__)

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

    # Fingerprint used for skip logic
    fingerprint_payload = {
        "aoi_id": aoi_id,
        "bbox": bbox,
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

    logger.info(f"Fetching Sentinel-2 scenes from {start_date} to {end_date}")
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

    logger.info(f"Found {len(items)} scenes")

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

    # Write CSV header immediately so you see the file early
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        handle.flush()

        rows_written = 0

        for idx, item in enumerate(items):
            item_id = item.id
            logger.info(f"Processing item {idx + 1}/{len(items)}: {item_id}")

            pc.sign_inplace(item)
            if log_signed_hrefs:
                for k, a in item.assets.items():
                    logger.info(f"signed_href[{item_id}][{k}] = {a.href}")

            chip_dir = chips_root / item_id
            chip_dir.mkdir(parents=True, exist_ok=True)

            if should_skip_scene(scenes_index, item_id, chip_dir, fingerprint):
                logger.info(f"Skipping {item_id} (chips already exist for this config)")
                # Still write a CSV row from index (if present)
                scene = scenes_index["scenes"][item_id]
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
                continue

            # Download + compute
            try:
                # 1) Read SCL window (defines canonical chip grid)
                scl_arr_raw, scl_crs, scl_transform = read_window_with_grid(item.assets["SCL"].href, bbox)
                if scl_arr_raw.size == 0 or scl_transform is None:
                    logger.warning(f"Empty SCL window for {item_id}, skipping")
                    scenes_index["scenes"][item_id] = {
                        "item_id": item_id,
                        "status": "empty_aoi",
                        "fingerprint": fingerprint,
                        "timestamp": item.datetime.isoformat() if item.datetime else None,
                        "updated_at": utc_now_iso(),
                    }
                    save_scenes_index(index_path, scenes_index)
                    continue

                grid = ChipGrid(
                    crs_wkt=scl_crs.to_wkt(),
                    transform=scl_transform,
                    width=int(scl_arr_raw.shape[1]),
                    height=int(scl_arr_raw.shape[0]),
                )

                scl_arr = scl_arr_raw.astype(np.uint8)

                invalid_mask = np.isin(scl_arr, list(invalid_scl_classes))
                valid_mask = ~invalid_mask
                valid_fraction = float(valid_mask.sum() / valid_mask.size)

                # 2) Read other bands and reproject to SCL grid
                def read_band_to_grid(asset_key: str, resampling: Resampling) -> np.ndarray:
                    arr_raw, crs, transform = read_window_with_grid(item.assets[asset_key].href, bbox)
                    if arr_raw.size == 0 or transform is None:
                        return np.full((grid.height, grid.width), np.nan, dtype=np.float32)

                    # Sentinel reflectance bands are typically int (scaled by 10000)
                    arr_raw = arr_raw.astype(np.float32)

                    # Reproject / resample to SCL grid (so mask matches)
                    dst = reproject_to_grid(
                        src_arr=arr_raw,
                        src_crs=crs,
                        src_transform=transform,
                        dst_grid=grid,
                        resampling=resampling,
                        src_nodata=None,
                        dst_nodata=np.nan,
                        dst_dtype=np.float32,
                    )
                    return dst

                b02 = read_band_to_grid("B02", Resampling.bilinear) / 10000.0
                b03 = read_band_to_grid("B03", Resampling.bilinear) / 10000.0
                b04 = read_band_to_grid("B04", Resampling.bilinear) / 10000.0
                b08 = read_band_to_grid("B08", Resampling.bilinear) / 10000.0
                b11 = read_band_to_grid("B11", Resampling.bilinear) / 10000.0

                # 3) Compute indices
                ndvi_mean, ndvi_p95 = compute_ndvi(b04, b08, valid_mask)
                evi_mean, evi_p95 = compute_evi(b02, b04, b08, valid_mask)
                ndmi_mean, ndmi_p95 = compute_ndmi(b08, b11, valid_mask)
                ndwi_mean, ndwi_p95 = compute_ndwi(b03, b08, valid_mask)
                mndwi_mean, mndwi_p95 = compute_mndwi(b03, b11, valid_mask)

                mgrs_tile = item.properties.get("mgrs:grid_cell", "unknown")
                eo_cloud_cover = item.properties.get("eo:cloud_cover", -1)

                # 4) Write chips (canonical grid)
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
                    "chip_grid": {
                        "crs_wkt": grid.crs_wkt,
                        "width": grid.width,
                        "height": grid.height,
                        # transform isn’t JSON-serializable by default; store a friendly tuple
                        "transform_gdal": list(grid.transform.to_gdal()) if hasattr(grid.transform, "to_gdal") else None,
                    },
                    "files": {
                        "SCL": "SCL.tif",
                        "B02": "B02.tif",
                        "B03": "B03.tif",
                        "B04": "B04.tif",
                        "B08": "B08.tif",
                        "B11": "B11.tif",
                    },
                    "created_at": utc_now_iso(),
                }
                safe_write_text(chip_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))

                # 6) Update global index
                scene_record = {
                    "item_id": item_id,
                    "timestamp": item.datetime.isoformat() if item.datetime else None,
                    "mgrs_tile": mgrs_tile,
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
                        "ndvi_mean": ndvi_mean,
                        "ndvi_p95": ndvi_p95,
                        "evi_mean": evi_mean,
                        "evi_p95": evi_p95,
                        "ndmi_mean": ndmi_mean,
                        "ndmi_p95": ndmi_p95,
                        "ndwi_mean": ndwi_mean,
                        "ndwi_p95": ndwi_p95,
                        "mndwi_mean": mndwi_mean,
                        "mndwi_p95": mndwi_p95,
                    },
                    "updated_at": utc_now_iso(),
                }
                scenes_index["scenes"][item_id] = scene_record
                save_scenes_index(index_path, scenes_index)

                # 7) Append CSV row immediately
                row = [
                    item_id,
                    item.datetime.isoformat(),
                    mgrs_tile,
                    eo_cloud_cover,
                    valid_fraction,
                    ndvi_mean,
                    ndvi_p95,
                    evi_mean,
                    evi_p95,
                    ndmi_mean,
                    ndmi_p95,
                    ndwi_mean,
                    ndwi_p95,
                    mndwi_mean,
                    mndwi_p95,
                ]
                writer.writerow(row)
                handle.flush()
                rows_written += 1

            except Exception as e:
                logger.warning(f"Error processing {item_id}: {e}")
                scenes_index["scenes"][item_id] = {
                    "item_id": item_id,
                    "status": "error",
                    "error": str(e),
                    "fingerprint": fingerprint,
                    "timestamp": item.datetime.isoformat() if item.datetime else None,
                    "updated_at": utc_now_iso(),
                }
                save_scenes_index(index_path, scenes_index)
                continue

    # Run metadata
    run_metadata = {
        "aoi_id": aoi_id,
        "bbox": bbox,
        "start_date": start_date,
        "end_date": end_date,
        "max_cloud": float(max_cloud),
        "mode": "download-chips+stats",
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Sentinel-2 scenes: download AOI chips (default), compute indices, write CSV + global index."
    )
    parser.add_argument("--config", default=None, help="Path to JSON config file")
    parser.add_argument("--aoi-id", required=False, help="Stable identifier for the AOI")
    parser.add_argument("--bbox", required=False, type=parse_bbox, help="min_lon,min_lat,max_lon,max_lat in EPSG:4326")
    parser.add_argument("--start-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--max-cloud", type=float, default=None, help="Cloud cover threshold (0-100)")
    parser.add_argument("--output-dir", default=None, help="Override output directory (default: data/<aoi_id>)")
    parser.add_argument("--force-rerun", action="store_true", help="Clear existing output and rerun ingestion")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--limit-items", type=int, default=None, help="Limit number of scenes (for testing)")
    parser.add_argument("--log-signed-hrefs", action="store_true", help="Log signed asset hrefs (very verbose)")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger(__name__).debug("Debug logging enabled")

    config = load_config(args.config)

    aoi_id = args.aoi_id or config.get("aoi_id")
    bbox_raw = args.bbox or config.get("bbox")

    if not aoi_id or bbox_raw is None:
        raise ValueError("aoi_id and bbox are required (via args or config)")

    bbox = bbox_raw if isinstance(bbox_raw, list) else normalize_bbox(bbox_raw)

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
    )

    logging.getLogger(__name__).info(f"Ingestion complete for {aoi_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
