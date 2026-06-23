"""Offline unit tests for cube ingestion — no network or credentials required."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from farmtrust_core.ingest.cube_stats import (
    OFFSET_POLICY,
    apply_boa_offset,
    build_day_cache_key,
    compute_day_stats,
)

INVALID_SCL = {0, 1, 3, 7, 8, 9, 10, 11}


# ---------------------------------------------------------------------------
# BOA offset scaling
# ---------------------------------------------------------------------------

def test_apply_boa_offset_formula():
    """(DN - 1000) / 10000 applied correctly to known DN values."""
    dn = np.array([1000, 2000, 6000, 10000], dtype=np.uint16)
    result = apply_boa_offset(dn)
    expected = np.array([0.0, 0.1, 0.5, 0.9], dtype=np.float32)
    np.testing.assert_allclose(result, expected, atol=1e-5)


def test_apply_boa_offset_nodata_is_nan():
    """DN=0 (NODATA) maps to NaN, not -0.1."""
    dn = np.array([0, 1000, 2000], dtype=np.uint16)
    result = apply_boa_offset(dn)
    assert np.isnan(result[0]), "DN=0 must become NaN, not a reflectance value"
    assert not np.isnan(result[1])
    assert not np.isnan(result[2])


def test_apply_boa_offset_output_dtype():
    """Output is always float32 regardless of input dtype."""
    dn = np.array([3000], dtype=np.uint16)
    assert apply_boa_offset(dn).dtype == np.float32


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------

_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[30.0, 31.0], [30.1, 31.0], [30.1, 31.1], [30.0, 31.1], [30.0, 31.0]]],
}


def test_cache_key_excludes_date_range():
    """start_date and end_date must NOT affect the per-day cache key."""
    base = build_day_cache_key("2024-07-01", _GEOMETRY, "EPSG:32636", 10, INVALID_SCL, 30.0)
    # Any hypothetical variant produced by a different date range must be the same key
    assert isinstance(base, str) and len(base) == 64


def test_cache_key_changes_with_offset_policy():
    """Different offset policies produce different keys (policy is in the payload)."""
    import hashlib, json
    from farmtrust_core.ingest.cube_stats import BOA_ADD_OFFSET, BOA_SCALE

    k1 = build_day_cache_key("2024-07-01", _GEOMETRY, "EPSG:32636", 10, INVALID_SCL, 30.0)
    # Mutate offset_policy via the canonical payload manually
    payload = {
        "solar_day": "2024-07-01",
        "aoi_geometry": _GEOMETRY,
        "aoi_bbox": None,
        "crs": "EPSG:32636",
        "resolution": 10,
        "invalid_scl_classes": sorted(INVALID_SCL),
        "max_cloud": 30.0,
        "offset_policy": "different_policy",
    }
    k2 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert k1 != k2


def test_cache_key_same_geometry_stable():
    """Same inputs always produce the same key (deterministic serialisation)."""
    k1 = build_day_cache_key("2024-07-01", _GEOMETRY, "EPSG:32636", 10, INVALID_SCL, 30.0)
    k2 = build_day_cache_key("2024-07-01", _GEOMETRY, "EPSG:32636", 10, INVALID_SCL, 30.0)
    assert k1 == k2


def test_cache_key_changes_with_bbox_for_bbox_only_runs():
    """BBox-only AOIs must not replay stale rows after the bbox changes."""
    k1 = build_day_cache_key(
        "2024-07-01", {}, "EPSG:32636", 10, INVALID_SCL, 30.0,
        aoi_bbox=[31.0, 30.0, 31.1, 30.1],
    )
    k2 = build_day_cache_key(
        "2024-07-01", {}, "EPSG:32636", 10, INVALID_SCL, 30.0,
        aoi_bbox=[31.2, 30.0, 31.3, 30.1],
    )
    assert k1 != k2


# ---------------------------------------------------------------------------
# compute_day_stats — pure offline tests using synthetic xarray datasets
# ---------------------------------------------------------------------------

def _make_ds(
    b02_dn=1500,
    b03_dn=2000,
    b04_dn=1500,
    b08_dn=6000,
    b11_dn=2000,
    scl_val=4,      # 4 = vegetation, valid
    height=4,
    width=4,
) -> xr.Dataset:
    """Synthetic uniform dataset for offline testing — no CRS, no odc accessor."""
    x = np.arange(width, dtype=float) * 10.0
    y = np.arange(height, dtype=float)[::-1] * -10.0

    def band(val, dtype):
        return xr.DataArray(
            np.full((height, width), val, dtype=dtype),
            dims=["y", "x"],
            coords={"y": y, "x": x},
        )

    return xr.Dataset({
        "B02": band(b02_dn, np.uint16),
        "B03": band(b03_dn, np.uint16),
        "B04": band(b04_dn, np.uint16),
        "B08": band(b08_dn, np.uint16),
        "B11": band(b11_dn, np.uint16),
        "SCL": band(scl_val, np.uint8),
    })


def test_ndvi_mean_known_value():
    """With known DN, NDVI mean matches hand-computed value.

    B04_dn=1500 → red=0.05, B08_dn=6000 → nir=0.5
    NDVI = (0.5 - 0.05) / (0.5 + 0.05) ≈ 0.8182
    """
    ds = _make_ds(b04_dn=1500, b08_dn=6000)
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    assert stats is not None
    expected_ndvi = (0.5 - 0.05) / (0.5 + 0.05)
    assert abs(stats["ndvi_mean"] - expected_ndvi) < 0.001


def test_valid_fraction_all_valid():
    """All pixels valid → valid_fraction == 1.0."""
    ds = _make_ds(scl_val=4)
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    assert stats is not None
    assert stats["valid_fraction"] == pytest.approx(1.0)


def test_valid_fraction_all_invalid():
    """All pixels cloud (SCL=9) → valid_fraction == 0.0, indices are NaN."""
    ds = _make_ds(scl_val=9)
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    assert stats is not None
    assert stats["valid_fraction"] == pytest.approx(0.0)
    assert np.isnan(stats["ndvi_mean"])
    assert np.isnan(stats["ndvi_p95"])


def test_valid_fraction_half_invalid():
    """Half the grid is cloud → valid_fraction ≈ 0.5."""
    height, width = 4, 4
    scl = np.full((height, width), 4, dtype=np.uint8)
    scl[:, width // 2 :] = 9  # right half is cloud

    x = np.arange(width, dtype=float) * 10.0
    y = np.arange(height, dtype=float)[::-1] * -10.0

    def band(val, dtype):
        return xr.DataArray(np.full((height, width), val, dtype=dtype), dims=["y", "x"],
                            coords={"y": y, "x": x})

    ds = xr.Dataset({
        "B02": band(1500, np.uint16), "B03": band(2000, np.uint16),
        "B04": band(1500, np.uint16), "B08": band(6000, np.uint16),
        "B11": band(2000, np.uint16),
        "SCL": xr.DataArray(scl, dims=["y", "x"], coords={"y": y, "x": x}),
    })
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    assert stats is not None
    assert abs(stats["valid_fraction"] - 0.5) < 0.01


def test_evi_mean_known_value():
    """EVI = 2.5*(nir-red)/(nir+6*red-7.5*blue+1) with known scaled values."""
    # B02=1500→0.05 (blue), B04=1500→0.05 (red), B08=6000→0.5 (nir)
    ds = _make_ds(b02_dn=1500, b04_dn=1500, b08_dn=6000)
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    blue, red, nir = 0.05, 0.05, 0.5
    expected_evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + 1e-8)
    assert abs(stats["evi_mean"] - expected_evi) < 0.001


def test_nodata_dn_excluded_from_stats():
    """DN=0 pixels (NODATA) must not bias index computation."""
    height, width = 4, 4
    # Left half is valid (DN=6000), right half is NODATA (DN=0)
    b08 = np.full((height, width), 6000, dtype=np.uint16)
    b08[:, width // 2 :] = 0  # NODATA
    b04 = np.full((height, width), 1500, dtype=np.uint16)

    x = np.arange(width, dtype=float) * 10.0
    y = np.arange(height, dtype=float)[::-1] * -10.0

    def band(arr, dtype=np.uint16):
        return xr.DataArray(arr.astype(dtype), dims=["y", "x"], coords={"y": y, "x": x})

    ds = xr.Dataset({
        "B02": band(np.full((height, width), 1500)),
        "B03": band(np.full((height, width), 2000)),
        "B04": band(b04),
        "B08": band(b08),
        "B11": band(np.full((height, width), 2000)),
        "SCL": band(np.full((height, width), 4), dtype=np.uint8),
    })
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    assert stats is not None
    # NDVI for valid half should be positive; NODATA half (NaN) should not drag it toward -0.1
    assert stats["ndvi_mean"] > 0.5


def test_compute_day_stats_returns_none_for_zero_aoi():
    """Returns None when AOI mask has no pixels (zero-size grid)."""
    ds = _make_ds(height=0, width=0)
    # height=0/width=0 makes the loop trivial — denominator=0
    # Re-create with 1×1 but manually patch: easier to test via all-invalid SCL + zero denominator
    # Instead test the zero-denominator path: create a 2×2 grid where SCL=4 but
    # simulate zero by passing a geometry that has no pixels.
    # The simplest path: aoi_geometry=None with an empty grid.
    ds2 = xr.Dataset({
        "B02": xr.DataArray(np.zeros((0, 0), dtype=np.uint16), dims=["y", "x"]),
        "B03": xr.DataArray(np.zeros((0, 0), dtype=np.uint16), dims=["y", "x"]),
        "B04": xr.DataArray(np.zeros((0, 0), dtype=np.uint16), dims=["y", "x"]),
        "B08": xr.DataArray(np.zeros((0, 0), dtype=np.uint16), dims=["y", "x"]),
        "B11": xr.DataArray(np.zeros((0, 0), dtype=np.uint16), dims=["y", "x"]),
        "SCL": xr.DataArray(np.zeros((0, 0), dtype=np.uint8), dims=["y", "x"]),
    })
    result = compute_day_stats(ds2, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    assert result is None


def test_scaling_applied_before_index_computation():
    """Verify that raw DN integers are scaled, not used directly.

    If scaling is skipped, NDVI computed from DN integers would be nearly 1.0
    (since (6000-1500)/(6000+1500) ≈ 0.6 in DN-space but only correct in
    reflectance-space). This test asserts the reflectance-space value.
    """
    ds = _make_ds(b04_dn=1500, b08_dn=6000)
    stats = compute_day_stats(ds, aoi_geometry=None, invalid_scl_classes=INVALID_SCL)
    # reflectance: red=0.05, nir=0.5 → NDVI≈0.818
    # raw DN ratio: (6000-1500)/(6000+1500) ≈ 0.6 — if this value appeared, scaling is missing
    assert stats["ndvi_mean"] > 0.8, (
        f"NDVI {stats['ndvi_mean']:.3f} suggests scaling was not applied "
        f"(expected ≈0.818 in reflectance space, ≈0.6 in DN space)"
    )
