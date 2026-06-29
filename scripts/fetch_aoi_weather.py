"""Fetch Open-Meteo weather for aoi_demo_01 and compute all derived features."""
import json
from pathlib import Path

import pandas as pd
import requests

AOI_DIR = Path("data/aoi_demo_01")
META_PATH = AOI_DIR / "run_metadata.json"
OUTPUT_PATH = AOI_DIR / "weather_daily.parquet"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

# AOI bbox from run_metadata.json
with open(META_PATH) as f:
    meta = json.load(f)
bbox = meta["bbox"]  # [min_lon, min_lat, max_lon, max_lat]
centroid_lon = (bbox[0] + bbox[2]) / 2
centroid_lat = (bbox[1] + bbox[3]) / 2

start_date = pd.Timestamp(meta["start_date"])
end_date = pd.Timestamp(meta["end_date"])
weather_start = pd.Timestamp(year=start_date.year, month=1, day=1).date().isoformat()
weather_end = end_date.date().isoformat()

print(f"AOI centroid: {centroid_lat:.6f}, {centroid_lon:.6f}")
print(f"Weather range: {weather_start} to {weather_end}")

# Fetch from Open-Meteo
params = {
    "latitude": centroid_lat,
    "longitude": centroid_lon,
    "start_date": weather_start,
    "end_date": weather_end,
    "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum",
    "timezone": "UTC",
}
resp = requests.get(OPEN_METEO_URL, params=params, timeout=90)
resp.raise_for_status()
data = resp.json()

daily = pd.DataFrame(data["daily"])
daily = daily.rename(columns={
    "time": "date",
    "temperature_2m_mean": "weather_daily_Temp_mean_C",
    "temperature_2m_max": "weather_daily_Temp_max_C",
    "temperature_2m_min": "weather_daily_Temp_min_C",
    "precipitation_sum": "weather_daily_Total_prec_mm",
})
daily["date"] = pd.to_datetime(daily["date"])
daily = daily.sort_values("date").reset_index(drop=True)

# Derive daily weather features
daily["weather_daily_gdd_base10"] = (daily["weather_daily_Temp_mean_C"] - 10.0).clip(lower=0)
daily["weather_daily_rainy_day"] = (daily["weather_daily_Total_prec_mm"] >= 1.0).astype(int)
daily["weather_daily_heavy_rain_day"] = (daily["weather_daily_Total_prec_mm"] >= 20.0).astype(int)
daily["weather_daily_heat_stress_day"] = (daily["weather_daily_Temp_max_C"] >= 35.0).astype(int)
daily["weather_daily_cold_stress_day"] = (daily["weather_daily_Temp_min_C"] <= 5.0).astype(int)

# Rolling windows (7, 14, 30 days)
for window_days in (7, 14, 30):
    prefix = f"weather_{window_days}d_"
    daily[f"{prefix}Total_prec_mm"] = daily["weather_daily_Total_prec_mm"].rolling(window_days, min_periods=1).sum()
    daily[f"{prefix}Temp_mean_C"] = daily["weather_daily_Temp_mean_C"].rolling(window_days, min_periods=1).mean()
    daily[f"{prefix}gdd_base10"] = daily["weather_daily_gdd_base10"].rolling(window_days, min_periods=1).sum()
    daily[f"{prefix}rainy_days"] = daily["weather_daily_rainy_day"].rolling(window_days, min_periods=1).sum()

# Cumulative features reset per calendar year, matching single-season training semantics.
cum_name_map = {
    "weather_daily_Total_prec_mm": "weather_cum_Total_prec_mm",
    "weather_daily_gdd_base10": "weather_cum_gdd_base10",
    "weather_daily_rainy_day": "weather_cum_rainy_days",
    "weather_daily_heavy_rain_day": "weather_cum_heavy_rain_days",
    "weather_daily_heat_stress_day": "weather_cum_heat_stress_days",
    "weather_daily_cold_stress_day": "weather_cum_cold_stress_days",
}
for col, cum_col in cum_name_map.items():
    daily[cum_col] = daily.groupby(daily["date"].dt.year)[col].cumsum()

daily.to_parquet(OUTPUT_PATH, index=False)
print(f"Saved weather to {OUTPUT_PATH}")
print(f"Rows: {len(daily)}, Columns: {len(daily.columns)}")
print(f"Date range: {daily['date'].min().date()} to {daily['date'].max().date()}")
