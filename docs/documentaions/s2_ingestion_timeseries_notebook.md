# Sentinel-2 Ingestion Notebook — How to Use It (AOI Time Series)

## 1) Purpose
This notebook generates a **per-scene time series** for a given AOI from **Sentinel-2 L2A** using the Microsoft Planetary Computer **STAC API**.

It is built for **AOI-only** ingestion:
- Reads only the AOI window from remote **COG** assets (no full-tile downloads).
- Uses **SCL** to mask clouds/shadows/no-data.
- Computes indices (NDVI/EVI/NDMI/NDWI/MNDWI) per scene.
- Exports a clean dataset for preprocessing.

---

## 2) What you edit (Configuration)
In the first config cell, set:

- `aoi_id`  
  Stable identifier for the AOI/run (e.g., `aoi_farmtrust_demo_01`)

- `bbox`  
  `[min_lon, min_lat, max_lon, max_lat]` in EPSG:4326 (lon/lat)

- `months_back`  
  Recommended:
  - `1` for quick iteration and debugging
  - `24` for the full Phase A dataset

- `max_cloud`  
  Metadata filter (e.g., 20–30). Use as a coarse filter only.

- Quality thresholds:
  - `usable_thresh` (e.g., 0.7)
  - `excellent_thresh` (e.g., 0.9)

---

## 3) Notebook Steps (what each section does)

### Step A — Connect to Planetary Computer STAC
We open the STAC endpoint:
- `https://planetarycomputer.microsoft.com/api/stac/v1`

We enable automatic signing using:
- `modifier=planetary_computer.sign_inplace`

This ensures asset URLs are signed before reading.

### Step B — Search for Sentinel-2 L2A scenes
We query:
- `collections=["sentinel-2-l2a"]`
- `bbox=bbox`
- `datetime=f"{start}/{end}"`
- optional: `query={"eo:cloud_cover": {"lt": max_cloud}}`

Then we:
- convert results to a list
- sort by `item.datetime` to ensure deterministic order

### Step C — Read AOI windows from COG assets
For each scene, the notebook reads only a window from each required band:

- Convert bbox bounds from EPSG:4326 → the asset CRS (typically UTM meters)
- Compute pixel window from projected bounds
- Read the window via rasterio

This is the key “AOI-first” behavior.

### Step D — Cloud masking with SCL (and valid_fraction)
We read:
- SCL (often 20m)

Then we:
- resample SCL to match the 10m grid (nearest neighbor)
- compute `valid_mask` = NOT invalid SCL classes
- compute `valid_fraction` = valid pixels / total AOI pixels

### Step E — Compute indices per scene (masked)
We compute (on valid pixels only):
- NDVI (B08, B04)
- EVI (B08, B04, B02)
- NDMI (B08, B11)
- NDWI (B03, B08)
- MNDWI (B03, B11)

For each index we store:
- mean over valid pixels
- 95th percentile over valid pixels

### Step F — Build the final time-series table
One row per scene with:
- IDs/timestamp/meta
- valid_fraction
- index stats (mean + p95)
- optional flags (`is_usable_scene`, `is_excellent_scene`)

### Step G — Visual sanity checks
We plot NDVI vs time (scatter), optionally highlighting low-quality scenes using `valid_fraction`.

### Step H — Save outputs
We export:

- `data/ingest/<aoi_id>/indices_timeseries.csv`
- `data/ingest/<aoi_id>/run_metadata.json`

CSV is used in Phase A to avoid parquet engine dependencies.

---

## 4) Output Schema (CSV contract)
Required columns:
- `item_id`
- `timestamp` (ISO-8601 UTC)
- `mgrs_tile`
- `eo_cloud_cover`
- `valid_fraction`

Index columns:
- `ndvi_mean`, `ndvi_p95`
- `evi_mean`, `evi_p95`
- `ndmi_mean`, `ndmi_p95`
- `ndwi_mean`, `ndwi_p95`
- `mndwi_mean`, `mndwi_p95`

Optional flags:
- `is_usable_scene`
- `is_excellent_scene`

---

## 5) Troubleshooting (common issues)

### 5.1 HTTP 403 (authentication/signature)
**Cause:** Signed asset URLs expired.  
**Fix:** Use STAC client with `modifier=sign_inplace` and re-sign items before read in long loops:
- `pc.sign_inplace(item)`

### 5.2 Parquet export fails
**Cause:** Missing `pyarrow`/`fastparquet`.  
**Fix:** Use CSV in Phase A (recommended). Add parquet engine later if required.

### 5.3 Band shape mismatch
**Cause:** Mixed resolutions (10m vs 20m).  
**Fix:** Resample SCL (and any needed 20m bands) consistently to the target grid.

---

## 6) Recommended run procedure
1) Run with `months_back = 1` to validate end-to-end behavior quickly.
2) Increase to `months_back = 24` for the full dataset.
3) Inspect:
   - total scenes found
   - distribution of `valid_fraction`
   - NDVI time series plot
4) Use exported CSV as the ingestion handoff to preprocessing.
