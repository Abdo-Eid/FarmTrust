"""BOA scaling, AOI masking, and per-solar-day statistics — no network I/O."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Set, Tuple

import numpy as np
import xarray as xr
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom

from farmtrust_core.ingest.indices import (
    compute_evi,
    compute_mndwi,
    compute_ndmi,
    compute_ndvi,
    compute_ndwi,
)

# Sentinel-2 processing baseline 04.00 (Jan 2022):
#   BOA_ADD_OFFSET = -1000  →  surface reflectance = (DN - 1000) / 10000
# DN=0 is NODATA in this baseline — not a valid surface observation.
BOA_NODATA_DN = 0
BOA_ADD_OFFSET = 1000
BOA_SCALE = 10000
OFFSET_POLICY = "boa_baseline_04_00"


def apply_boa_offset(arr: np.ndarray) -> np.ndarray:
    """Convert raw Sentinel-2 DN to surface reflectance: (DN - 1000) / 10000.

    DN=0 is NODATA and is mapped to NaN before arithmetic so it cannot bias
    index means. Output dtype is float32.
    """
    out = arr.astype(np.float32)
    out = np.where(out == BOA_NODATA_DN, np.nan, out)
    return (out - BOA_ADD_OFFSET) / BOA_SCALE


def build_day_cache_key(
    solar_day: str,
    aoi_geometry: Dict[str, Any],
    crs: str,
    resolution: int,
    invalid_scl_classes: Set[int],
    max_cloud: float,
    aoi_bbox: Optional[list[float]] = None,
) -> str:
    """Stable SHA-256 cache key for one solar-day mosaic.

    Excludes start_date/end_date — those select the window but do not change
    any individual day's output. Changing the offset_policy, geometry, or bbox
    produces a different key, preventing stale source pixels from being reused.
    """
    payload = {
        "solar_day": solar_day,
        "aoi_geometry": aoi_geometry,
        "aoi_bbox": aoi_bbox,
        "crs": crs,
        "resolution": resolution,
        "invalid_scl_classes": sorted(invalid_scl_classes),
        "max_cloud": float(max_cloud),
        "offset_policy": OFFSET_POLICY,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def make_aoi_mask(
    geometry_wgs84: Dict[str, Any],
    crs_wkt: str,
    transform: Any,
    height: int,
    width: int,
) -> np.ndarray:
    """Rasterize WGS84 AOI polygon onto a grid. Returns bool mask (True = inside AOI)."""
    geom_proj = transform_geom("EPSG:4326", crs_wkt, geometry_wgs84)
    outside = geometry_mask(
        [geom_proj],
        out_shape=(height, width),
        transform=transform,
        invert=False,
    )
    return ~outside


def derive_transform(ds_day: xr.Dataset) -> Any:
    """Derive an affine transform from odc-loaded coordinate arrays.

    odc.stac.load places coordinate values at pixel centers. The affine
    UL-corner is shifted back by half a pixel so rasterio operations
    produce the correct alignment.
    """
    from affine import Affine

    x_coords = ds_day.coords["x"].values
    y_coords = ds_day.coords["y"].values
    x_res = float(x_coords[1] - x_coords[0]) if len(x_coords) > 1 else 10.0
    y_res = float(y_coords[1] - y_coords[0]) if len(y_coords) > 1 else -10.0
    x0 = float(x_coords[0]) - x_res / 2
    y0 = float(y_coords[0]) - y_res / 2
    return Affine(x_res, 0.0, x0, 0.0, y_res, y0)


def compute_day_stats(
    ds_day: xr.Dataset,
    aoi_geometry: Optional[Dict[str, Any]],
    invalid_scl_classes: Set[int],
    crs_wkt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Compute per-AOI stats for one solar-day Dataset slice (no time dimension).

    ds_day must have variables B02, B03, B04, B08, B11, SCL as 2D (y, x) arrays
    in raw DN (uint16/uint8). Scaling is applied here via apply_boa_offset().

    aoi_geometry: WGS84 Polygon dict, or None (use whole grid).
    crs_wkt: CRS of the dataset — required when aoi_geometry is not None.
    Returns None when the AOI has zero pixels on this grid (empty intersection).
    """
    height = ds_day.sizes["y"]
    width = ds_day.sizes["x"]

    scl = ds_day["SCL"].values.astype(np.uint8)
    invalid_mask = np.isin(scl, list(invalid_scl_classes))

    if aoi_geometry is not None and crs_wkt is not None:
        transform = derive_transform(ds_day)
        aoi_mask = make_aoi_mask(aoi_geometry, crs_wkt, transform, height, width)
    else:
        aoi_mask = np.ones((height, width), dtype=bool)

    denominator = int(aoi_mask.sum())
    if denominator == 0:
        return None

    valid_mask = (~invalid_mask) & aoi_mask
    valid_fraction = float(valid_mask.sum() / denominator)

    b02 = apply_boa_offset(ds_day["B02"].values)
    b03 = apply_boa_offset(ds_day["B03"].values)
    b04 = apply_boa_offset(ds_day["B04"].values)
    b08 = apply_boa_offset(ds_day["B08"].values)
    b11 = apply_boa_offset(ds_day["B11"].values)

    # Zero out pixels outside AOI so they don't skew index arithmetic
    out_of_aoi = ~aoi_mask
    for arr in (b02, b03, b04, b08, b11):
        arr[out_of_aoi] = np.nan

    ndvi_mean, ndvi_p95 = compute_ndvi(b04, b08, valid_mask)
    evi_mean, evi_p95 = compute_evi(b02, b04, b08, valid_mask)
    ndmi_mean, ndmi_p95 = compute_ndmi(b08, b11, valid_mask)
    ndwi_mean, ndwi_p95 = compute_ndwi(b03, b08, valid_mask)
    mndwi_mean, mndwi_p95 = compute_mndwi(b03, b11, valid_mask)

    return {
        "valid_fraction": valid_fraction,
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
    }
