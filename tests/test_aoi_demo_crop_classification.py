from __future__ import annotations

import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AOI_DIR = PROJECT_ROOT / "data" / "aoi_demo_01"
MODEL_DIR = PROJECT_ROOT / "notebooks" / "data" / "models" / "combined_crop_classifier"
WEATHER_PATH = AOI_DIR / "weather_daily.parquet"
INDICES_PATH = AOI_DIR / "indices_timeseries.csv"
CUBE_PATH = AOI_DIR / "cube.zarr"
VALID_SCL = {2, 4, 5, 6}
BAND_FEATURES = [
    "feat_s2_B02_mean",
    "feat_s2_B03_mean",
    "feat_s2_B04_mean",
    "feat_s2_B05_mean",
    "feat_s2_B06_mean",
    "feat_s2_B07_mean",
    "feat_s2_B08_mean",
    "feat_s2_B8A_mean",
    "feat_s2_B11_mean",
]

SEASONS = {
    "C1": {"label": "Corn", "start": "2024-05-18", "end": "2024-08-30"},
    "C3": {"label": "Corn", "start": "2025-06-15", "end": "2025-09-11"},
    "C4": {"label": "Alfalfa", "start": "2025-10-05", "end": "2026-05-31"},
}


def _compute_vi_from_bands(band_means: dict[str, float]) -> dict[str, float]:
    B02 = band_means["B02"]
    B03 = band_means["B03"]
    B04 = band_means["B04"]
    B05 = band_means["B05"]
    B06 = band_means["B06"]
    B07 = band_means["B07"]
    B08 = band_means["B08"]
    B8A = band_means["B8A"]
    B11 = band_means["B11"]

    def _safe_div(num: float, den: float) -> float:
        if abs(den) < 1e-10:
            return float("nan")
        return num / den

    return {
        "s2_SAVI_mean": _safe_div((B08 - B04) * 1.5, B08 + B04 + 0.5),
        "s2_GNDVI_mean": _safe_div(B08 - B03, B08 + B03),
        "s2_NDRE_mean": _safe_div(B08 - B05, B08 + B05),
        "s2_MSI_mean": _safe_div(B11, B08),
        "s2_BSI_mean": _safe_div((B11 + B04) - (B08 + B02), (B11 + B04) + (B08 + B02)),
    }


def _spatial_mean_per_date(ds_10m, ds_20m, scl, dates):
    """Compute per-date spatial mean for each band, masked by valid SCL."""
    n_dates = len(dates)
    out = {b: np.full(n_dates, np.nan) for b in ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11"]}
    time_idx = {pd.Timestamp(t).date(): i for i, t in enumerate(ds_10m.time.values)}

    # Align SCL to 10m grid via nearest-neighbor
    scl_10m = scl.sel(y=ds_10m.y, x=ds_10m.x, method="nearest")

    for i, dt in enumerate(dates):
        dt_date = pd.Timestamp(dt).date()
        if dt_date not in time_idx:
            continue
        ti = time_idx[dt_date]

        valid_mask = np.isin(scl_10m.isel(time=ti).values, list(VALID_SCL))
        valid_count = valid_mask.sum()
        if valid_count == 0:
            continue

        for band in out:
            if band in ds_10m:
                arr = ds_10m[band].isel(time=ti).values.astype(float)
            else:
                arr_20m = ds_20m[band].isel(time=ti).values.astype(float)
                arr_10m = xr.DataArray(arr_20m, dims=["y", "x"], coords={"y": ds_20m.y, "x": ds_20m.x})
                arr = arr_10m.sel(y=ds_10m.y, x=ds_10m.x, method="nearest").values

            masked = arr * valid_mask
            out[band][i] = masked.sum() / valid_count
    return out


class TestAoiDemoCropClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = joblib.load(MODEL_DIR / "model.pkl")
        cls.label_encoder = joblib.load(MODEL_DIR / "label_encoder.pkl")
        cls.feature_columns = joblib.load(MODEL_DIR / "feature_columns.pkl")

        cls.ds_10m = xr.open_zarr(CUBE_PATH, consolidated=False)
        cls.ds_20m = xr.open_zarr(CUBE_PATH, group="20m", consolidated=False)
        cls.scl = cls.ds_20m["SCL"]
        cls.indices = pd.read_csv(INDICES_PATH, parse_dates=["solar_day"])
        cls.weather = pd.read_parquet(WEATHER_PATH)
        cls.weather["date"] = pd.to_datetime(cls.weather["date"])

    def _compute_season_features(self, season_name: str) -> pd.DataFrame:
        s = SEASONS[season_name]
        start = pd.Timestamp(s["start"])
        end = pd.Timestamp(s["end"])

        dates = pd.date_range(start, end, freq="D")
        dates_in_data = self.indices[
            (self.indices["solar_day"] >= start)
            & (self.indices["solar_day"] <= end)
            & (self.indices["valid_fraction"] > 0)
        ]

        # Per-date spatial band means from cube
        band_means_per_date = _spatial_mean_per_date(
            self.ds_10m, self.ds_20m, self.scl, dates_in_data["solar_day"]
        )

        # Per-date VI means for missing VIs from band means
        vi_missing_per_date = {k: [] for k in ["s2_SAVI_mean", "s2_GNDVI_mean", "s2_NDRE_mean", "s2_MSI_mean", "s2_BSI_mean"]}
        for j in range(len(dates_in_data)):
            bm = {b: band_means_per_date[b][j] for b in band_means_per_date}
            vi_row = _compute_vi_from_bands(bm)
            for k in vi_missing_per_date:
                vi_missing_per_date[k].append(vi_row[k])

        features = {}

        # Per-season mean of per-date band means (reflectance)
        for band in ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11"]:
            vals = band_means_per_date[band] / 10000.0  # uint16 → reflectance
            features[f"feat_s2_{band}_mean"] = np.nanmean(vals)

        # Per-season mean of per-date VI means (from CSV where available)
        vi_csv_map = {
            "feat_s2_NDVI_mean": "ndvi_mean",
            "feat_s2_EVI_mean": "evi_mean",
            "feat_s2_NDMI_mean": "ndmi_mean",
            "feat_s2_NDWI_GREEN_mean": "ndwi_mean",
        }
        for feat_key, csv_col in vi_csv_map.items():
            features[feat_key] = dates_in_data[csv_col].mean()

        # Per-season mean of per-date VI means (computed from bands)
        for vi_key in vi_missing_per_date:
            features[f"feat_{vi_key}"] = np.nanmean(vi_missing_per_date[vi_key])

        brightness = np.nanmean([features[col] for col in BAND_FEATURES])
        for col in BAND_FEATURES:
            norm_col = f"{col}_brightness_norm"
            features[norm_col] = features[col] / brightness if brightness and not np.isnan(brightness) else np.nan

        # Per-season mean of weather features
        weather_season = self.weather[
            (self.weather["date"] >= start) & (self.weather["date"] <= end)
        ]
        weather_feat_cols = [c for c in weather_season.columns if c != "date"]
        weather_means = weather_season[weather_feat_cols].mean()
        for col in weather_feat_cols:
            features[f"feat_{col}"] = weather_means[col]

        df = pd.DataFrame([features])
        df = df[self.feature_columns]
        return df

    def _predict_season(self, season_name: str) -> tuple[str, str]:
        df = self._compute_season_features(season_name)
        pred = self.pipeline.predict(df)[0]
        label = self.label_encoder.inverse_transform([pred])[0]
        probabilities = self.pipeline.predict_proba(df)[0]
        ranked = sorted(
            zip(self.label_encoder.classes_, probabilities, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
        scores = ", ".join(f"{name}={score:.3f}" for name, score in ranked)
        return label, scores

    def _assert_known_label(self, season_name: str) -> None:
        expected = SEASONS[season_name]["label"]
        predicted, scores = self._predict_season(season_name)
        self.assertEqual(
            predicted,
            expected,
            f"{season_name}: known={expected}, predicted={predicted}, probabilities: {scores}",
        )

    def test_c1_corn(self):
        self._assert_known_label("C1")

    def test_c3_corn(self):
        self._assert_known_label("C3")

    def test_c4_alfalfa(self):
        self._assert_known_label("C4")


if __name__ == "__main__":
    unittest.main()
