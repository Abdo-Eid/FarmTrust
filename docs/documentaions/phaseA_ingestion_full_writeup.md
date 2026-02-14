# Phase A Ingestion (Sentinel-2 via Planetary Computer STAC) — Full Write-up

## 1) Objective
Build an **AOI-first** ingestion pipeline for land/farm assessment to support financing decisions. The ingestion phase must:

- Fetch **Sentinel-2 L2A** scenes for an AOI within a time window (e.g., last month for testing, last 24 months for full runs).
- Avoid full-tile downloads by reading **only AOI windows** from remote **COG** assets.
- Compute per-scene indices (**NDVI/EVI/NDMI/NDWI/MNDWI**) over the AOI.
- Compute a robust quality signal per scene using **SCL-based masking** (cloud-free usable fraction).
- Export a clean per-scene time series for downstream preprocessing (smoothing, gap handling, confidence inputs).

This document captures:
- Decisions and reasoning
- Steps and examples
- Findings/interpretation
- Problems encountered and solutions
- Output contract and handoff to preprocessing

---

## 2) Key Concepts (what we aligned on)

### 2.1 Sentinel-2 satellites (2A/2B/…)
Sentinel-2 is a mission with multiple satellites (commonly **2A** and **2B**, and you may also see newer spacecraft in some catalogs). More satellites means more revisit opportunities.

**Why multiple scenes can appear “on the same day”:**
- More frequent revisits
- Different acquisition times
- Different processing versions/products in the catalog  
So seeing more than one Item near the same date/time is normal.

### 2.2 Processing levels (L1C vs L2A)
- **L1C** = top-of-atmosphere reflectance (includes atmospheric effects)
- **L2A** = surface reflectance (atmosphere-corrected, analysis-ready)

We used **L2A** (`sentinel-2-l2a`) for indices and ML-ready workflows.

### 2.3 Scene vs Tile (MGRS)
- **Tile (MGRS)**: fixed grid cell (~100km x 100km). Example: `36RTV`.
- **Scene / STAC Item**: one acquisition at a specific time for a tile, with metadata + assets.

### 2.4 COG (Cloud Optimized GeoTIFF)
A **COG** is a GeoTIFF arranged to support efficient **partial reads** over HTTP (range requests).  
This is the core enabler for “AOI-only” reads.

**Old mental model:** satellite image = a file you download  
**New mental model:** satellite image = queryable cloud-hosted data

### 2.5 CRS and “convert bbox to scene CRS”
AOIs are often defined in **EPSG:4326** (lon/lat degrees). Sentinel-2 assets are typically in **UTM meters** (e.g., EPSG:32636).  

To compute the correct raster window:
1) Convert bbox bounds from EPSG:4326 → the asset CRS (UTM)
2) Compute the pixel window in that CRS
3) Read only that window

---

## 3) What STAC returns (and how we use it)
STAC provides:
- **Catalog**: entry point to data
- **Collection**: dataset grouping (e.g., `sentinel-2-l2a`)
- **Item**: one scene/acquisition (datetime, geometry, cloud cover, etc.)
- **Assets**: URLs (bands, QA layers, metadata files)

We query STAC by:
- AOI (`bbox` or `intersects`)
- time window (`datetime=start/end`)
- optional metadata filter `eo:cloud_cover`

---

## 4) Pipeline Summary (what we built)
For each AOI:
1) Define AOI (bbox or polygon)
2) STAC search (Sentinel-2 L2A)
3) Sort items by datetime
4) For each item:
   - Read AOI window from band assets (COGs)
   - Read SCL and align to target grid
   - Compute valid mask + valid_fraction
   - Compute indices on valid pixels only
   - Store per-scene summary stats
5) Save:
   - `indices_timeseries.csv` (or agreed CSV name)
   - `run_metadata.json`

---

## 5) Indices computed (per scene, over AOI window)
We computed (mean and p95 over valid pixels):

- **NDVI**: (NIR - RED) / (NIR + RED)
- **EVI**: 2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)
- **NDMI**: (NIR - SWIR1) / (NIR + SWIR1)
- **NDWI**: (GREEN - NIR) / (GREEN + NIR)
- **MNDWI**: (GREEN - SWIR1) / (GREEN + SWIR1)

**Note on scaling:** Many Sentinel-2 reflectance products use an integer scale factor (often 10000).  
If EVI is frequently > 1, reflectance scaling and/or masking should be reviewed.

---

## 6) Quality masking with SCL + valid_fraction

### 6.1 Why SCL
SCL (Scene Classification Layer) provides per-pixel classes (vegetation, water, cloud, shadow, no-data, etc.).  
We used it to remove pixels that are not reliable for index computation.

Typical SCL classes include:
- 0 No data
- 1 Saturated/defective
- 3 Cloud shadow
- 8 Cloud medium probability
- 9 Cloud high probability
- 10 Thin cirrus
- 11 Snow/ice

### 6.2 Valid mask and valid_fraction
We define a set of invalid classes:
- `INVALID_SCL = {0, 1, 3, 7, 8, 9, 10, 11}` (example)

Then:
- `valid = NOT (SCL in INVALID_SCL)`
- `valid_fraction = valid.sum() / valid.size`

This yields an AOI-specific usability metric per scene.

### 6.3 Why valid_fraction differs from eo:cloud_cover
- `eo:cloud_cover` is scene/tile-level metadata
- `valid_fraction` is AOI-only, computed from SCL in the bbox window

So it is normal to see mismatch between the two.

---

## 7) Findings and interpretation

### 7.1 Scene counts and revisit density
When running a ~24 month window for one AOI, we observed a large number of scenes (e.g., ~186 scenes).  
This is normal due to revisit frequency and multi-satellite coverage.

### 7.2 Using valid_fraction to decide usability
We used thresholds (example):
- `usable_thresh = 0.7`
- `excellent_thresh = 0.9`

And counted scenes meeting each threshold to understand how “good” the time series will be before preprocessing.

### 7.3 Reading windows (AOI-only) is the key cost/performance win
AOI windows are typically < 1% of a tile. Reading only windows keeps:
- bandwidth low
- runtime manageable
- storage minimal (especially when exporting only time-series stats)

---

## 8) Problems encountered and solutions

### 8.1 uv + Jupyter environment mismatch
**Symptoms**
- `ModuleNotFoundError` for geopandas/odc/etc.
- `No module named pip`
- Broken pandas metadata

**Solutions**
- Ensure Jupyter kernel uses the same Python executable as the uv environment.
- Install packages into the active environment.
- If pandas is corrupted, reinstall cleanly in the venv.

### 8.2 Parquet export error (missing engine)
**Symptom**
- pandas `to_parquet` fails due to missing `pyarrow` or `fastparquet`.

**Solution**
- For Phase A, export **CSV + JSON metadata** (simplest).
- Add parquet engine later only if required.

### 8.3 403 errors (signed URLs expired)
**Symptom**
- HTTP 403 “failed to authenticate the request” when reading many assets or archiving URLs.

**Root cause**
- Planetary Computer asset URLs are signed (SAS) and can expire.

**Solutions**
- Open the STAC client with `modifier=planetary_computer.sign_inplace`.
- In long loops, **re-sign** items before reads: `pc.sign_inplace(item)`.
- Avoid persisting signed URLs as permanent references; store item ids and re-sign at runtime.

### 8.4 Resolution mismatch between bands
**Symptom**
- B04/B08 (10m) shapes differ from SCL (20m) or SWIR (20m).

**Solution**
- Resample categorical layers (SCL) to match the 10m grid using nearest neighbor.
- For indices that require 20m bands, choose a consistent target grid and resample appropriately.

---

## 9) Decisions / Defaults (so the team can reproduce)
These are the practical defaults we converged on:

- **AOI input**: bbox in EPSG:4326 (lon/lat).
- **Time windows**:
  - Use **1 month** while iterating/debugging
  - Use **24 months** for the full Phase A dataset
- **Cloud filtering**:
  - Use metadata filter `eo:cloud_cover < X` as a coarse pre-filter (X often 20–30)
  - Trust AOI-quality more via `valid_fraction` from SCL
- **Masking**: Use SCL-based invalid classes to build `valid_mask`.
- **Scene quality thresholds**:
  - `usable_thresh = 0.7`
  - `excellent_thresh = 0.9`
- **Storage for Phase A**:
  - CSV for the time-series stats
  - JSON for run metadata
  - Avoid parquet until pyarrow is standardized in the env

---

## 10) What ingestion does NOT do (by design)
- Does **not** download full tiles.
- Does **not** produce a regular monthly grid (that’s preprocessing/resampling).
- Does **not** do smoothing, interpolation, or gap filling (preprocessing phase).
- Does **not** attempt to build a full “pixel cube” dataset unless explicitly requested (that is a separate storage design: GeoTIFF chips / Zarr / NetCDF).

---

## 11) Output contract (handoff to preprocessing)

### 11.1 Primary output (per-scene time series CSV)
One row per scene with:

- `item_id`
- `timestamp` (ISO-8601 UTC)
- `mgrs_tile`
- `eo_cloud_cover`
- `valid_fraction`
- Index stats:
  - `ndvi_mean`, `ndvi_p95`
  - `evi_mean`, `evi_p95`
  - `ndmi_mean`, `ndmi_p95`
  - `ndwi_mean`, `ndwi_p95`
  - `mndwi_mean`, `mndwi_p95`
Optional:
- `is_usable_scene`
- `is_excellent_scene`

### 11.2 Run metadata JSON
- AOI id + bbox
- time window
- STAC endpoint + collection
- cloud threshold
- invalid SCL classes
- thresholds and scene counts
- created_at timestamp
- notes

---

## 12) Next steps (preprocessing readiness)
Given the time-series CSV, preprocessing can:
- filter and weight observations by `valid_fraction`,
- smooth NDVI,
- handle gaps with bounded interpolation rules,
- compute confidence inputs:
  - usable observation count
  - gap ratio
  - max gap days
  - season clarity proxy
- log preprocessing parameters for reproducibility
