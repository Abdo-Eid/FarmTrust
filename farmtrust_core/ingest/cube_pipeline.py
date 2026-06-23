"""Cube-path AOI ingestion: two-phase pipeline over a pre-allocated Zarr cube.

Phase 1 — download_cubes:  STAC search → load_day_cube (HTTP) → region-write each
                           solar day into its slot in cube.zarr.
Phase 2 — process_cubes:   open cube.zarr → compute stats → emit indices_timeseries.csv.

Artifacts (siblings under output_dir):
  cube.zarr            — the source dataset: raw-DN pixels + per-day provenance.
                          Root stores the 10m grid/time/provenance; native 20m
                          bands live in the "20m" group. PRIMARY artifact.
  scenes_index.jsonl   — operational write-ahead ledger: one record per attempted
                         solar day {solar_day, cache_key, status, updated_at}.
                         Source of truth for which days are real in the cube.
  indices_timeseries.csv — derived export (downstream contract for preprocess/API).
  run_metadata.json    — run config (downstream contract; Phase 2 reads config here).

Time axis: a fresh cube is pre-allocated with the full sorted day list. Existing
cubes can append newly discovered days without rewriting old chunks, so the
physical on-disk time axis may become append-ordered after date-range backfill.
The JSONL ledger (not cube.time) is authoritative about which slices are real,
and Phase 2 sorts output rows by solar_day.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import dask.array as da
import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import xarray as xr
import zarr

from farmtrust_core.ingest.config import geometry_to_bbox, normalize_geometry
from farmtrust_core.ingest.cube_loader import (
    BAND_NATIVE_RESOLUTION,
    BAND_DTYPE,
    DEFAULT_SENTINEL2_BANDS,
    NATIVE_20M_BANDS,
    ROOT_10M_BANDS,
    SENTINEL2_BANDS,
    estimate_utm_epsg,
    load_day_cube,
)
from farmtrust_core.ingest.cube_stats import (
    OFFSET_POLICY,
    build_day_cache_key,
    compute_day_stats,
)
from farmtrust_core.ingest.utils import safe_write_text, utc_now_iso

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
STAC_COLLECTION = "sentinel-2-l2a"


class CubePipelineCancelledError(Exception):
    pass


class CubeRangeChangedError(Exception):
    """Raised when an existing cube/group cannot be incrementally extended."""


# Cube dataset schema id (provenance for the dataset asset).
_CUBE_SCHEMA = "g15f.cube.v2"
# v5 ledger: day state plus optional per-band state for repair/backfill.
_INDEX_SCHEMA = "g15f.scenes_index.v5.jsonl"
_NATIVE_20M_GROUP = "20m"

# Matches the MGRS tile token in Sentinel-2 item IDs: _T36RUU_
_MGRS_RE = re.compile(r"_T([0-9]{2}[A-Z]{3})_")

INVALID_SCL_CLASSES = {0, 1, 3, 7, 8, 9, 10, 11}

# Per-time string provenance variables stored in the cube.
_STR_PROV_VARS = ("source_item_ids", "mgrs_tiles")
_STR_PROV_DTYPE = "S4096"
# Derived per-time stats emitted to indices_timeseries.csv.
_STAT_VARS = (
    "valid_fraction",
    "ndvi_mean", "ndvi_p95",
    "evi_mean", "evi_p95",
    "ndmi_mean", "ndmi_p95",
    "ndwi_mean", "ndwi_p95",
    "mndwi_mean", "mndwi_p95",
)
# Per-time float variables stored in cube.zarr.
_FLOAT_TIME_VARS = ("min_cloud_cover",)

CSV_HEADERS = [
    "solar_day",
    # timestamp + item_id satisfy preprocess REQUIRED_COLUMNS without changing preprocessing.
    "timestamp",
    "item_id",
    "item_ids",
    "mgrs_tiles",
    "min_cloud_cover",
    "valid_fraction",
    "ndvi_mean", "ndvi_p95",
    "evi_mean", "evi_p95",
    "ndmi_mean", "ndmi_p95",
    "ndwi_mean", "ndwi_p95",
    "mndwi_mean", "mndwi_p95",
]


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------

def _mgrs_tile_from_item_id(item_id: str) -> str:
    """Extract MGRS tile from a Sentinel-2 item ID (e.g. S2B_..._T36RUU_... → '36RUU')."""
    m = _MGRS_RE.search(item_id)
    return m.group(1) if m else "unknown"


def _solar_day_timestamp(solar_day: str) -> str:
    return f"{solar_day}T00:00:00+00:00"


def _day_str(ts: Any) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _scalar_str(value: Any) -> str:
    """Read a 0-d xarray object/str value to a python str ('' for missing)."""
    try:
        v = value.item()
    except (AttributeError, ValueError):
        v = value
    if isinstance(v, bytes):
        return v.decode("utf-8").rstrip("\x00")
    return "" if v is None else str(v)


def _scalar_float(value: Any) -> float:
    try:
        return float(value.item())
    except (AttributeError, ValueError):
        return float(value)


# ---------------------------------------------------------------------------
# JSONL ledger helpers
# ---------------------------------------------------------------------------

def _load_index(path: Path) -> Dict[str, Any]:
    """Load scenes_index.jsonl into an in-memory dict (last-write-wins per solar_day)."""
    index: Dict[str, Any] = {"schema": _INDEX_SCHEMA, "created_at": utc_now_iso(), "days": {}}
    if not path.exists():
        return index
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rtype = rec.get("_type")
        if rtype == "meta":
            index.update({k: v for k, v in rec.items() if k != "_type"})
            index.setdefault("days", {})
        elif rtype == "day":
            solar_day = rec.get("solar_day")
            if solar_day:
                index["days"][solar_day] = rec
    return index


def _append_day_entry(path: Path, rec: Dict[str, Any]) -> None:
    """Append one day record. O(1); crash-safe."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"_type": "day", **rec}, sort_keys=True) + "\n")


def _write_index_meta(path: Path, meta: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"_type": "meta", **meta}, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Grouping and cache key
# ---------------------------------------------------------------------------

def _group_by_solar_day(items: List[Any]) -> Dict[str, List[Any]]:
    """Group STAC items by their solar_day (YYYY-MM-DD string)."""
    groups: Dict[str, List[Any]] = {}
    for item in items:
        if item.datetime:
            day = item.datetime.strftime("%Y-%m-%d")
        else:
            day = item.properties.get("datetime", "")[:10]
        groups.setdefault(day, []).append(item)
    return groups


def _day_cache_key(
    solar_day: str,
    aoi_geometry: Optional[Dict[str, Any]],
    bbox: List[float],
    crs: str,
    resolution: int,
    max_cloud: float,
) -> str:
    return build_day_cache_key(
        solar_day,
        aoi_geometry or {},
        crs,
        resolution,
        INVALID_SCL_CLASSES,
        max_cloud,
        aoi_bbox=list(bbox),
    )


def _normalize_bands(bands: Optional[List[str]]) -> List[str]:
    selected = bands or DEFAULT_SENTINEL2_BANDS
    normalized: List[str] = []
    for band in selected:
        b = str(band).strip()
        if not b:
            continue
        if b not in SENTINEL2_BANDS:
            raise ValueError(f"Unsupported Sentinel-2 band: {b}")
        if b not in normalized:
            normalized.append(b)
    return normalized


def _bands_for_resolution(bands: List[str], resolution: int) -> List[str]:
    return [band for band in bands if BAND_NATIVE_RESOLUTION[band] == resolution]


def _zarr_format_kwargs(zarr_path: Path) -> Dict[str, Any]:
    """Use v2 for new stores, but preserve an existing v3 store such as older demo data."""
    if (zarr_path / "zarr.json").exists():
        return {}
    return {"zarr_format": 2}


def _time_units_base(time_array: Any) -> Optional[pd.Timestamp]:
    attrs = time_array.attrs.asdict() if hasattr(time_array.attrs, "asdict") else dict(time_array.attrs)
    units = str(attrs.get("units", ""))
    if " since " not in units:
        return None
    unit, base = units.split(" since ", 1)
    if unit.strip() != "days":
        return None
    return pd.Timestamp(base)


def _encoded_time_values(time_array: Any, days: List[str]) -> np.ndarray:
    base = _time_units_base(time_array)
    if base is not None:
        return np.array([(pd.Timestamp(day) - base).days for day in days], dtype=time_array.dtype)
    return pd.to_datetime(days).values.astype(time_array.dtype, copy=False)


def _zarr_array_dims(arr: Any) -> List[str]:
    metadata_dims = getattr(getattr(arr, "metadata", None), "dimension_names", None)
    if metadata_dims:
        return list(metadata_dims)
    attrs = arr.attrs.asdict() if hasattr(arr.attrs, "asdict") else dict(arr.attrs)
    return list(attrs.get("_ARRAY_DIMENSIONS") or [])


def _append_time_slots(zarr_path: Path, group: Optional[str], days: List[str]) -> None:
    """Append empty time slots in-place without rewriting existing Zarr chunks."""
    if not days:
        return
    root = zarr.open_group(str(zarr_path), mode="a")
    zgroup = root if group is None else root[group]
    if "time" not in zgroup:
        raise CubeRangeChangedError(f"Cannot append days: {group or 'root'} group has no time axis.")

    old_len = int(zgroup["time"].shape[0])
    new_len = old_len + len(days)
    for name in list(zgroup.array_keys()):
        arr = zgroup[name]
        dims = _zarr_array_dims(arr)
        if not arr.shape or not dims or dims[0] != "time" or int(arr.shape[0]) != old_len:
            continue
        arr.resize((new_len, *arr.shape[1:]))

    zgroup["time"][old_len:new_len] = _encoded_time_values(zgroup["time"], days)
    for name in _STR_PROV_VARS:
        if name in zgroup:
            zgroup[name][old_len:new_len] = [""] * len(days)
    for name in _FLOAT_TIME_VARS:
        if name in zgroup:
            zgroup[name][old_len:new_len] = np.full((len(days),), np.nan, dtype=zgroup[name].dtype)


# ---------------------------------------------------------------------------
# Zarr cube helpers
# ---------------------------------------------------------------------------

def _grid_from_ds(ds: xr.Dataset) -> Tuple[np.ndarray, np.ndarray, Optional[xr.DataArray]]:
    """Extract (y_values, x_values, spatial_ref) from a loaded day Dataset."""
    spatial_ref = ds["spatial_ref"].load() if "spatial_ref" in ds.coords else None
    return ds["y"].values, ds["x"].values, spatial_ref


def _empty_cube_template(
    y_vals: np.ndarray,
    x_vals: np.ndarray,
    spatial_ref: Optional[xr.DataArray],
    days_sorted: List[str],
    attrs: Optional[Dict[str, Any]],
) -> xr.Dataset:
    """Build an empty cube spanning days_sorted on the given grid.

    Pixel bands are zero-filled, min_cloud NaN, provenance empty strings.
    Backed by dask + written with compute=False so no chunk data is materialised
    until region-writes fill each slot.
    """
    times = pd.to_datetime(list(days_sorted))
    t = len(times)
    ny = int(len(y_vals))
    nx = int(len(x_vals))

    data_vars: Dict[str, Any] = {}
    for band in ROOT_10M_BANDS:
        dtype = BAND_DTYPE[band]
        data_vars[band] = (
            ("time", "y", "x"),
            da.zeros((t, ny, nx), dtype=dtype, chunks=(1, ny, nx)),
        )
    for name in _STR_PROV_VARS:
        data_vars[name] = (("time",), np.array([""] * t, dtype=_STR_PROV_DTYPE))
    for name in _FLOAT_TIME_VARS:
        data_vars[name] = (("time",), da.full((t,), np.nan, dtype="float32", chunks=(1,)))

    ds = xr.Dataset(data_vars, coords={"time": times, "y": y_vals, "x": x_vals})
    if spatial_ref is not None:
        ds = ds.assign_coords(spatial_ref=spatial_ref)
    if attrs:
        ds.attrs.update(attrs)
    # One chunk per solar day for every time-indexed variable, so each day's
    # region-write touches a DISTINCT chunk file. A single shared chunk would be
    # rewritten once per day (262×), and on Windows the repeated atomic
    # tmp→replace eventually collides with a transient file lock (WinError 5).
    return ds.chunk({"time": 1})


def _empty_band_group_template(
    y_vals: np.ndarray,
    x_vals: np.ndarray,
    spatial_ref: Optional[xr.DataArray],
    days_sorted: List[str],
    bands: List[str],
    attrs: Optional[Dict[str, Any]],
) -> xr.Dataset:
    times = pd.to_datetime(list(days_sorted))
    t = len(times)
    ny = int(len(y_vals))
    nx = int(len(x_vals))
    data_vars: Dict[str, Any] = {}
    for band in bands:
        data_vars[band] = (
            ("time", "y", "x"),
            da.zeros((t, ny, nx), dtype=BAND_DTYPE[band], chunks=(1, ny, nx)),
        )
    ds = xr.Dataset(data_vars, coords={"time": times, "y": y_vals, "x": x_vals})
    if spatial_ref is not None:
        ds = ds.assign_coords(spatial_ref=spatial_ref)
    if attrs:
        ds.attrs.update(attrs)
    return ds.chunk({"time": 1})


def _ensure_cube(
    zarr_path: Path,
    grid: Tuple[np.ndarray, np.ndarray, Optional[xr.DataArray]],
    target_days_sorted: List[str],
    attrs: Optional[Dict[str, Any]],
) -> Dict[str, int]:
    """Ensure cube.zarr has slots for every target day; return day→index.

    Fresh cubes are sorted by time. Existing cubes append missing days at the end
    to avoid rewriting old chunks; Phase 2 sorts rows by solar_day.
    """
    y_vals, x_vals, spatial_ref = grid
    if not zarr_path.exists():
        template = _empty_cube_template(y_vals, x_vals, spatial_ref, target_days_sorted, attrs)
        template.to_zarr(
            str(zarr_path), mode="w", compute=False, consolidated=False,
            **_zarr_format_kwargs(zarr_path),
        )
        return {d: i for i, d in enumerate(target_days_sorted)}

    with xr.open_zarr(str(zarr_path), consolidated=False) as cube:
        existing = [_day_str(t) for t in cube.time.values]
    existing_set = set(existing)
    missing = [d for d in target_days_sorted if d not in existing_set]
    if missing:
        _append_time_slots(zarr_path, None, missing)
        existing.extend(missing)
    return {d: i for i, d in enumerate(existing)}


def _open_group(zarr_path: Path, group: str) -> Optional[xr.Dataset]:
    if not (zarr_path / group).exists():
        return None
    try:
        return xr.open_zarr(str(zarr_path), group=group, consolidated=False)
    except Exception:
        return None


def _ensure_band_group(
    zarr_path: Path,
    group: str,
    grid: Tuple[np.ndarray, np.ndarray, Optional[xr.DataArray]],
    target_days_sorted: List[str],
    bands: List[str],
    attrs: Optional[Dict[str, Any]],
) -> None:
    if not bands:
        return
    y_vals, x_vals, spatial_ref = grid
    group_path = zarr_path / group
    if not group_path.exists():
        template = _empty_band_group_template(y_vals, x_vals, spatial_ref, target_days_sorted, bands, attrs)
        template.to_zarr(
            str(zarr_path), group=group, mode="w", compute=False,
            consolidated=False, **_zarr_format_kwargs(zarr_path),
        )
        return

    with xr.open_zarr(str(zarr_path), group=group, consolidated=False) as existing:
        existing_vars = set(existing.data_vars)
        missing_bands = [band for band in bands if band not in existing_vars]
        existing_days = [_day_str(t) for t in existing.time.values]

    existing_day_set = set(existing_days)
    missing_days = [d for d in target_days_sorted if d not in existing_day_set]
    if missing_days:
        _append_time_slots(zarr_path, group, missing_days)
        existing_days.extend(missing_days)

    if existing_days != target_days_sorted:
        raise CubeRangeChangedError(
            f"The {group} group time axis differs from cube.zarr and cannot be safely appended."
        )

    if missing_bands:
        template = _empty_band_group_template(y_vals, x_vals, spatial_ref, target_days_sorted, missing_bands, attrs)
        template.to_zarr(
            str(zarr_path), group=group, mode="a", compute=False,
            consolidated=False, **_zarr_format_kwargs(zarr_path),
        )


def _to_zarr_region(
    out: xr.Dataset,
    zarr_path: Path,
    idx: int,
    attempts: int = 5,
    group: Optional[str] = None,
) -> None:
    """Region-write with retry on transient Windows file locks (os.replace WinError 5).

    Each chunk is written once, but antivirus/indexer can briefly hold a
    newly-written file during the atomic tmp→replace. Retry with short backoff.
    """
    last: Optional[BaseException] = None
    for k in range(attempts):
        try:
            out.to_zarr(
                str(zarr_path),
                group=group,
                region={"time": slice(idx, idx + 1)},
                consolidated=False,
                **_zarr_format_kwargs(zarr_path),
            )
            return
        except (PermissionError, OSError) as exc:
            last = exc
            time.sleep(0.3 * (k + 1))
    raise last  # type: ignore[misc]


def _region_write_day(
    zarr_path: Path,
    result: Dict[str, Any],
    idx: int,
    grid_shape: Tuple[int, int],
) -> None:
    """Region-write one downloaded day's pixels + provenance into time slot idx."""
    ds_day = result["ds_day"]
    ts = pd.Timestamp(result["solar_day"])
    payload: Dict[str, Any] = {}
    for band in ROOT_10M_BANDS:
        if band not in ds_day:
            continue
        arr = ds_day[band].values
        if arr.shape != grid_shape:
            raise ValueError(
                f"{result['solar_day']}: band {band} shape {arr.shape} != cube grid {grid_shape}"
            )
        payload[band] = (("time", "y", "x"), arr[np.newaxis, ...])
    payload["source_item_ids"] = (
        ("time",), np.array(["|".join(result["item_ids"])], dtype=_STR_PROV_DTYPE),
    )
    payload["mgrs_tiles"] = (
        ("time",), np.array(["|".join(result["mgrs_tiles"])], dtype=_STR_PROV_DTYPE),
    )
    payload["min_cloud_cover"] = (
        ("time",), np.array([result["min_cloud_cover"]], dtype="float32"),
    )
    out = xr.Dataset(payload, coords={"time": [ts]})
    _to_zarr_region(out, zarr_path, idx)


def _region_write_band_group(
    zarr_path: Path,
    group: str,
    result: Dict[str, Any],
    idx: int,
    grid_shape: Tuple[int, int],
    bands: List[str],
) -> None:
    ds_day = result["ds_day"]
    ts = pd.Timestamp(result["solar_day"])
    payload: Dict[str, Any] = {}
    for band in bands:
        if band not in ds_day:
            continue
        arr = ds_day[band].values
        if arr.shape != grid_shape:
            raise ValueError(
                f"{result['solar_day']}: band {band} shape {arr.shape} != {group} grid {grid_shape}"
            )
        payload[band] = (("time", "y", "x"), arr[np.newaxis, ...])
    if not payload:
        return
    out = xr.Dataset(payload, coords={"time": [ts]})
    _to_zarr_region(out, zarr_path, idx, group=group)


# ---------------------------------------------------------------------------
# Phase 1 worker
# ---------------------------------------------------------------------------

def _download_one_day(
    solar_day: str,
    day_items: List[Any],
    cache_key: str,
    bbox: List[float],
    crs: str,
    resolution: int,
    bands: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Load one solar day from COG assets (no stats). Returns numpy-backed ds_day.

    HTTP reads happen here, in the worker thread; .compute() forces them so the
    region-write under the lock is pure local disk.
    """
    logger = logging.getLogger(__name__)
    item_ids = [it.id for it in day_items]
    mgrs_tiles = sorted({_mgrs_tile_from_item_id(it.id) for it in day_items})
    min_cloud = min(
        (it.properties.get("eo:cloud_cover", float("nan")) for it in day_items),
        default=float("nan"),
    )
    try:
        selected_bands = bands or DEFAULT_SENTINEL2_BANDS
        ds = load_day_cube(day_items, bbox, crs=crs, resolution=resolution, bands=selected_bands)
        if "time" in ds.dims:
            ds_day = ds.isel(time=0).drop_vars("time", errors="ignore")
        else:
            ds_day = ds
        crs_wkt = str(ds.odc.crs.to_wkt())
        ds_day = ds_day.compute()
        return {
            "status": "downloaded",
            "solar_day": solar_day,
            "cache_key": cache_key,
            "item_ids": item_ids,
            "mgrs_tiles": mgrs_tiles,
            "min_cloud_cover": min_cloud,
            "crs_wkt": crs_wkt,
            "ds_day": ds_day,
            "bands": selected_bands,
        }
    except Exception as exc:
        logger.warning(f"{solar_day}: download failed — {exc}")
        return {
            "status": "error",
            "solar_day": solar_day,
            "cache_key": cache_key,
            "item_ids": item_ids,
            "mgrs_tiles": mgrs_tiles,
            "min_cloud_cover": min_cloud,
            "crs_wkt": None,
            "ds_day": None,
            "bands": bands or DEFAULT_SENTINEL2_BANDS,
            "error": str(exc),
        }


def _ledger_record(result: Dict[str, Any], bands: Optional[List[str]] = None) -> Dict[str, Any]:
    """Operational ledger record for an attempted day (no provenance/stats)."""
    rec = {
        "solar_day": result["solar_day"],
        "cache_key": result["cache_key"],
        "status": result["status"],
        "updated_at": utc_now_iso(),
    }
    if result.get("error"):
        rec["error"] = result["error"]
    if result["status"] == "downloaded":
        downloaded_bands = bands or result.get("bands") or []
        if downloaded_bands:
            rec["band_status"] = {band: "downloaded" for band in downloaded_bands}
    return rec


def _merge_ledger_record(existing: Optional[Dict[str, Any]], new_rec: Dict[str, Any]) -> Dict[str, Any]:
    if not existing:
        return new_rec
    merged = {**existing, **new_rec}
    band_status = dict(existing.get("band_status") or {})
    band_status.update(new_rec.get("band_status") or {})
    if band_status:
        merged["band_status"] = band_status
    return merged


def _band_vars_in_group(zarr_path: Path, group: str) -> set[str]:
    ds = _open_group(zarr_path, group)
    if ds is None:
        return set()
    try:
        return set(ds.data_vars)
    finally:
        ds.close()


def _backfill_20m_bands(
    *,
    zarr_path: Path,
    index_path: Path,
    day_index: Dict[str, Any],
    day_groups: Dict[str, List[Any]],
    target_days_sorted: List[str],
    requested_bands: List[str],
    bbox: List[float],
    crs: str,
    max_cloud: float,
    normalized_geometry: Optional[Dict[str, Any]],
    max_workers: int,
    cancel_check: Optional[Callable[[], bool]],
    on_progress: Optional[Callable[[int, int], None]],
) -> int:
    """Backfill missing native-20m bands without touching existing 10m bands."""
    logger = logging.getLogger(__name__)
    bands_20m = _bands_for_resolution(requested_bands, 20)
    if not bands_20m:
        return 0

    with xr.open_zarr(str(zarr_path), consolidated=False) as cube:
        index_map = {_day_str(t): i for i, t in enumerate(cube.time.values)}
        cube_days_order = [_day_str(t) for t in cube.time.values]
        root_attrs = dict(cube.attrs)

    existing_vars = _band_vars_in_group(zarr_path, _NATIVE_20M_GROUP)
    work: List[Tuple[str, List[Any], str, List[str]]] = []
    for solar_day in target_days_sorted:
        if solar_day not in index_map:
            continue
        stored = day_index["days"].get(solar_day, {})
        if stored.get("status") not in ("downloaded", "ok"):
            continue
        cache_key = _day_cache_key(solar_day, normalized_geometry, bbox, crs, 10, max_cloud)
        band_status = stored.get("band_status") or {}
        missing = [
            band for band in bands_20m
            if band not in existing_vars
            or stored.get("cache_key") != cache_key
            or band_status.get(band) != "downloaded"
        ]
        if missing:
            work.append((solar_day, day_groups[solar_day], cache_key, missing))

    if not work:
        logger.info("No 20m band backfill needed.")
        return 0

    logger.info(f"Backfilling native 20m bands for {len(work)} day(s).")
    bootstrap: Optional[Tuple[Dict[str, Any], List[str]]] = None
    remaining = list(work)

    if not (zarr_path / _NATIVE_20M_GROUP).exists():
        while remaining:
            if cancel_check and cancel_check():
                raise CubePipelineCancelledError("Cancelled")
            day, day_items, key, missing = remaining.pop(0)
            res = _download_one_day(day, day_items, key, bbox, crs, 20, bands=missing)
            if res["status"] == "downloaded":
                bootstrap = (res, missing)
                break
            rec = _ledger_record(res, bands=[])
            merged = _merge_ledger_record(day_index["days"].get(day), rec)
            day_index["days"][day] = merged
            _append_day_entry(index_path, merged)
        if bootstrap is None:
            logger.warning("20m band backfill failed before a grid could be established.")
            return 0
        grid = _grid_from_ds(bootstrap[0]["ds_day"])
        attrs = {
            **root_attrs,
            "schema": f"{_CUBE_SCHEMA}.20m",
            "resolution": 20,
            "native_resolution": 20,
        }
        _ensure_band_group(zarr_path, _NATIVE_20M_GROUP, grid, cube_days_order, bands_20m, attrs)
    else:
        with xr.open_zarr(str(zarr_path), group=_NATIVE_20M_GROUP, consolidated=False) as group_ds:
            grid = (
                group_ds["y"].values,
                group_ds["x"].values,
                group_ds["spatial_ref"].load() if "spatial_ref" in group_ds.coords else None,
            )
        attrs = {
            **root_attrs,
            "schema": f"{_CUBE_SCHEMA}.20m",
            "resolution": 20,
            "native_resolution": 20,
        }
        _ensure_band_group(zarr_path, _NATIVE_20M_GROUP, grid, cube_days_order, bands_20m, attrs)

    with xr.open_zarr(str(zarr_path), group=_NATIVE_20M_GROUP, consolidated=False) as group_ds:
        group_shape = (int(group_ds.sizes["y"]), int(group_ds.sizes["x"]))

    written = 0
    lock = threading.Lock()

    def _record_success(result: Dict[str, Any], bands: List[str]) -> None:
        nonlocal written
        solar_day = result["solar_day"]
        _region_write_band_group(
            zarr_path, _NATIVE_20M_GROUP, result, index_map[solar_day], group_shape, bands,
        )
        rec = _ledger_record(result, bands=bands)
        merged = _merge_ledger_record(day_index["days"].get(solar_day), rec)
        day_index["days"][solar_day] = merged
        _append_day_entry(index_path, merged)
        written += 1

    done = 0
    total = len(work)
    if bootstrap is not None:
        res, bands = bootstrap
        _record_success(res, bands)
        done += 1
        if on_progress:
            on_progress(done, total)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_download_one_day, day, day_items, key, bbox, crs, 20, bands=missing): (day, missing)
            for day, day_items, key, missing in remaining
        }
        for future in as_completed(futures):
            if cancel_check and cancel_check():
                raise CubePipelineCancelledError("Cancelled")
            day, missing = futures[future]
            result = future.result()
            with lock:
                if result["status"] == "downloaded":
                    _record_success(result, missing)
                else:
                    rec = _ledger_record(result, bands=[])
                    merged = _merge_ledger_record(day_index["days"].get(day), rec)
                    day_index["days"][day] = merged
                    _append_day_entry(index_path, merged)
                done += 1
                logger.info(f"Backfilled {day} {','.join(missing)} → {result['status']}")
                if on_progress:
                    on_progress(done, total)
    return written


# ---------------------------------------------------------------------------
# Phase 1: Download
# ---------------------------------------------------------------------------

def download_cubes(
    output_dir: Path,
    aoi_id: str,
    bbox: List[float],
    start_date: str,
    end_date: str,
    max_cloud: float,
    force_rerun: bool,
    limit_items: Optional[int] = None,
    log_signed_hrefs: bool = False,
    resolution: int = 10,
    crs: Optional[str] = None,
    geometry: Optional[Dict[str, Any]] = None,
    bands: Optional[List[str]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    max_workers: int = 6,
) -> None:
    """Phase 1: STAC search → region-write each solar day into a pre-allocated cube.zarr."""
    logger = logging.getLogger(__name__)
    requested_bands = _normalize_bands(bands)
    root_bands = _bands_for_resolution(requested_bands, 10)
    normalized_geometry = normalize_geometry(geometry) if geometry else None
    if normalized_geometry:
        bbox = geometry_to_bbox(normalized_geometry)

    if output_dir.exists() and force_rerun:
        logger.info(f"Clearing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    zarr_path = output_dir / "cube.zarr"
    index_path = output_dir / "scenes_index.jsonl"
    metadata_path = output_dir / "run_metadata.json"

    if crs is None:
        lon = (bbox[0] + bbox[2]) / 2
        lat = (bbox[1] + bbox[3]) / 2
        crs = estimate_utm_epsg(lon, lat)

    logger.info(
        f"Cube download for {aoi_id}: {start_date} → {end_date}, CRS={crs}, "
        f"bands={','.join(requested_bands)}"
    )

    catalog = pystac_client.Client.open(STAC_URL, modifier=pc.sign_inplace)
    search = catalog.search(
        collections=[STAC_COLLECTION],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        query={"eo:cloud_cover": {"lt": float(max_cloud)}},
    )
    items = sorted(list(search.items()), key=lambda x: x.datetime)
    if limit_items is not None:
        items = items[: int(limit_items)]
    logger.info(f"Found {len(items)} STAC items")

    day_groups = _group_by_solar_day(items)
    target_days_sorted = sorted(day_groups.keys())
    logger.info(f"{len(target_days_sorted)} solar days after grouping")

    # Ledger setup (create meta line on first use).
    is_new_index = not index_path.exists()
    day_index = _load_index(index_path)
    if is_new_index:
        _write_index_meta(index_path, {
            "schema": _INDEX_SCHEMA,
            "created_at": day_index.get("created_at", utc_now_iso()),
            "aoi_id": aoi_id,
        })

    # Classify days: skip those already downloaded/ok with a matching cache key.
    # (No cube-membership term: pre-allocation makes every slot exist immediately,
    #  so "in cube" is vacuous; the JSONL status is authoritative.)
    work: List[Tuple[str, List[Any], str]] = []
    skipped = 0
    existing_root_vars: set[str] = set()
    cube_config_matches = False
    if zarr_path.exists():
        try:
            with xr.open_zarr(str(zarr_path), consolidated=False) as c:
                existing_root_vars = set(c.data_vars)
                cube_config_matches = (
                    list(c.attrs.get("bbox", [])) == list(bbox)
                    and c.attrs.get("aoi_geometry") == normalized_geometry
                    and c.attrs.get("crs") == crs
                    and int(c.attrs.get("resolution", resolution)) == int(resolution)
                    and float(c.attrs.get("max_cloud", max_cloud)) == float(max_cloud)
                )
        except Exception:
            existing_root_vars = set()

    for solar_day in target_days_sorted:
        cache_key = _day_cache_key(solar_day, normalized_geometry, bbox, crs, resolution, max_cloud)
        stored = day_index["days"].get(solar_day)
        root_missing = [band for band in root_bands if band not in existing_root_vars]
        cache_current = stored and stored.get("cache_key") == cache_key
        if (
            stored and (cache_current or cube_config_matches)
            and stored.get("status") in ("downloaded", "ok")
            and not root_missing
        ):
            skipped += 1
        else:
            work.append((solar_day, day_groups[solar_day], cache_key))

    # Run config — downstream contract; also Phase 2's config read path.
    crs_wkt = ""
    cube_exists = zarr_path.exists()
    if cube_exists:
        try:
            with xr.open_zarr(str(zarr_path), consolidated=False) as c:
                crs_wkt = c.attrs.get("crs_wkt", "") or crs
        except Exception:
            pass

    def _write_run_metadata(extra: Optional[Dict[str, Any]] = None) -> None:
        meta: Dict[str, Any] = {
            "schema": "g15f.run_metadata.v2",
            "aoi_id": aoi_id,
            "bbox": list(bbox),
            "geometry": normalized_geometry,
            "start_date": start_date,
            "end_date": end_date,
            "max_cloud": float(max_cloud),
            "loader": "odc-stac",
            "offset_policy": OFFSET_POLICY,
            "crs": crs,
            "crs_wkt": crs_wkt,
            "resolution": resolution,
            "bands_requested": requested_bands,
            "bands_root_10m": root_bands,
            "bands_native_20m": _bands_for_resolution(requested_bands, 20),
            "invalid_scl_classes": sorted(INVALID_SCL_CLASSES),
            "mode": "cube-zarr",
            "created_at": utc_now_iso(),
            "outputs": {
                "cube_zarr": zarr_path.as_posix(),
                "scenes_index_jsonl": index_path.as_posix(),
                "csv": (output_dir / "indices_timeseries.csv").as_posix(),
            },
            "notes": (
                "Solar-day cube stored as cube.zarr (raw DN pixels + provenance; "
                "10m root plus native 20m group). process_cubes() emits derived indices_timeseries.csv."
            ),
        }
        if extra:
            meta.update(extra)
        safe_write_text(metadata_path, json.dumps(meta, indent=2, sort_keys=True))

    _write_run_metadata()

    if not work:
        logger.info(f"Nothing to download: {skipped} day(s) already current.")
        backfilled = _backfill_20m_bands(
            zarr_path=zarr_path, index_path=index_path, day_index=day_index,
            day_groups=day_groups, target_days_sorted=target_days_sorted,
            requested_bands=requested_bands, bbox=bbox, crs=crs, max_cloud=max_cloud,
            normalized_geometry=normalized_geometry, max_workers=max_workers,
            cancel_check=cancel_check, on_progress=on_progress,
        ) if zarr_path.exists() else 0
        _write_run_metadata({"download_completed_at": utc_now_iso()})
        if backfilled:
            _write_run_metadata({
                "backfilled_band_day_count": backfilled,
                "download_completed_at": utc_now_iso(),
            })
        return

    logger.info(f"{skipped} already current, {len(work)} to download")
    total = len(work)
    done_count = 0
    lock = threading.Lock()

    # --- Establish grid + ensure cube exists ---
    index_map: Dict[str, int]
    bootstrap: Optional[Dict[str, Any]] = None
    remaining = list(work)

    if cube_exists:
        with xr.open_zarr(str(zarr_path), consolidated=False) as c:
            grid = (c["y"].values, c["x"].values,
                    c["spatial_ref"].load() if "spatial_ref" in c.coords else None)
        index_map = _ensure_cube(zarr_path, grid, target_days_sorted, attrs=None)
    else:
        # Bootstrap: load days sequentially until one succeeds, to establish the grid.
        while remaining:
            if cancel_check and cancel_check():
                raise CubePipelineCancelledError("Cancelled")
            day, day_items, key = remaining[0]
            res = _download_one_day(day, day_items, key, bbox, crs, resolution, bands=root_bands)
            if res["status"] == "downloaded":
                bootstrap = res
                remaining.pop(0)
                break
            rec = _ledger_record(res, bands=[])
            merged = _merge_ledger_record(day_index["days"].get(day), rec)
            day_index["days"][day] = merged
            _append_day_entry(index_path, merged)
            remaining.pop(0)
            done_count += 1
            if on_progress:
                on_progress(done_count, total)
        if bootstrap is None:
            logger.error("All downloads failed; no cube created.")
            _write_run_metadata({"download_completed_at": utc_now_iso()})
            return
        crs_wkt = bootstrap["crs_wkt"]
        attrs = {
            "schema": _CUBE_SCHEMA,
            "aoi_id": aoi_id,
            "bbox": list(bbox),
            "aoi_geometry": normalized_geometry,
            "start_date": start_date,
            "end_date": end_date,
            "max_cloud": float(max_cloud),
            "crs": crs,
            "crs_wkt": crs_wkt,
            "resolution": resolution,
            "invalid_scl_classes": sorted(INVALID_SCL_CLASSES),
            "offset_policy": OFFSET_POLICY,
            "loader": "odc-stac",
            "bands_requested": requested_bands,
            "bands_root_10m": root_bands,
            "bands_native_20m": _bands_for_resolution(requested_bands, 20),
            "collection": STAC_COLLECTION,
            "stac_endpoint": STAC_URL,
            "created_at": utc_now_iso(),
        }
        grid = _grid_from_ds(bootstrap["ds_day"])
        index_map = _ensure_cube(zarr_path, grid, target_days_sorted, attrs)
        _write_run_metadata()  # refresh now that crs_wkt is known
        # Write the bootstrap day.
        boot_shape = (int(len(grid[0])), int(len(grid[1])))
        _region_write_day(zarr_path, bootstrap, index_map[bootstrap["solar_day"]], boot_shape)
        rec = _ledger_record(bootstrap, bands=root_bands)
        merged = _merge_ledger_record(day_index["days"].get(bootstrap["solar_day"]), rec)
        day_index["days"][bootstrap["solar_day"]] = merged
        _append_day_entry(index_path, merged)
        done_count += 1
        logger.info(f"Downloaded {bootstrap['solar_day']} → downloaded")
        if on_progress:
            on_progress(done_count, total)

    # --- Parallel download + region-write of remaining days ---
    with xr.open_zarr(str(zarr_path), consolidated=False) as c:
        grid_shape = (int(c.sizes["y"]), int(c.sizes["x"]))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_download_one_day, day, day_items, key, bbox, crs, resolution, bands=root_bands): day
            for day, day_items, key in remaining
        }
        for future in as_completed(futures):
            if cancel_check and cancel_check():
                raise CubePipelineCancelledError("Cancelled")
            result = future.result()
            solar_day = result["solar_day"]
            with lock:
                if result["status"] == "downloaded":
                    _region_write_day(
                        zarr_path, result, index_map[solar_day], grid_shape,
                    )
                rec = _ledger_record(result, bands=root_bands if result["status"] == "downloaded" else [])
                merged = _merge_ledger_record(day_index["days"].get(solar_day), rec)
                day_index["days"][solar_day] = merged
                _append_day_entry(index_path, merged)
                done_count += 1
                logger.info(f"Downloaded {solar_day} → {result['status']}")
                if on_progress:
                    on_progress(done_count, total)

    downloaded = sum(
        1 for d in day_index["days"].values() if d.get("status") in ("downloaded", "ok")
    )
    backfilled = _backfill_20m_bands(
        zarr_path=zarr_path, index_path=index_path, day_index=day_index,
        day_groups=day_groups, target_days_sorted=target_days_sorted,
        requested_bands=requested_bands, bbox=bbox, crs=crs, max_cloud=max_cloud,
        normalized_geometry=normalized_geometry, max_workers=max_workers,
        cancel_check=cancel_check, on_progress=on_progress,
    )

    _write_run_metadata({
        "downloaded_solar_day_count": downloaded,
        "backfilled_band_day_count": backfilled,
        "download_completed_at": utc_now_iso(),
    })
    logger.info(f"Download done: {downloaded} solar days in cube.zarr")


# ---------------------------------------------------------------------------
# Phase 2: Process
# ---------------------------------------------------------------------------

def _build_csv_row(solar_day: str, slice_ds: xr.Dataset, stats: Dict[str, Any]) -> List[Any]:
    item_ids_str = _scalar_str(slice_ds["source_item_ids"])
    mgrs_str = _scalar_str(slice_ds["mgrs_tiles"])
    min_cloud = _scalar_float(slice_ds["min_cloud_cover"])
    item_ids = item_ids_str.split("|") if item_ids_str else []
    return [
        solar_day,
        _solar_day_timestamp(solar_day),
        item_ids[0] if item_ids else "",
        item_ids_str,
        mgrs_str,
        min_cloud,
        stats.get("valid_fraction", float("nan")),
        stats.get("ndvi_mean", float("nan")), stats.get("ndvi_p95", float("nan")),
        stats.get("evi_mean", float("nan")), stats.get("evi_p95", float("nan")),
        stats.get("ndmi_mean", float("nan")), stats.get("ndmi_p95", float("nan")),
        stats.get("ndwi_mean", float("nan")), stats.get("ndwi_p95", float("nan")),
        stats.get("mndwi_mean", float("nan")), stats.get("mndwi_p95", float("nan")),
    ]


def _merge_native_20m_for_stats(root_day: xr.Dataset, native_20m_day: Optional[xr.Dataset]) -> xr.Dataset:
    """Return a stats-ready day slice on the root grid.

    Source storage keeps 20m bands native to save space. The current stats code
    operates on one grid, so align only the needed 20m bands in memory.
    """
    if native_20m_day is None:
        return root_day
    out = root_day.copy()
    if "B11" in native_20m_day:
        out["B11"] = _nearest_align_to_root(native_20m_day["B11"], root_day).astype(BAND_DTYPE["B11"])
    if "SCL" in native_20m_day:
        out["SCL"] = _nearest_align_to_root(native_20m_day["SCL"], root_day).astype(BAND_DTYPE["SCL"])
    return out


def _nearest_align_to_root(source: xr.DataArray, root_day: xr.Dataset) -> xr.DataArray:
    src_x = np.asarray(source["x"].values, dtype=float)
    src_y = np.asarray(source["y"].values, dtype=float)
    dst_x = np.asarray(root_day["x"].values, dtype=float)
    dst_y = np.asarray(root_day["y"].values, dtype=float)
    x_idx = np.abs(src_x[:, np.newaxis] - dst_x[np.newaxis, :]).argmin(axis=0)
    y_idx = np.abs(src_y[:, np.newaxis] - dst_y[np.newaxis, :]).argmin(axis=0)
    aligned = np.asarray(source.values)[np.ix_(y_idx, x_idx)]
    return xr.DataArray(aligned, coords={"y": root_day["y"], "x": root_day["x"]}, dims=("y", "x"))


def process_cubes(
    output_dir: Path,
    cancel_check: Optional[Callable[[], bool]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Phase 2: open cube.zarr → compute stats → CSV export.

    Ledger-driven: only days the JSONL confirms (status 'downloaded' or legacy
    'ok') are emitted. Phantom zero-filled slots (failed or cancelled downloads)
    are never processed. Config is read from run_metadata.json.
    """
    logger = logging.getLogger(__name__)

    zarr_path = output_dir / "cube.zarr"
    index_path = output_dir / "scenes_index.jsonl"
    csv_path = output_dir / "indices_timeseries.csv"
    metadata_path = output_dir / "run_metadata.json"

    if not zarr_path.exists():
        logger.warning("No cube.zarr found — writing empty indices_timeseries.csv.")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(CSV_HEADERS)
        return
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"run_metadata.json not found at {metadata_path}. Run download_cubes() first."
        )

    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    geometry: Optional[Dict[str, Any]] = meta.get("geometry")
    bbox: List[float] = list(meta["bbox"])
    crs: str = meta["crs"]
    resolution: int = meta["resolution"]
    max_cloud: float = meta["max_cloud"]
    invalid_scl = set(meta.get("invalid_scl_classes", sorted(INVALID_SCL_CLASSES)))

    day_index = _load_index(index_path)
    cube = xr.open_zarr(str(zarr_path), consolidated=False)  # on-disk order
    native_20m = _open_group(zarr_path, _NATIVE_20M_GROUP)
    crs_wkt: str = cube.attrs.get("crs_wkt", "") or meta.get("crs_wkt", "") or crs
    day_to_idx: Dict[str, int] = {_day_str(t): i for i, t in enumerate(cube.time.values)}

    ledger_days = sorted(day_index["days"].items())
    to_process = [
        (d, r) for d, r in ledger_days
        if r.get("status") in ("downloaded", "ok") and d in day_to_idx
    ]
    total = len(to_process)
    logger.info(f"{total} confirmed day(s) in ledger to process")

    rows: List[List[Any]] = []
    done = 0
    computed = 0

    for solar_day, rec in to_process:
        if cancel_check and cancel_check():
            raise CubePipelineCancelledError("Cancelled")

        i = day_to_idx[solar_day]
        cache_key = _day_cache_key(solar_day, geometry, bbox, crs, resolution, max_cloud)

        # Always compute derived stats from source pixels. cube.zarr intentionally
        # stores reusable source data, not processing-policy-dependent stats.
        ds_day_root = cube.isel(time=i).compute()
        ds_day_20m = native_20m.isel(time=i).compute() if native_20m is not None else None
        ds_day = _merge_native_20m_for_stats(ds_day_root, ds_day_20m)
        stats = compute_day_stats(
            ds_day, aoi_geometry=geometry, invalid_scl_classes=invalid_scl, crs_wkt=crs_wkt,
        )
        if stats is None:
            new_rec = {
                "solar_day": solar_day, "cache_key": cache_key,
                "status": "empty_aoi", "updated_at": utc_now_iso(),
            }
            day_index["days"][solar_day] = new_rec
            _append_day_entry(index_path, new_rec)
            logger.warning(f"{solar_day}: AOI has zero pixels on grid, skipping")
            done += 1
            if on_progress:
                on_progress(done, total)
            continue

        rows.append(_build_csv_row(solar_day, ds_day, stats))
        computed += 1
        done += 1
        logger.info(f"Processed {solar_day} → ok")
        if on_progress:
            on_progress(done, total)

    rows.sort(key=lambda r: r[0])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADERS)
        writer.writerows(rows)

    meta["processed_solar_day_count"] = len(rows)
    meta["newly_computed_count"] = computed
    meta["process_completed_at"] = utc_now_iso()
    safe_write_text(metadata_path, json.dumps(meta, indent=2, sort_keys=True))
    logger.info(f"Process done: {len(rows)} solar-day rows → {csv_path}")


# ---------------------------------------------------------------------------
# Combined entry point (backwards-compatible)
# ---------------------------------------------------------------------------

def write_cube_outputs(
    output_dir: Path,
    aoi_id: str,
    bbox: List[float],
    start_date: str,
    end_date: str,
    max_cloud: float,
    force_rerun: bool,
    limit_items: Optional[int] = None,
    log_signed_hrefs: bool = False,
    resolution: int = 10,
    crs: Optional[str] = None,
    geometry: Optional[Dict[str, Any]] = None,
    bands: Optional[List[str]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    max_workers: int = 6,
) -> None:
    """Run both phases in sequence. Callers needing phase-level control call
    download_cubes() and process_cubes() directly."""
    download_cubes(
        output_dir=output_dir, aoi_id=aoi_id, bbox=bbox,
        start_date=start_date, end_date=end_date, max_cloud=max_cloud,
        force_rerun=force_rerun, limit_items=limit_items,
        log_signed_hrefs=log_signed_hrefs, resolution=resolution, crs=crs,
        geometry=geometry, bands=bands,
        on_progress=on_progress, cancel_check=cancel_check,
        max_workers=max_workers,
    )
    process_cubes(output_dir=output_dir, cancel_check=cancel_check, on_progress=on_progress)
