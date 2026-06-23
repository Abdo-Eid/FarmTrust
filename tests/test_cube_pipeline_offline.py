"""Offline integration tests for the two-phase cube pipeline.

Mocks the network seam (STAC catalog + load_day_cube) so download_cubes and
process_cubes can be exercised end-to-end without credentials: pre-allocation,
out-of-order region-writes landing sorted, and ledger-driven Phase 2.
"""

from __future__ import annotations

import csv
import shutil
from datetime import datetime, timezone

import numpy as np
import odc.geo.xr  # noqa: F401  registers the .odc accessor
import pandas as pd
import pytest
import xarray as xr
from rasterio.warp import transform_geom

from farmtrust_core.ingest import cube_pipeline as cp

_DAYS = ["2024-06-21", "2024-06-01", "2024-06-11"]  # deliberately unsorted
_GRID_Y, _GRID_X = 4, 5


class _FakeItem:
    def __init__(self, item_id: str, dt: datetime, cloud: float):
        self.id = item_id
        self.datetime = dt
        self.properties = {"eo:cloud_cover": cloud}


class _FakeSearch:
    def __init__(self, items):
        self._items = items

    def items(self):
        return list(self._items)


class _FakeCatalog:
    def __init__(self, items):
        self._items = items

    def search(self, **_kwargs):
        return _FakeSearch(self._items)


def _make_day_ds(b08_dn: int, bands=None, resolution: int = 10) -> xr.Dataset:
    # North-up grid (y descending), matching real odc.stac.load output.
    bands = bands or ["B02", "B03", "B04", "B08", "B11", "SCL"]
    grid_y = _GRID_Y if resolution == 10 else 2
    grid_x = _GRID_X if resolution == 10 else 3
    y = np.arange(grid_y, dtype=float) * -float(resolution) + 1_000_000.0
    x = np.arange(grid_x, dtype=float) * float(resolution) + 500_000.0

    def band(val, dtype):
        return (("y", "x"), np.full((grid_y, grid_x), val, dtype=dtype))

    all_vars = {
        "B02": band(1500, np.uint16),
        "B03": band(2000, np.uint16),
        "B04": band(1500, np.uint16),
        "B05": band(1800, np.uint16),
        "B06": band(1900, np.uint16),
        "B07": band(2100, np.uint16),
        "B08": band(b08_dn, np.uint16),
        "B8A": band(6200, np.uint16),
        "B11": band(2000, np.uint16),
        "SCL": band(4, np.uint8),  # 4 = vegetation, valid
    }
    ds = xr.Dataset({b: all_vars[b] for b in bands}, coords={"y": y, "x": x})
    return ds.odc.assign_crs("EPSG:32636")


@pytest.fixture
def patched(monkeypatch):
    """Patch the STAC catalog and load_day_cube; return per-day b08 map for asserts."""
    items = [
        _FakeItem(
            f"S2B_MSIL2A_{d.replace('-', '')}T082559_R021_T36RUU_x",
            datetime.fromisoformat(d).replace(tzinfo=timezone.utc),
            cloud=float(i),
        )
        for i, d in enumerate(_DAYS)
    ]
    monkeypatch.setattr(
        cp.pystac_client.Client, "open",
        staticmethod(lambda *a, **k: _FakeCatalog(items)),
    )
    # Distinct B08 per day so we can verify each lands in its sorted slot.
    b08_by_day = {"2024-06-01": 6000, "2024-06-11": 6500, "2024-06-21": 7000}

    def fake_load(day_items, aoi_bbox, crs=None, resolution=10, bands=None):
        day = day_items[0].datetime.strftime("%Y-%m-%d")
        return _make_day_ds(b08_by_day[day], bands=bands, resolution=resolution)

    monkeypatch.setattr(cp, "load_day_cube", fake_load)
    return b08_by_day


def _run_download(tmp_path):
    cp.download_cubes(
        output_dir=tmp_path,
        aoi_id="aoi_test",
        bbox=[31.0, 30.0, 31.1, 30.1],
        start_date="2024-06-01",
        end_date="2024-06-30",
        max_cloud=30.0,
        force_rerun=False,
        max_workers=3,
    )


def test_download_creates_sorted_cube(tmp_path, patched):
    _run_download(tmp_path)
    zarr_path = tmp_path / "cube.zarr"
    assert zarr_path.exists()

    cube = xr.open_zarr(str(zarr_path), consolidated=False)
    on_disk = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in cube.time.values]
    assert on_disk == sorted(_DAYS), "cube time axis must be sorted on disk"

    # Each day's distinct B08 landed in its correct sorted slot.
    assert int(cube["B08"].isel(time=0, y=0, x=0).values) == patched["2024-06-01"]
    assert int(cube["B08"].isel(time=2, y=0, x=0).values) == patched["2024-06-21"]

    # cube.zarr stores source pixels/provenance only; derived stats live in CSV.
    assert "ndvi_mean" not in cube

    # Ledger has 3 downloaded days.
    index = cp._load_index(tmp_path / "scenes_index.jsonl")
    assert len(index["days"]) == 3
    assert all(r["status"] == "downloaded" for r in index["days"].values())

    # Cube self-describes config via attrs.
    assert cube.attrs["aoi_id"] == "aoi_test"
    assert cube.attrs["crs"] == "EPSG:32636"


def test_process_fills_stats_and_csv(tmp_path, patched):
    _run_download(tmp_path)
    cp.process_cubes(output_dir=tmp_path)

    csv_path = tmp_path / "indices_timeseries.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["solar_day"] for r in rows] == sorted(_DAYS), "CSV rows sorted by day"
    # All days are valid vegetation (red=0.05, nir≥0.5) → high NDVI, full validity.
    for r in rows:
        assert float(r["ndvi_mean"]) > 0.8
        assert float(r["valid_fraction"]) == pytest.approx(1.0)
        assert "36RUU" in r["mgrs_tiles"]
    # Distinct B08 per day → strictly increasing NDVI across sorted days.
    ndvis = [float(r["ndvi_mean"]) for r in rows]
    assert ndvis[0] < ndvis[1] < ndvis[2]

    # Derived stats are not written back into the source cube.
    cube = xr.open_zarr(str(tmp_path / "cube.zarr"), consolidated=False)
    assert "ndvi_mean" not in cube

    # Ledger remains operational download state; processing does not mark stats-current.
    index = cp._load_index(tmp_path / "scenes_index.jsonl")
    assert all(r["status"] == "downloaded" for r in index["days"].values())


def test_process_recomputes_derived_csv_without_mutating_cube(tmp_path, patched, monkeypatch):
    _run_download(tmp_path)
    cp.process_cubes(output_dir=tmp_path)

    calls = {"count": 0}
    original = cp.compute_day_stats

    def counted_compute_day_stats(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(cp, "compute_day_stats", counted_compute_day_stats)
    cp.process_cubes(output_dir=tmp_path)
    assert calls["count"] == len(_DAYS)

    csv_path = tmp_path / "indices_timeseries.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    assert [r["solar_day"] for r in rows] == sorted(_DAYS)


def test_download_skips_current_days_on_rerun(tmp_path, patched, monkeypatch):
    _run_download(tmp_path)
    cp.process_cubes(output_dir=tmp_path)

    # Re-running download must skip all days (status downloaded + matching cache key);
    # load_day_cube must not be called again.
    def _boom(*a, **k):
        raise AssertionError("load_day_cube called for an already-current day")

    monkeypatch.setattr(cp, "load_day_cube", _boom)
    _run_download(tmp_path)  # should be a no-op download


def test_date_range_backfill_appends_only_missing_days(tmp_path, patched, monkeypatch):
    _run_download(tmp_path)
    cp.process_cubes(output_dir=tmp_path)

    extra_days = ["2024-05-01", "2024-05-11"]
    all_days = extra_days + _DAYS
    items = [
        _FakeItem(
            f"S2B_MSIL2A_{d.replace('-', '')}T082559_R021_T36RUU_x",
            datetime.fromisoformat(d).replace(tzinfo=timezone.utc),
            cloud=float(i),
        )
        for i, d in enumerate(all_days)
    ]
    monkeypatch.setattr(
        cp.pystac_client.Client, "open",
        staticmethod(lambda *a, **k: _FakeCatalog(items)),
    )

    b08_by_day = {**patched, "2024-05-01": 5500, "2024-05-11": 5750}
    calls = []

    def fake_load(day_items, aoi_bbox, crs=None, resolution=10, bands=None):
        day = day_items[0].datetime.strftime("%Y-%m-%d")
        calls.append((day, resolution, tuple(bands or [])))
        return _make_day_ds(b08_by_day[day], bands=bands, resolution=resolution)

    monkeypatch.setattr(cp, "load_day_cube", fake_load)
    cp.download_cubes(
        output_dir=tmp_path,
        aoi_id="aoi_test",
        bbox=[31.0, 30.0, 31.1, 30.1],
        start_date="2024-05-01",
        end_date="2024-06-30",
        max_cloud=30.0,
        force_rerun=False,
        max_workers=2,
    )

    assert {day for day, _resolution, _bands in calls} == set(extra_days)
    assert any(resolution == 10 for _day, resolution, _bands in calls)
    assert any(resolution == 20 for _day, resolution, _bands in calls)

    root = xr.open_zarr(str(tmp_path / "cube.zarr"), consolidated=False)
    native = xr.open_zarr(str(tmp_path / "cube.zarr"), group="20m", consolidated=False)
    root_days = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in root.time.values]
    native_days = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in native.time.values]
    assert root_days == sorted(all_days)
    assert native_days == root_days
    assert int(root["B08"].isel(time=root_days.index("2024-05-01"), y=0, x=0).values) == 5500

    cp.process_cubes(output_dir=tmp_path)
    with (tmp_path / "indices_timeseries.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["solar_day"] for r in rows] == sorted(all_days)


def test_bbox_change_invalidates_bbox_only_cache(tmp_path, patched, monkeypatch):
    _run_download(tmp_path)
    cp.process_cubes(output_dir=tmp_path)

    calls = []

    def changed_bbox_load(day_items, aoi_bbox, crs=None, resolution=10, bands=None):
        calls.append((day_items[0].datetime.strftime("%Y-%m-%d"), tuple(aoi_bbox)))
        return _make_day_ds(7500, bands=bands, resolution=resolution)

    monkeypatch.setattr(cp, "load_day_cube", changed_bbox_load)
    cp.download_cubes(
        output_dir=tmp_path,
        aoi_id="aoi_test",
        bbox=[31.2, 30.0, 31.3, 30.1],
        start_date="2024-06-01",
        end_date="2024-06-30",
        max_cloud=30.0,
        force_rerun=False,
        max_workers=3,
    )

    assert len(calls) == len(_DAYS)
    assert {bbox for _, bbox in calls} == {(31.2, 30.0, 31.3, 30.1)}


def test_aoi_geometry_masking_restricts_denominator(tmp_path, monkeypatch):
    """AOI masking limits valid_fraction to AOI pixels only — proves the crs_wkt
    round-trip + make_aoi_mask path the geometry=None tests skip.

    SCL layout (4 rows × 5 cols): top 2 rows cloud everywhere; right 2 cols cloud
    everywhere; bottom-left valid. AOI = left 3 columns.
      - Masked (correct): denominator = 12 AOI px, valid = 6 (bottom-left) → 0.5
      - Unmasked (bug):   denominator = 20 grid px, valid = 6 → 0.3
    Asserting ≈0.5 distinguishes a working mask from a no-op one.
    """
    def masked_ds() -> xr.Dataset:
        y = np.arange(_GRID_Y, dtype=float) * -10.0 + 1_000_000.0
        x = np.arange(_GRID_X, dtype=float) * 10.0 + 500_000.0
        scl = np.full((_GRID_Y, _GRID_X), 4, dtype=np.uint8)
        scl[0:2, :] = 9   # top 2 rows: cloud
        scl[:, 3:5] = 9   # right 2 cols: cloud (outside AOI)

        def band(val, dtype):
            return (("y", "x"), np.full((_GRID_Y, _GRID_X), val, dtype=dtype))

        ds = xr.Dataset(
            {
                "B02": band(1500, np.uint16), "B03": band(2000, np.uint16),
                "B04": band(1500, np.uint16), "B08": band(6000, np.uint16),
                "B11": band(2000, np.uint16),
                "SCL": (("y", "x"), scl),
            },
            coords={"y": y, "x": x},
        )
        return ds.odc.assign_crs("EPSG:32636")

    items = [_FakeItem("S2B_MSIL2A_20240601T082559_R021_T36RUU_x",
                       datetime(2024, 6, 1, tzinfo=timezone.utc), 1.0)]
    monkeypatch.setattr(cp.pystac_client.Client, "open",
                        staticmethod(lambda *a, **k: _FakeCatalog(items)))
    monkeypatch.setattr(cp, "load_day_cube", lambda *a, **k: masked_ds())

    # AOI = left 3 columns (x centres 500000/500010/500020), all rows.
    utm_box = {
        "type": "Polygon",
        "coordinates": [[
            [499994.0, 999960.0], [500024.0, 999960.0],
            [500024.0, 1000010.0], [499994.0, 1000010.0], [499994.0, 999960.0],
        ]],
    }
    _projected = transform_geom("EPSG:32636", "EPSG:4326", utm_box)
    wgs84_geom = {
        "type": "Polygon",
        "coordinates": [[list(pt) for pt in ring] for ring in _projected["coordinates"]],
    }

    cp.download_cubes(
        output_dir=tmp_path, aoi_id="aoi_geom",
        bbox=[31.0, 30.0, 31.1, 30.1],
        start_date="2024-06-01", end_date="2024-06-30",
        max_cloud=30.0, force_rerun=False, crs="EPSG:32636",
        geometry=wgs84_geom, max_workers=1,
    )
    cp.process_cubes(output_dir=tmp_path)

    with (tmp_path / "indices_timeseries.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    vf = float(rows[0]["valid_fraction"])
    assert vf == pytest.approx(0.5, abs=0.05), (
        f"AOI masking should restrict denominator to AOI (≈0.5); got {vf} "
        f"(0.3 would mean the mask was a no-op)"
    )


def test_resume_redownloads_failed_day(tmp_path, monkeypatch):
    """A day that fails on the first pass is re-downloaded on a second pass.

    Covers the cube_exists grid-extraction branch + region-write into an existing
    slot, plus the bootstrap-retry-on-failure loop.
    """
    items = [
        _FakeItem(
            f"S2B_MSIL2A_{d.replace('-', '')}T082559_R021_T36RUU_x",
            datetime.fromisoformat(d).replace(tzinfo=timezone.utc),
            cloud=float(i),
        )
        for i, d in enumerate(_DAYS)
    ]
    monkeypatch.setattr(
        cp.pystac_client.Client, "open",
        staticmethod(lambda *a, **k: _FakeCatalog(items)),
    )
    state = {"fail": {"2024-06-11"}}

    def flaky_load(day_items, aoi_bbox, crs=None, resolution=10, bands=None):
        day = day_items[0].datetime.strftime("%Y-%m-%d")
        if day in state["fail"]:
            raise RuntimeError(f"simulated download failure for {day}")
        return _make_day_ds(6000, bands=bands, resolution=resolution)

    monkeypatch.setattr(cp, "load_day_cube", flaky_load)

    _run_download(tmp_path)  # 06-11 fails
    index = cp._load_index(tmp_path / "scenes_index.jsonl")
    assert index["days"]["2024-06-11"]["status"] == "error"
    assert index["days"]["2024-06-01"]["status"] == "downloaded"

    state["fail"] = set()  # heal
    _run_download(tmp_path)  # resume: only 06-11 is work; written into its slot
    index = cp._load_index(tmp_path / "scenes_index.jsonl")
    assert index["days"]["2024-06-11"]["status"] == "downloaded"

    cp.process_cubes(output_dir=tmp_path)
    with (tmp_path / "indices_timeseries.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["solar_day"] for r in rows] == sorted(_DAYS)


def test_backfills_deleted_20m_bands_without_reloading_10m(tmp_path, patched, monkeypatch):
    _run_download(tmp_path)

    for band in ("B11", "SCL"):
        store_path = tmp_path / "cube.zarr" / "20m" / band
        assert store_path.exists()
        shutil.rmtree(store_path)

    calls = []

    def fake_backfill_load(day_items, aoi_bbox, crs=None, resolution=10, bands=None):
        calls.append((resolution, tuple(bands or [])))
        day = day_items[0].datetime.strftime("%Y-%m-%d")
        return _make_day_ds(patched[day], bands=bands, resolution=resolution)

    monkeypatch.setattr(cp, "load_day_cube", fake_backfill_load)
    _run_download(tmp_path)

    assert calls
    assert all(resolution == 20 for resolution, _bands in calls)
    assert all(set(_bands) <= {"B11", "SCL"} for _resolution, _bands in calls)

    root = xr.open_zarr(str(tmp_path / "cube.zarr"), consolidated=False)
    native = xr.open_zarr(str(tmp_path / "cube.zarr"), group="20m", consolidated=False)
    assert "B08" in root
    assert "B11" in native
    assert "SCL" in native
    assert root.sizes["y"] != native.sizes["y"]
    assert root.sizes["x"] != native.sizes["x"]

    cp.process_cubes(output_dir=tmp_path)
    with (tmp_path / "indices_timeseries.csv").open(newline="", encoding="utf-8") as fh:
        assert len(list(csv.DictReader(fh))) == len(_DAYS)


def test_backfills_requested_red_edge_bands_only(tmp_path, patched, monkeypatch):
    _run_download(tmp_path)
    calls = []

    def fake_red_edge_load(day_items, aoi_bbox, crs=None, resolution=10, bands=None):
        calls.append((resolution, tuple(bands or [])))
        day = day_items[0].datetime.strftime("%Y-%m-%d")
        return _make_day_ds(patched[day], bands=bands, resolution=resolution)

    monkeypatch.setattr(cp, "load_day_cube", fake_red_edge_load)
    cp.download_cubes(
        output_dir=tmp_path,
        aoi_id="aoi_test",
        bbox=[31.0, 30.0, 31.1, 30.1],
        start_date="2024-06-01",
        end_date="2024-06-30",
        max_cloud=30.0,
        force_rerun=False,
        bands=["B02", "B03", "B04", "B08", "B11", "SCL", "B05", "B06", "B07", "B8A"],
        max_workers=3,
    )

    assert calls
    assert all(resolution == 20 for resolution, _bands in calls)
    assert all(set(_bands) <= {"B05", "B06", "B07", "B8A"} for _resolution, _bands in calls)

    native = xr.open_zarr(str(tmp_path / "cube.zarr"), group="20m", consolidated=False)
    for band in ("B05", "B06", "B07", "B8A", "B11", "SCL"):
        assert band in native
    assert "ndvi_mean" not in native
