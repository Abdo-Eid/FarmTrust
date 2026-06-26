"""ODC-backed Sentinel-2 cube loader — wraps odc.stac.load for FarmTrust ingest."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import odc.stac
import xarray as xr

DEFAULT_SENTINEL2_BANDS = ["B02", "B03", "B04", "B08", "B11", "SCL"]
SENTINEL2_BANDS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12", "SCL"]
ROOT_10M_BANDS = ["B02", "B03", "B04", "B08"]
NATIVE_20M_BANDS = ["B05", "B06", "B07", "B8A", "B11", "B12", "SCL"]
BAND_NATIVE_RESOLUTION: Dict[str, int] = {
    **{band: 10 for band in ROOT_10M_BANDS},
    **{band: 20 for band in NATIVE_20M_BANDS},
}

# Nearest-neighbor for categorical SCL; bilinear for all reflectance bands.
# This is the deciding factor for ODC over stackstac: stackstac applies one
# resampling kernel to all assets and cannot mix them in a single load call.
BAND_RESAMPLING: Dict[str, str] = {
    "B02": "bilinear",
    "B03": "bilinear",
    "B04": "bilinear",
    "B05": "bilinear",
    "B06": "bilinear",
    "B07": "bilinear",
    "B08": "bilinear",
    "B8A": "bilinear",
    "B11": "bilinear",
    "B12": "bilinear",
    "SCL": "nearest",
}

# Integer dtypes force raw DN output — odc.stac.load will NOT apply scale/offset
# from STAC raster:bands metadata when the output dtype is integer.
# Scaling is applied explicitly in cube_stats.apply_boa_offset().
BAND_DTYPE: Dict[str, str] = {
    "B02": "uint16",
    "B03": "uint16",
    "B04": "uint16",
    "B05": "uint16",
    "B06": "uint16",
    "B07": "uint16",
    "B08": "uint16",
    "B8A": "uint16",
    "B11": "uint16",
    "B12": "uint16",
    "SCL": "uint8",
}


def estimate_utm_epsg(lon: float, lat: float) -> str:
    """Estimate UTM CRS EPSG code from a centroid lon/lat pair."""
    zone = int((lon + 180) / 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return f"EPSG:{epsg}"


def load_day_cube(
    items: List[Any],
    aoi_bbox: List[float],
    crs: Optional[str] = None,
    resolution: int = 10,
    bands: Optional[List[str]] = None,
) -> xr.Dataset:
    """Load one solar-day's STAC items into a raw-DN xarray Dataset.

    The dataset has dimensions (time, y, x) if groupby produces multiple days,
    or (y, x) for a single day. Caller should index by time before passing to
    compute_day_stats().

    All bands are returned in raw DN (uint16/uint8). Scaling must be applied
    via cube_stats.apply_boa_offset() before computing indices.

    Args:
        items: Signed STAC items for a single solar day (all from same AOI).
        aoi_bbox: [min_lon, min_lat, max_lon, max_lat] in EPSG:4326.
        crs: Target CRS string (e.g. "EPSG:32636"). Defaults to centroid UTM.
        resolution: Output pixel resolution in CRS units (metres). Default 10m.
        bands: Sentinel-2 asset names to load. Defaults to MVP bands.
    """
    if crs is None:
        lon = (aoi_bbox[0] + aoi_bbox[2]) / 2
        lat = (aoi_bbox[1] + aoi_bbox[3]) / 2
        crs = estimate_utm_epsg(lon, lat)

    selected_bands = bands or DEFAULT_SENTINEL2_BANDS
    unknown = sorted(set(selected_bands) - set(SENTINEL2_BANDS))
    if unknown:
        raise ValueError(f"Unsupported Sentinel-2 band(s): {unknown}")

    ds = odc.stac.load(
        items,
        bands=selected_bands,
        crs=crs,
        resolution=resolution,
        bbox=aoi_bbox,
        resampling={band: BAND_RESAMPLING[band] for band in selected_bands},
        dtype={band: BAND_DTYPE[band] for band in selected_bands},
        groupby="solar_day",
    )
    return ds
