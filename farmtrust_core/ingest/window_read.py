"""Raster window reading, reprojection, and GeoTIFF output for AOI chips."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds
from rasterio.warp import reproject


def bbox_to_scene_crs(bbox_lonlat: List[float], dst_crs: str, src_crs: str = "EPSG:4326") -> List[float]:
    """
    Transform bbox from EPSG:4326 (lon/lat) to scene CRS (typically UTM via EPSG:326xx).

    Sentinel-2 assets are stored in UTM, not lon/lat. This conversion is required before
    computing the raster window from the AOI bbox. The always_xy=True flag ensures lon/lat
    argument order regardless of CRS axis convention.
    """
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
    Read AOI window from COG asset via HTTP range request.

    Reads only the AOI window, not the full tile (leverages Cloud Optimized GeoTIFF).
    Clips the computed window to tile bounds to avoid out-of-bounds reads.
    Returns empty array + None transform if the AOI falls entirely outside the tile.
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
    Reproject and resample source array to canonical chip grid.

    Sentinel-2 bands have different native resolutions: 10m for B02/B03/B04/B08,
    20m for SCL/B11. SCL defines the canonical grid. All bands must be resampled to it
    so the cloud mask aligns pixel-for-pixel with reflectance bands.
    The caller specifies the resampling method: bilinear for reflectance, nearest-neighbor
    for categorical data like SCL.
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
    """
    Write single-band GeoTIFF in the ChipGrid's CRS and affine transform.

    Uses tiled=True + deflate compression for COG-compatible efficiency.
    The predictor (delta filter) is applied only to float data (predictor=2);
    integer data uses predictor=1 to avoid false gains.
    """
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
