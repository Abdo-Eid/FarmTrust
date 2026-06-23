# Pipeline Walkthrough

This is a conversational guide for explaining the pipeline to a professor or reviewer. It keeps the original learning flow, but removes raw chat labels so it reads as a walkthrough.

Starting understanding: the user provides an AOI for the land as a polygon. We create a bounding box around that polygon, use it to search STAC for Sentinel-2 scenes from the last two years, load the relevant AOI window into a time-sorted cube, then mask everything outside the original polygon during statistics. After that, we calculate the valid fraction inside the polygon.

## Pipeline Ingestion — Explanation Guide

### Big Picture

The ingestion stage takes a **farmer's land parcel** (drawn as a polygon on a map) and produces a **per-solar-day time series of vegetation & moisture indices** over the last ~2 years. It answers: *"For every Sentinel-2 solar day over this field, what fraction was cloud-free and what were the index values?"*

---

### Step-by-step Walkthrough

**1. AOI → Bounding Box**

The user draws a polygon (GeoJSON). Since STAC APIs only search by rectangular bounding box, we compute the minimal axis-aligned rectangle that encloses the polygon.

- **Code:** `config.py:geometry_to_bbox()` — iterates polygon vertices, takes min/max lon/lat.
- **Why not search by polygon directly?** STAC does support `intersects` (geometries), but:
  - Planetary Computer search is simpler/more reliable with bbox
  - COG reads also use a rectangular window, so we need the bbox anyway

**2. STAC Search — Find Relevant Scenes**

We query **Planetary Computer's STAC catalog** for `sentinel-2-l2a` (atmosphere-corrected surface reflectance) that:
- Overlaps the bbox
- Falls within the date window (e.g., last 24 months)
- Has `eo:cloud_cover < 30%` (coarse pre-filter)

- **Code:** `cube_pipeline.py:466-472` — `catalog.search(bbox=bbox, datetime=..., query={...})`
- **Key detail:** The STAC client is opened with `modifier=pc.sign_inplace` — this automatically signs SAS URLs so they don't expire mid-run.

**3. Solar-Day Grouping — Mosaic All Overlapping Tiles**

Multiple Sentinel-2 items can land on the same calendar date because the AOI may cross tile boundaries or receive overlapping passes. The current path groups items by **solar day** and lets `odc.stac.load(groupby="solar_day")` mosaic the overlapping items into one aligned day slice.

This is different from the old per-scene dedup path: we do not choose one "best" tile and discard the others. For boundary AOIs, mosaicking is the correctness fix because every overlapping tile can contribute pixels.

- **Code:** `cube_pipeline.py:_group_by_solar_day()` and `cube_loader.py:load_day_cube()`

**4. Phase 1 Download — Write Raw Pixels Into `cube.zarr`**

This is the core efficiency and traceability win. Instead of downloading full Sentinel-2 tiles, `odc.stac.load` reads the rectangular AOI bbox window from the cloud assets, aligns requested bands on the needed UTM grid, and returns raw DN pixels for that solar day.

- **Code:** `cube_loader.py:load_day_cube()` and `cube_pipeline.py:download_cubes()`
- **How it works:**
  1. Estimate or accept a target UTM CRS for the AOI.
  2. Load default bands `B02`, `B03`, `B04`, `B08`, `B11`, and `SCL`; optionally backfill extra bands such as `B05`, `B06`, `B07`, `B8A`, and `B12`.
  3. Store 10m bands on the root grid and native 20m bands in the `20m` group. Use nearest-neighbor for categorical `SCL` only when aligning it for processing.
  4. Keep raw integer DN values in the cube; do not apply reflectance scaling during download.
  5. Region-write each completed day into its sorted time slot in `cube.zarr`.

- **Why this matters:** The cube is reusable and repairable. If one band is missing or a new band is requested, Phase 1 downloads only that band for existing real days; if the SCL policy or index formulas change, Phase 2 can reprocess local pixels without re-downloading from Planetary Computer.

- **Windows write safety:** Per-day chunks and a small Zarr region-write retry prevent transient file-lock failures while writing stats or pixels.

**5. Phase 2 Processing — Polygon Mask Applied**

After opening `cube.zarr`, Phase 2 masks out everything **outside the original polygon** so indices only reflect the actual land parcel.

- **Code:** `cube_stats.py:make_aoi_mask()` and `cube_stats.py:compute_day_stats()`
- **Process:**
  1. Transform polygon from EPSG:4326 to the cube's UTM CRS.
  2. Rasterize the polygon onto the cube grid: `True` inside polygon, `False` outside.
  3. Apply this mask before computing valid fraction and index statistics.

- **Why this matters for your professor:** It means the indices are computed **only over the actual field boundary**, not the surrounding area that happened to be in the bbox.

**6. SCL Masking & Valid Fraction**

Sentinel-2 includes a **Scene Classification Layer (SCL)** — a per-pixel classification (vegetation, cloud, shadow, snow, etc.). We use it to filter out unreliable pixels.

Invalid classes (from `cube_pipeline.py:82`):
```
{0: no data, 1: saturated, 3: cloud shadow, 7: low-probability cloud,
 8: medium-probability cloud, 9: high-probability cloud, 10: thin cirrus, 11: snow/ice}
```

**Valid fraction** = `(valid pixels inside polygon) / (all pixels inside polygon)`

- `valid` = pixels whose SCL class is NOT in the invalid set
- **Not the same as `eo:cloud_cover`** — that's a tile-level metadata estimate. `valid_fraction` is AOI-specific, computed from the actual pixel classification within your field boundary.
- **Code:** `cube_stats.py:compute_day_stats()`

**7. Index Computation**

Five vegetation/water indices are computed over valid pixels only:

| Index | Formula | What it tells you |
|---|---|---|
| NDVI | (NIR - Red) / (NIR + Red) | Vegetation greenness / biomass |
| EVI | 2.5×(NIR-Red) / (NIR+6×Red-7.5×Blue+1) | Vegetation, better in dense canopy |
| NDMI | (NIR - SWIR1) / (NIR + SWIR1) | Moisture content |
| NDWI | (Green - NIR) / (Green + NIR) | Open water |
| MNDWI | (Green - SWIR1) / (Green + SWIR1) | Water, better for built-up areas |

Before computing indices, raw Sentinel-2 DN is converted to surface reflectance using the post-2022 BOA baseline rule: `(DN - 1000) / 10000`; DN=0 is treated as nodata.

Each index returns **mean** and **95th percentile** over valid pixels.

- **Code:** `cube_stats.py:apply_boa_offset()`, `cube_stats.py:compute_day_stats()`, `indices.py`

**8. Output Artifacts**

For each AOI run, four outputs are produced:

- **`cube.zarr`** — Primary source artifact. Raw DN pixels, source provenance, and root attrs live on one sorted time axis. The root group stores 10m bands; the `20m` group stores native 20m bands such as `B11`, `SCL`, and red-edge bands.
- **`indices_timeseries.csv`** — Derived downstream handoff. One row per solar-day mosaic with `timestamp`, representative `item_id`, `valid_fraction`, and all index stats. Recompute this from `cube.zarr` when processing policy changes.
- **`scenes_index.jsonl`** — v4+ operational ledger. One append-only record per attempted solar day with `cache_key`, day `status`, and optional per-band `band_status`; it is authoritative about which cube slots and bands are real.
- **`run_metadata.json`** — Run config and Phase 2 config read-path for downstream auditability.

---

### The Key Design Decisions (for your professor's questions)

**"Why not just download the full tile?"**
Each Sentinel-2 tile is large, and the AOI window is typically a tiny fraction of it. The ODC cube path reads only the bbox window needed for the AOI and persists that compact subset in `cube.zarr`.

**"How do you handle different band resolutions?"**
Visible/NIR bands (`B02`, `B03`, `B04`, `B08`) are stored on the 10m root grid. Native 20m bands (`B05`, `B06`, `B07`, `B8A`, `B11`, `B12`, `SCL`) are stored in the `20m` group to avoid upscaling storage. Phase 2 aligns 20m bands temporarily in memory only when an index or mask needs a shared grid.

**"What if the AOI is on the edge of a tile or spans multiple tiles?"**
Items from the same solar day are mosaicked, so overlapping tiles can jointly cover the AOI. If the AOI polygon has zero pixels on the cube grid, Phase 2 marks the day `empty_aoi` and skips it.

**"Why compute both mean and p95?"**
Mean is sensitive to the overall distribution. P95 captures the "best" pixels — useful when a field has mixed conditions (e.g., partial irrigation).

**"What about caching?"**
Each solar day has a **fingerprint** based on the AOI identity (geometry and bbox), CRS, resolution, cloud threshold, SCL classes, and offset policy. If a day was previously downloaded with the same fingerprint and requested bands exist, it can be skipped or replayed from the cube. Missing requested bands are backfilled independently. The date range itself is not part of the per-day key, but the current cube time axis is fixed; extending to days absent from an existing `cube.zarr` requires a rebuild with `--force-rerun`.

---

### If your professor asks "What comes next?"

The `indices_timeseries.csv` feeds into:
1. **Preprocessing** (`preprocess_timeseries.py`) — gap-aware local smoothing, gap analysis, quality metrics
2. **Seasonal analysis** (`seasonal_analysis.py`) — detecting growing-season windows from smoothed NDVI
3. **Land assessment** (`scoring/`) — rule-based classification: active/intermittent/inactive, trend, risk flags

That leads into the downstream stages: preprocessing, activity-window analysis, and assessment.

### Quick Example: `indices_timeseries.csv`

Here's what a row in `indices_timeseries.csv` looks like — formatted as a table for clarity:

| item_id | timestamp | mgrs_tile | eo_cloud_cover | valid_fraction | ndvi_mean | ndvi_p95 | evi_mean | evi_p95 | ndmi_mean | ndmi_p95 | ndwi_mean | ndwi_p95 | mndwi_mean | mndwi_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `S2B_36RTV_20260601_0_L2A` | `2026-06-01T09:24:31Z` | `36RTV` | 12.3 | 0.92 | 0.71 | 0.88 | 0.42 | 0.55 | 0.35 | 0.48 | -0.21 | -0.08 | 0.15 | 0.29 |
| `S2A_36RTV_20260527_0_L2A` | `2026-05-27T09:27:14Z` | `36RTV` | 25.1 | 0.78 | 0.65 | 0.82 | 0.38 | 0.51 | 0.31 | 0.44 | -0.18 | -0.05 | 0.12 | 0.26 |
| `S2B_36RTV_20260522_0_L2A` | `2026-05-22T09:24:52Z` | `36RTV` | 5.1 | 0.97 | 0.73 | 0.89 | 0.44 | 0.57 | 0.36 | 0.49 | -0.22 | -0.09 | 0.16 | 0.30 |

**Key readings from the data:**

- **Jun 1** (12% cloud → `valid_fraction=0.92`): 92% of the field pixels are usable. NDVI mean=0.71 indicates **healthy dense vegetation**.
- **May 27** (25% cloud → `valid_fraction=0.78`): cloudier, so fewer usable pixels, but indices are still reliable because we mask clouds out via SCL, not just drop the whole scene.
- **May 22** (5% cloud → `valid_fraction=0.97`):  cleanest pass — NDVI 0.73, NDMI 0.36 (good moisture).

The CSV is sparse by design — irregular timestamps, one row per satellite pass, and no interpolation. Downstream smoothing cleans usable observations, but it still keeps only real observation dates.

### Brief Next-Step View

Here's the high-level pipeline flow after ingestion:

```
  ┌─────────────┐
  │  Ingestion  │  ← we just covered this (STAC → COG → mask → CSV)
  │  (you are   │
  │   here)     │
  └──────┬──────┘
         ↓
  ┌─────────────┐
  │ Preprocess  │  Clean the noisy time series: smooth, flag gaps, mark usable scenes
  └──────┬──────┘
         ↓
  ┌─────────────┐
  │  Seasonal   │  Detect growing seasons from the smoothed NDVI signal
  │  Analysis   │  (start/peak/end dates, quality labels)
  └──────┬──────┘
         ↓
  ┌─────────────┐
  │    Land     │  Final answer: active? declining? risk flags? confidence?
  │ Assessment  │  Combines everything into a decision
  └─────────────┘
```

**4 stages, 4 scripts, one AOI.** Each stage reads the previous stage's output files. The chain is:

1. **Preprocessing** — takes the irregular CSV, smooths NDVI/EVI/etc. with a gap-aware local smoother, flags long observation gaps, marks scenes as "usable" if `valid_fraction ≥ 0.90`
2. **Seasonal analysis** — looks at the smooth NDVI curve, finds vegetation activity windows using field-relative peak prominence compared with the field's own estimated noise, then labels each window as `good` / `interrupted` / `weak`
3. **Land assessment** — combines everything to classify the AOI as `active` / `intermittent` / `inactive` over the 2-year window, with a trend (improving/stable/declining), risk flags, and an overall confidence level

**TL;DR for your professor:** *Ingestion gives us a raw time series. Preprocessing cleans it. Seasonal analysis finds the growing windows. Assessment makes the final call.*

## Preprocessing — Detailed Explanation

### The Problem It Solves

The ingestion CSV has **raw, uneven, noisy** data. On a single day, you might get 2-3 scenes from different satellite passes with slightly different values. Cloudy scenes have low `valid_fraction` and unreliable indices. And between clear days, there are gaps where clouds blocked view.

Preprocessing takes this messy signal and produces a **clean, smoothed time series** with explicit quality flags, so downstream seasonal analysis doesn't have to deal with raw noise.

---

### Step-by-Step

**1. Load & Sort**

Read the ingestion CSV, validate required columns exist (`item_id`, `timestamp`, `valid_fraction`, `ndvi_mean`, `evi_mean`, `ndmi_mean`, `ndwi_mean`), sort all rows by timestamp.

- **Code:** `pipeline.py:100-130` — `load_ingestion_observations()`

**2. Collapse Same-Day Duplicates**

Multiple scenes can fall on the same UTC calendar day (overlapping tiles, S2A + S2B passes). These are **merged into one row per day** using a **valid-fraction-weighted average**:

- Each scene's contribution weight = its `valid_fraction`
- If `valid_fraction` is 0 (all cloudy), weight is clamped to 0
- If total weight is 0, falls back to simple arithmetic mean

**Example:**

| Raw rows (same day) | valid_fraction | ndvi |
|---|---|---|
| Scene A (clear pass) | 0.95 | 0.72 |
| Scene B (cloudy pass) | 0.30 | 0.65 |

→ Merged: NDVI ≈ `(0.72 × 0.95 + 0.65 × 0.30) / (0.95 + 0.30)` = **0.70** (the clear scene dominates)

- **Code:** `pipeline.py:133-171` — `collapse_same_day_observations()`

**3. Filter Usable Observations**

After merging, we apply a **`valid_fraction ≥ 0.90`** threshold. Any observation where less than 90% of the field pixels were usable (cloud-free, not shadow/snow) is marked as **not usable**. Its raw values are kept in the output but it does **not** contribute to smoothing.

- **Why 0.90?** It's conservative — we only trust scenes where almost the entire field is clear. Stricter than `eo:cloud_cover` because it's computed on the **actual polygon**, not the whole tile.

- **Code:** `pipeline.py:206-207`

**4. Smoothing — Gap-Aware Local Median Then Weighted Mean**

The smoothing method is **`gap_aware_local_median_weighted_mean`**. It smooths noisy observations, but it refuses to hide evidence gaps or create fake vegetation continuity.

The rules are:

1. Keep the existing usability gate: only observations with `valid_fraction >= 0.90` can be smoothed.
2. Split usable observations into continuous segments. Any usable-observation gap **greater than 12 days** starts a new segment.
3. For each real usable observation, look only within the same segment and within a local `±12 day` window.
4. First pass: local median removes spikes.
5. Second pass: weighted mean smooths the curve. Weight = `valid_fraction / (1 + abs(delta_days) / 12.0)`.
6. If a point has fewer than 2 neighboring usable observations in its segment/window, keep the raw value.
7. 1-point and 2-point segments keep raw values.
8. No interpolation. No synthetic dates. Only real observations remain.

**Graph from the current data**

![NDVI before and after gap-aware smoothing](assets/session-ses_1244_smoothing.png)

This graph uses the real ingestion output from `data/land-5f9a0269b2ea4f96b0a120098b6c65c4/indices_timeseries.csv` and recomputes preprocessing with the current gap-aware smoothing method.

**Example** (raw NDVI values from usable scenes over time):

| Observation | Day | Raw NDVI | Segment |
|---|---:|---:|---|
| A | 0 | 0.30 | 1 |
| B | 5 | 0.72 | 1 |
| C | 10 | 0.31 | 1 |
| D | 28 | 0.68 | 2 |

A, B, and C can smooth together because their gaps are within 12 days. The gap from C to D is 18 days, so D starts a new segment. The smoother cannot use D to smooth C, or C to smooth D. This prevents fake continuity across cloudy periods.

- Smoothing is applied to **NDVI, EVI, NDMI, and NDWI** independently.
- Non-usable observations get empty smoothed values.
- Seasonal confirmation and scoring consume the same smoothed EVI, NDMI, and NDWI policy from preprocessing.

- **Code:** `smoothing.py` — `smooth_usable_values()`

**5. Gap Analysis**

Even after filtering, the usable observations have **irregular spacing**. Sentinel-2 revisits every ~5 days, but clouds can create longer gaps. Three metrics quantify this:

| Metric | What it is | How it's computed |
|---|---|---|
| **gap_ratio** | Fraction of the total span that is "excess gap" beyond the expected 5-day cadence | `sum(max(0, gap - 5)) / total_span_days`, range [0,1] |
| **max_gap_days** | Longest stretch with no usable observation | simple max of consecutive deltas |
| **median_gap_days** | Typical gap between usable observations | median of consecutive deltas |

Then these drive a **gap risk classification**:

| Condition | Risk Label | Confidence Penalty |
|---|---|---|
| `max_gap > 15 days` OR `gap_ratio > 0.30` | **high** | high |
| `max_gap > 10 days` OR `gap_ratio > 0.15` | **moderate** | moderate |
| otherwise | **low** | low |

- **Code:** `gaps.py` — `compute_gap_metrics()`, `classify_gap_risk()`
- **Design note:** This is NOT land risk — it's **evidence reliability**. A high gap risk means "we can't be as confident in what the land did during that missing period." Land assessment uses this to decide how much to trust its own conclusion.

---

### Outputs

**1. `ndvi_smoothed.csv`** — One row per real merged observation date, sorted by time. It is not a regular daily grid and does not include invented dates:

| timestamp | ndvi_raw | ndvi_smoothed | evi_raw | evi_smoothed | ndmi_raw | ndmi_smoothed | ndwi_raw | ndwi_smoothed | valid_fraction | is_usable | source_row_count |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-05-01 | 0.30 | 0.31 | 0.18 | 0.19 | 0.12 | 0.13 | -0.09 | -0.10 | 0.96 | true | 1 |
| 2026-05-06 | 0.72 | 0.33 | 0.46 | 0.21 | 0.29 | 0.14 | -0.18 | -0.11 | 0.94 | true | 1 |
| 2026-05-11 | 0.31 | 0.31 | 0.19 | 0.19 | 0.13 | 0.13 | -0.10 | -0.10 | 0.97 | true | 1 |
| 2026-05-20 | 0.65 | — | 0.38 | — | 0.31 | — | -0.18 | — | 0.78 | false | 2 |
| 2026-05-29 | 0.68 | 0.68 | 0.40 | 0.40 | 0.30 | 0.30 | -0.17 | -0.17 | 0.95 | true | 1 |

How to read this example:

- May 1, May 6, and May 11 are usable and close enough together, so they form one smoothing segment. The May 6 NDVI spike is dampened by the local median plus weighted mean.
- May 20 is kept for transparency, but it has no smoothed values because `valid_fraction = 0.78`, below the 0.90 usability threshold.
- May 29 is usable, but the 18-day gap from May 11 is greater than the 12-day smoothing limit. It starts a new 1-point segment, so its smoothed values equal its raw values instead of borrowing from the earlier segment.

**2. `quality_metrics.json`** — All the gap/confidence metadata:

```json
{
  "aoi_id": "aoi_demo_01",
  "total_observation_count": 186,
  "merged_observation_count": 98,
  "usable_observation_count": 67,
  "dropped_observation_count": 31,
  "gap_ratio": 0.12,
  "max_gap_days": 14.2,
  "median_gap_days": 4.8,
  "long_gap_count": 2,
  "long_gap_windows": [
    {"start": "2025-12-20", "end": "2026-01-03", "gap_days": 14.2},
    ...
  ],
  "gap_risk": "moderate",
  "confidence_penalty": "moderate",
  "smoothing_method": "gap_aware_local_median_weighted_mean",
  "max_smoothing_gap_days": 12.0,
  "local_window_days": 12.0,
  "minimum_local_neighbors": 2,
  "minimum_local_neighbors_excludes_center": true,
  "weighting_policy": "valid_fraction_time_distance",
  "interpolation_policy": "none",
  "creates_synthetic_timestamps": false,
  "smooths_only_usable_observations": true
}
```

---

### Common Questions Your Professor Might Ask

**"Why not interpolate to fill gaps?"**

Deliberate choice. If a 2-week gap hides a drought or a growing-season start, interpolation would **fabricate data** that looks smooth but is wrong. The pipeline is honest about gaps — they lower confidence explicitly.

**"Why both median AND mean smoothing?"**

Median kills spikes without being pulled by them. Weighted mean makes the local curve smoother. Both passes are time-aware and gap-aware: they only use observations inside the same continuous segment and within `±12` days.

**"What does `is_usable = false` mean for downstream?"**

That row's raw values are present for transparency, but its smoothed value is empty (`""` in CSV). Seasonal analysis skips it entirely. The raw values can still be helpful for manual review ("the field was cloudy that day, but here's what the sensor saw through thin clouds").

---

**Summary for your professor:** *Preprocessing takes the scattered raw scenes, merges same-day duplicates weighted by quality, filters to only 90%+ clear observations, smooths the signal with a gap-aware local median then weighted-mean filter, and measures gaps explicitly. It does not smooth across gaps greater than 12 days or invent missing observations.*

## Seasonal Analysis — Detailed Explanation

### The Problem It Solves

Preprocessing gives you a smooth NDVI curve over time, but it's just a sequence of numbers. Seasonal analysis answers: *"When did the farmer actually grow something? How many seasons in the last 2 years? Were they good seasons or weak ones?"*

It turns a signal into **discrete events** — growing windows with start, peak, end dates and quality labels.

---

### Step-by-Step

**1. Load Only Usable, Smoothed Data**

It reads the preprocessing CSV but **filters** to rows where `is_usable = true` AND `ndvi_smoothed` is not empty. Non-usable days are invisible to the detector — they had too much cloud to trust.

- **Code:** `seasons.py:109-144` — `load_preprocess_observations()`

**2. Find Candidate Activity — Adaptive Peak Prominence**

The detector scans the smoothed NDVI curve for local peaks and compares each peak with the field's own nearby low points. It does **not** use a fixed NDVI floor or fixed NDVI amplitude gate.

- **Local low envelope:** the detector keeps a local 20th-percentile NDVI reference inside a 90-day window for review/context.
- **Prominence:** the important signal is how far the peak rises above surrounding low shoulders.
- **Noise floor:** the detector estimates the field's own noise from short-term movement and residual variation.
- **Decision:** `prominence_to_noise_ratio >= 3.8` becomes a confirmed activity window; `>= 2.5` becomes a borderline window for review.

```
NDVI
 0.7 │            ▄▄▄▄▄▄▄
 0.6 │         ▄▄▤        ▄▄▄
 0.5 │       ▄▤                ▄
 0.4 │     ▄▤                    ▄
 0.3 │   ▄▤                        ▄
 0.2 │ ▄▤  ← rising above local shoulder
 0.1 │▤                               ▄
     └──────────────────────────────────── time
       ^ candidate must be prominent compared with field-specific noise
```

- **Code:** `seasons.py` — `build_activity_signal_model()`, `detect_activity_windows()`, `detect_season_windows()`

**3. Bound the Activity Window**

After finding a candidate peak, the detector bounds the activity window using a relative boundary: about 20% of the candidate prominence above the local shoulder. This keeps boundaries field-relative instead of tied to a universal NDVI value.

- If the curve is still rising at the final observation, the window is `open_right`.
- If the curve was already active at the first observation, the window is `open_left`.
- Open windows are retained but marked `provisional` because the full biological start/end was not observed.

**4. Filter Out Noise — Minimum Requirements**

A brief or weak blip is not a season. Three filters remove false positives:

| Filter | Value | Why |
|---|---|---|
| Min signal evidence | `prominence_to_noise_ratio >= 3.8` for confirmed; `>= 2.5` for borderline | Need a meaningful rise compared with field-specific noise |
| Min observations | **4** smoothed points | Need enough data to confirm a pattern |
| Min duration | **20 days** | A real growing season spans weeks, not days |

If the curve starts in the middle of an activity cycle, it is no longer silently excluded. It is emitted as `open_left`, with `start_boundary_certainty = "open"` and `provisional = true`.

- **Code:** `seasons.py` — adaptive candidate detection and lifecycle classification in `detect_activity_windows()` / `detect_season_windows()`

**Graph from the current data**

![How season count is detected](assets/session-ses_1244_season_detection.png)

How to read it:

- The blue line is the smoothed NDVI signal from usable observations.
- Candidate peaks are compared against surrounding low shoulders and field-specific noise.
- Confirmed windows become `seasons[]` and count toward `season_count`.
- Borderline windows are reported separately in `borderline_windows[]` and do not count as confirmed seasons.
- Incomplete windows are preserved as `open_right` or `open_left` instead of being treated as finished seasons.
- In the current data example, the detector finds **1 confirmed open-right activity window** peaking on `2026-04-22` and **1 borderline complete candidate** from late 2025 / early 2026.

**5. Label Quality — Good / Interrupted / Weak**

Each detected season gets a quality label based on signal shape:

**Prominence-to-noise ratio** — Is the peak strong compared with this field's noise?
**Lifecycle status** — Did we observe a complete cycle, or is it still open?
**Max single-step drop** — Did the signal crash suddenly relative to its prominence?

| Label | Conditions | What it means |
|---|---|---|
| **Good** | Complete window with strong prominence/noise evidence | Strong observed activity window |
| **Interrupted** | Large one-step drop relative to prominence | Activity signal has a sharp interruption-like dip |
| **Weak** | Confirmed but weaker or provisional signal shape | Activity exists, but confidence in strength is lower |

- **Code:** `seasons.py:214-255` — `_label_quality()`

**6. Multi-Index Confirmation — Does NDVI Tell the Whole Story?**

NDVI alone can be fooled (e.g., green weeds on wet soil). The detector cross-checks three other indices:

| Check | Condition | What it tests |
|---|---|---|
| EVI behavior | Relative support near the NDVI peak | Is vegetation really there? EVI is better at dense canopy |
| NDMI behavior | Relative support near the NDVI peak | Is moisture context consistent with vegetation? |
| NDWI behavior | Does not spike like water near the NDVI peak | Helps avoid water/cloud contamination false positives |

If all three support the season → **strong** confirmation. If only 1-2 → **weak** or **moderate**.

Multi-index confirmation is reported as `strong`, `moderate`, or `weak`. It explains support from other indices, but the main activity decision remains based on adaptive NDVI prominence and evidence quality.

- **Code:** `seasons.py:270-309`

**7. Gap Overlap — Did the Satellite Miss a Critical Moment?**

Seasons detected during periods with long observation gaps get flagged. The detector checks if each season window overlaps a **long gap window** (from preprocessing), and classifies which **stage** was affected:

| Stage | What it means | Risk |
|---|---|---|
| Onset | Gap hid the very start of growth | **high** |
| Peak | Gap hid peak NDVI (hard to know max vigor) | **high** |
| Tail | Gap hid the end / senescence | moderate |
| Multiple | Gap covered more than one stage | **high** |

- **Code:** `seasons.py:312-379` — `_compute_gap_overlap()`

---

### Visual Example

Imagine a 2-year NDVI curve for a field in Egypt:

```
NDVI
0.8 │                    ┌──── season 2
0.7 │            ┌────┐  │  (good)
0.6 │    ┌────┐  │    │  │
0.5 │    │    │  │    │  │
0.4 │    │    │  │    │  │
0.3 │    │    │  │    │  └── prominent peak above local shoulder
0.2 │ ┌──┘    └──┘    └────
0.1 │─┘
    └──────────────────────────── time
    2024         2025         2026
```

The detector finds:
- **Season 1** (2024): has a clear rise and fall with strong prominence compared with noise, peaks at 0.55 in April, ends June → `good`, `confirmation=strong`
- **Season 2** (2025): has another clear field-relative activity cycle, peaks at 0.70, ends May → `good`, `confirmation=strong`
- Between seasons: the curve returns toward a local low shoulder, separating the two windows

---

### Output — `season_windows.json`

```json
{
  "aoi_id": "aoi_demo_01",
  "season_count": 2,
  "complete_window_count": 2,
  "open_window_count": 0,
  "borderline_window_count": 0,
  "gap_risk": "low",
  "seasons": [
    {
      "season_id": "season_01",
      "start_date": "2024-02-15",
      "crossing_date": "2024-03-02",
      "peak_date": "2024-04-10",
      "end_date": "2024-06-05",
      "is_open": false,
      "peak_ndvi": 0.55,
      "duration_days": 111.0,
      "quality_label": "good",
      "confirmation_level": "strong",
      "lifecycle_status": "complete",
      "detection_status": "confirmed",
      "prominence_ndvi": 0.35,
      "prominence_to_noise_ratio": 5.8,
      "evidence_summary": "Good vegetation activity window: peak_ndvi=0.550, prominence_ndvi=0.350, prominence_to_noise_ratio=5.80. Multi-index confirmation=strong ... ",
      "gap_overlap_count": 0,
      "gap_overlap_risk": "low",
      "gap_overlap_stage": "none",
      "season_confidence_note": "Gap risk is low. Observation continuity is strong enough..."
    },
    {
      "season_id": "season_02",
      "start_date": "2025-01-10",
      "crossing_date": "2025-01-28",
      "peak_date": "2025-03-15",
      "end_date": "2025-05-20",
      "is_open": false,
      "peak_ndvi": 0.70,
      "duration_days": 131.0,
      "quality_label": "good",
      "confirmation_level": "strong",
      ...
    }
  ]
}
```

---

### Common Questions Your Professor Might Ask

**"Why not use one fixed NDVI threshold?"**

Because one NDVI value does not work reliably across crops, soils, irrigation conditions, and regions. The current detector uses the field's own curve: local peaks, surrounding low shoulders, and a noise estimate. Near-cases become `borderline_windows` instead of being silently accepted or rejected.

**"What does `is_open = true` mean?"**

If the last accepted activity window is still active when our data ends, it is an **open-right window** — we caught the active window but do not have the end yet. If the field was already active when observations began, it is an **open-left window**. Both are provisional because a boundary is outside the observed interval.

**"Why use EVI/NDMI/NDWI for confirmation instead of just NDVI?"**

Each index has blind spots. NDVI saturates in dense vegetation (can't tell 0.80 from 0.85). EVI doesn't. NDMI sees moisture stress NDVI misses. NDWI distinguishes water from soil. Cross-referencing makes the system more robust to false positives.

**"What if no seasons are detected?"**

The seasonal output can validly report `season_count = 0`. That means no confirmed vegetation activity window passed the adaptive evidence gates. The payload may still include `borderline_windows` for review. Land assessment can continue and may classify the land as inactive or uncertain depending on evidence coverage.

---

**Summary for your professor:** *Seasonal analysis takes the smooth NDVI curve, finds vegetation activity windows using field-relative peak prominence compared with estimated noise, separates confirmed from borderline windows, preserves unfinished windows as provisional, labels each confirmed window as good/interrupted/weak using curve shape, cross-checks with EVI/NDMI/NDWI, and flags if critical moments fell in satellite observation gaps.*

## Land Assessment — Detailed Explanation

### The Problem It Solves

This is the **final automated answer when satellite evidence is sufficient**. The previous stages produced raw scenes, a cleaned signal, and detected seasons. Now we answer: *"What is this land doing? Is it actively farmed? Is it getting better or worse? Should a lender be cautious?"*

It's the stage where data turns into a **decision** — but with an evidence gate. If the satellite evidence is too weak, the system does **not** present a final automated land decision; it marks the assessment as requiring manual review.

---

### What It Reads From Each Stage

| Stage | File | What It Uses |
|---|---|---|
| Ingestion | `run_metadata.json` | Date interval |
| Preprocessing | `ndvi_smoothed.csv` | Raw values for all merged observations, plus smoothed NDVI/EVI/NDMI/NDWI for usable rows only |
| Preprocessing | `quality_metrics.json` | Gap risk, usable count, long gap windows |
| Seasonal | `season_windows.json` | Each season's dates, quality, confirmation, gap overlap |

---

### Step-by-Step

**1. Build Season Metrics — Rich Season Profiles**

Each season from the seasonal analysis gets enriched with **additional metrics** that weren't computed before:

| Metric | What it is | Why useful |
|---|---|---|
| **AUC** (Area Under Curve) | Sum of trapezoids under the NDVI curve across the season | Measures total "greenwork" — better than peak alone |
| **Peak EVI** | Max EVI during the season | Cross-check on vegetation density |
| **Median NDMI** | Typical moisture during the season | Detects dry spells |
| **Median NDWI** | Typical wetness during the season | Detects waterlogging |

- **Code:** `rules.py:152-197`

**2. Activity Coverage Fraction — How Much of the Time Was Inside Confirmed Activity Windows?**

Simple but powerful: of all usable smoothed observations, what fraction falls inside confirmed activity windows?

```
activity_coverage_fraction = observations_inside_confirmed_windows / total_usable_observations
```

- **0.70** = field was inside confirmed activity windows most of the time (multiple seasons, or one long one)
- **0.20** = brief pulses of activity, mostly fallow
- **Code:** `rules.py:200-202`

**3. Land Status — Active / Intermittent / Inactive**

This is the **core classification**. It considers both recent seasons (last 12 months) and the full activity coverage fraction.

| Status | Conditions | Meaning |
|---|---|---|
| **Active** | ≥ 2 recent seasons AND at least 1 is "good" AND activity coverage ≥ 0.35 | Regular farming, multiple good seasons |
| **Intermittent** | ≥ 1 recent season AND activity coverage ≥ 0.18 | Some activity but not consistent — could be fallow periods between crops |
| **Inactive** | Otherwise (no seasons or very low activity) | No significant vegetation detected — likely fallow, abandoned, or non-agricultural |

**Example:** A field with 2 good seasons over 2 years and 55% of usable observations inside confirmed activity windows → **active**.

- **Code:** `rules.py:214-242`

**4. 2-Year Trend — Improving / Stable / Declining / Uncertain**

Compares the **first** closed season to the **last** closed season on two axes:

| Metric | Direction | Rule |
|---|---|---|
| Peak NDVI delta | Improved | `≥ +0.03` |
| | Declined | `≤ -0.03` |
| AUC ratio | Improved | `≥ +10%` |
| | Declined | `≤ -10%` |

If either metric shows improvement → **improving**. If either shows decline → **declining**. If both are stable → **stable**. Need at least 2 seasons to compute; otherwise **uncertain**.

**Example:** Season 1 peak NDVI = 0.40, Season 2 peak NDVI = 0.55, AUC grew 15% → **improving**.

- **Code:** `rules.py:245-272`

**5. Latest Season Performance**

Takes the most recent closed season's quality label. If no closed season exists (last season is still open), it's marked **provisional**.

Determines whether the current/latest growing effort was:
- **Good** — strong peak, good confirmation
- **Interrupted** — had a significant dip
- **Weak** — low peak NDVI

- **Code:** `rules.py:275-287`

**6. Confidence — How Much Should We Trust This Assessment?**

Three components scored 0-3, then the **minimum** determines the final level:

| Component | What It Measures | Start Score | Deductions |
|---|---|---|---|
| **Continuity** | Were there enough clear-sky passes? | 3.0 | gap_risk: high → -1.5, moderate → -0.75; usable_count < 30 → -1.0, < 60 → -0.5; latest season gap overlap → -0.5 |
| **Season Clarity** | Did the indices agree on the season? | 3.0 | confirmation: weak → -0.75, moderate → -0.25 |
| **Signal Strength** | Was the actual vegetation signal strong? | 3.0 | quality_label: weak → -0.75, interrupted → -0.5 |

**Final level:**
| Score | Level | What it means to a lender |
|---|---|---|
| ≥ 2.5 | **high** | Confident assessment, reliable data |
| ≥ 1.5 | **medium** | Usable but with caveats |
| < 1.5 | **low** | Too much uncertainty for a firm decision |

Then confidence is capped by satellite evidence coverage:

| Evidence coverage | Confidence cap |
|---|---|
| `good` | No cap |
| `fair` | Maximum `medium` |
| `limited` | Maximum `low` |
| `insufficient` | `low` and manual review required |

- **Code:** `rules.py:290-364`

**7. Satellite Evidence Coverage — Separate from Land Confidence**

Before even looking at the land, how good is the satellite data itself? This is reported **separately** so it's clear if limitations are from data quality vs. land condition:

| Status | When |
|---|---|
| **Insufficient** | `usable_observation_count < 12`, or `gap_ratio > 0.60`, or `max_gap_days > 90`, or `long_gap_count > 12` |
| **Limited** | `usable_observation_count < 30`, or `gap_risk = high`, or `gap_ratio > 0.30`, or `max_gap_days > 45`, or `long_gap_count > 6` |
| **Fair** | `usable_observation_count < 60`, or `gap_risk = moderate`, or `gap_ratio > 0.15`, or `max_gap_days > 10`, or `long_gap_count > 0` |
| **Good** | None of the above |

- **Code:** `rules.py:367-385`

**8. Assessment Status Gate — Complete or Manual Review**

After computing evidence coverage, the backend decides whether the automated assessment can be presented as final:

| `assessment_status` | When | What the public API/report does |
|---|---|---|
| `complete` | Evidence is `good`, `fair`, or `limited` | Shows automated land status, trend, latest season performance, risk tier, and risk flags |
| `manual_review_required` | Evidence is `insufficient` | Hides final automated `land_status`, `trend_2y`, `season_performance`, and `risk_tier`; clears risk flags |

Key rule: **clouds and evidence gaps reduce confidence or trigger manual review, but they do not become land risk or farmer failure by themselves.**

- **Code:** `rules.py:445-485`, `assessment_mapper.py:176-208`

**9. Risk Flags — Conservative Warning System**

Risk flags describe observed land or farming issues only. Evidence gaps can lower confidence or trigger manual review, but they do **not** create risk flags by themselves.

| Flag | Severity | Trigger |
|---|---|---|
| `interruption_risk` | moderate | Any season had a sudden drop |
| `weak_activity_risk` | high/moderate | Latest season is weak or peak NDVI < 0.30 |
| `water_stress_risk` | moderate | Latest season NDMI < 0.05 (dry) |
| `waterlogging_risk` | moderate | Latest season NDWI > -0.05 (wet) |
| `possible_inactivity` | high/moderate | Land status is inactive or intermittent |
| `provisional_latest_season` | low | Latest season is still ongoing (no end date yet) |

Each flag has a `code`, `severity`, and human-readable `reason`. They are **not** combined into a single score — a lender sees the list and decides what matters. If evidence is `insufficient`, public risk flags are cleared because the system is saying "not enough evidence," not "this land is risky."

- **Code:** `rules.py:396-475`

---

### Output — `land_assessment.json`

Here's a real example of what comes out:

```json
{
  "aoi_id": "aoi_demo_01",
  "assessment_status": "complete",
  "interval": {
    "start_date": "2024-06-01",
    "end_date": "2026-06-01"
  },
  "land_status": "active",
  "trend_2y": "improving",
  "season_count": 2,
  "latest_season_performance": {
    "season_id": "season_02",
    "label": "good",
    "provisional": false,
    "confirmation_level": "strong",
    "evidence_summary": "Good season: peak_ndvi=0.550, rise_gain=0.350..."
  },
  "risk_flags": [
    {
      "code": "provisional_latest_season",
      "severity": "low",
      "reason": "The latest season is still open at the right edge of the available series."
    }
  ],
  "satellite_evidence_coverage": {
    "status": "good",
    "rationale": "Satellite observations are continuous enough for the assessment window."
  },
  "confidence": {
    "level": "high",
    "reasons": [
      "Gap continuity is strong enough for a confident baseline.",
      "Usable observation count is solid (72).",
      "Latest season has strong multi-index confirmation."
    ],
    "components": {
      "continuity": "high",
      "season_clarity": "high",
      "signal_strength": "high"
    }
  },
  "evidence": {
    "land_status_basis": "2 recent seasons were detected with active_fraction=0.55.",
    "trend_basis": "Season strength improved from peak_ndvi=0.350 to 0.550 with auc_ratio=0.18.",
    "latest_season_basis": "Good season: peak_ndvi=0.550, rise_gain=0.350...",
    "gap_note": "Observation continuity is strong enough that gap-related distortion risk is limited."
  },
  "metrics_summary": {
    "usable_observation_count": 72,
    "gap_risk": "low",
    "long_gap_count": 0,
    "active_observation_fraction": 0.55,
    "interval_max_ndvi": 0.72,
    "interval_max_evi": 0.45,
    "interval_median_ndmi": 0.28,
    "interval_median_ndwi": -0.15,
    "season_strength": [
      {
        "season_id": "season_01",
        "peak_ndvi": 0.35,
        "auc_ndvi": 24.5,
        "quality_label": "good",
        "confirmation_level": "strong",
        ...
      },
      {
        "season_id": "season_02",
        "peak_ndvi": 0.55,
        "auc_ndvi": 32.1,
        "quality_label": "good",
        "confirmation_level": "strong",
        ...
      }
    ]
  }
}
```

If satellite evidence is insufficient, the public result looks different:

```json
{
  "aoi_id": "aoi_demo_01",
  "assessment_status": "manual_review_required",
  "land_status": null,
  "trend_2y": null,
  "latest_season_performance": null,
  "risk_flags": [],
  "satellite_evidence_coverage": {
    "status": "insufficient",
    "rationale": "Too few usable satellite observations for a complete automated assessment."
  },
  "confidence": {
    "level": "low"
  }
}
```

---

### Common Questions Your Professor Might Ask

**"Why not just use a machine learning model for land status?"**

Intentional choice for this build. Rule-based assessment is **explainable** — every decision traces back to a specific threshold and evidence line. A lender or reviewer can read the `evidence.land_status_basis` and understand *why* the system said "active." ML would give a black-box score.

**"How is this different from seasonal analysis?"**

Seasonal analysis reports *what happened* (2 seasons, peak NDVI dates). Land assessment is *what it means* for a lender: is this farmer active? improving? risky? It combines season data with gap analysis, active fraction, and multi-index cross-checks.

**"The confidence has three components — why take the minimum?"**

Weakest link principle. If signal strength is high (lush vegetation) but continuity is low (satellite missed half the year), the overall assessment confidence should be low because you might have missed a crop failure in the gap. Taking the minimum ensures the overall level reflects the **most uncertain** dimension.

**"What happens when `satellite_evidence_coverage` is 'insufficient'?"**

The backend sets `assessment_status = "manual_review_required"`. The public API/report does not present a final automated `land_status`, `trend_2y`, `risk_tier`, or latest season performance. This avoids confusing "not enough satellite evidence" with "bad land" or "farmer risk."

**"How do risk flags get used?"**

They're not combined into a score. Each flag is an independent observed land signal. A lender might care most about `water_stress_risk` in a dry region, or `interruption_risk` if the loan is for a single-season crop. Evidence gaps are handled separately through `satellite_evidence_coverage`, `confidence`, and `assessment_status`.

---

### The Full Pipeline in One Sentence

Here's how you'd summarize the entire pipeline for your professor:

> *We take a farmer's field boundary, find every Sentinel-2 satellite pass over 2 years via STAC, read only the relevant pixels from Cloud-Optimized GeoTIFFs, mask to the field shape, compute vegetation indices from only clear pixels (SCL-based), smooth usable observations with a gap-aware local median then weighted-mean filter without inventing dates or smoothing across long gaps, detect vegetation activity windows using field-relative peak prominence compared with estimated noise, preserve unfinished windows as provisional, label quality using curve shape and multi-index cross-checks, and finally either classify the land as active/intermittent/inactive with trend, risk flags, and confidence, or require manual review when satellite evidence is insufficient — all explainable from first principles.*

## What We Have vs. What a Real System Needs

After understanding the rule-based current build, the next useful review is: what important pieces are still missing, and what better options might fit this use case?

The current pipeline is an explainable first working system: it can say whether land appears active, how many vegetation activity windows it has, and whether those windows look good, interrupted, or weak. For agricultural finance, that is useful, but it is not the full product yet.

Here is the assessment categorized by **what's missing** — grouped so you can tackle them one at a time.

---

### 1. The "Active/Inactive" Question Is Too Coarse

**What we have:** Three buckets: active, intermittent, inactive. The current logic is explainable, but it is still too coarse for many lending decisions.

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Crop type** | Knowing it's wheat vs. maize vs. orchard changes everything — season timing, water needs, risk profile |
| **Yield estimation** | "Active" doesn't tell you how much was harvested. A lender needs tons/hectare, not just "something grew" |
| **Crop health / stress** | NDVI can be 0.70 from weeds as easily as from a healthy crop. Current system can't distinguish |
| **Irrigation detection** | Is this farmer irrigating (controlled risk) or rainfed (weather-dependent)? Huge difference for financing |
| **Fallow vs. abandoned** | A field can be fallow for a season (normal rotation) vs. genuinely abandoned. Current system just says "inactive" after 1 year |

**What you could do:**
- **Crop type classification** from time-series phenology (shape of NDVI curve identifies crop)
- **Yield models** using peak NDVI + rainfall + soil data + historical calibration
- **Irrigation detection** from thermal band (Landsat) or SAR texture analysis
- **Red-edge indices** (NDRE, CIRE) for crop health vs. weed cover

---

### 2. The Seasonal Detection Still Needs Local Validation

**What we have:** Adaptive prominence/noise activity-window detection with confirmed, borderline, open-left, and open-right cases. This is much better than fixed NDVI thresholds, but it still needs ground-truth validation by region/crop system.

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Ground-truth calibration** | Prominence/noise and duration rules should be checked against known field histories |
| **Multiple cropping patterns** | Some regions have 3 seasons/year (rice in SE Asia). Some have 1 long season. Current hard-coded filters might miss or miscount |
| **Irregular calendars** | Northern vs. southern hemisphere. Current code assumes UTC dates but doesn't adjust for local growing windows |
| **Perennial crops** | Orchards, vineyards, and plantations may stay green year-round or have weak seasonal amplitude. They need a separate interpretation path |

**Alternatives to explore:**
- **Harmonic regression** (Fourier fit) to model the annual cycle — works across climates
- **Region-calibrated local NDVI baseline** and amplitude thresholds
- **TIMESAT-style phenology** — widely used in remote sensing for exactly this
- **Perennial crop detector** as a separate path (different rules for trees vs. annuals)

---

### 3. No External Data Integration

**What we have:** Pure satellite-derived indices. No context.

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Weather data** (rainfall, temp, GDD) | Explains WHY a season was weak — drought? cold? clouds? Without it, the system can't distinguish "bad farming" from "bad weather" |
| **Soil data** (type, WHC, slope) | Same crop on sandy vs. clay soil performs differently. Same NDVI means different things |
| **Historical benchmarks** | Is this year's NDVI normal for this field? Need 5-10 year baseline to detect anomalies |
| **Neighbor comparison** | Is one field declining while neighbors are fine? That's a farm-level problem vs. region-wide issue |
| **Market/price data** | Not all active land is profitable. High NDVI doesn't mean the farmer made money |

**What you could do:**
- **CHIRPS / ERA5 rainfall** integration (open, global)
- **SoilGrids / ISRIC** for soil properties
- **Z-score** computation against 5-year history once you have enough data
- **Peer comparison** — average NDVI of fields within 5km for relative scoring

---

### 4. No All-Weather Capability

**What we have:** Sentinel-2 optical only. Clouds = gaps.

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Sentinel-1 SAR (radar)** | Sees through clouds. Critical during monsoon/rainy seasons. Also detects soil moisture, flooding, harvest events |
| **Landsat** | Longer history (40+ years) for baselines. 30m resolution overlaps S2 |
| **MODIS / VIIRS** | Daily revisit (but coarse 250m-1km). Good for gap-filling and trend detection |
| **Commercial high-res** | Planet, Maxar — for small fields (< 1 ha) where Sentinel-2's 10m is too coarse |

**What you could do:**
- **S1 backscatter time-series** for cloud-free vegetation monitoring
- **S1-S2 fusion** models for daily gap-free vegetation index
- **Landsat Archive** for historical baselines before S2 existed (pre-2015)

---

### 5. No Spatial Detail Within Fields

**What we have:** One number per field (mean, p95). The field is a single blob.

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Within-field variability** | Half the field could be dead while the other half is fine. Mean NDVI hides this |
| **Spatial pattern analysis** | Stripes (irrigation problem), edges (encroachment), patches (pest outbreak) |
| **Patch identification** | Salinity spots, waterlogging zones, erosion areas — all visible in multi-year NDVI variability |
| **Field boundary change** | Is the field shrinking? Expanding? Being subdivided? This detects land tenure changes |

**What you could do:**
- **Coefficient of variation** within the field as a metric
- **Texture metrics** (GLCM, variograms)
- **Persistence maps** — pixels that are always bad vs. occasionally bad
- **Multi-year NDVI trend per pixel** before averaging to the field

---

### 6. No Forward-Looking Component

**What we have:** Entirely backward-looking. "What happened in the last 2 years?"

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Current season status** | Is the current crop progressing normally or failing? Early warning matters more than post-mortem |
| **Forecast / prediction** | Will the next season be normal based on current conditions, weather outlook, and historical patterns? |
| **Early warning alerts** | NDVI dropping unusually fast → possible pest/drought/flood → notify the lender during the season, not after |

**What you could do:**
- **Current season monitoring** — compare current NDVI trajectory to historical normal
- **Season-ahead analog prediction** — find historically similar years and forecast outcomes
- **Trigger-based alerts** — NDVI drop > 2 std from normal → automated flag

---

### 7. The Confidence System is Manual

**What we have:** Hand-tuned scoring with three components. Works but not statistically rigorous.

**What's missing:**

| Missing | Why It Matters |
|---|---|
| **Uncertainty quantification** | Every index (NDVI mean, valid fraction) has measurement error. Current system ignores it |
| **Calibration** | Are our thresholds correct? We don't know without validation data |
| **Ground truth loop** | No mechanism to learn from outcomes. If we say "active" and the field is fallow, we never find out |

**What you could do:**
- **Validation campaigns** — sample fields, collect ground truth, compare to assessment
- **Bayesian confidence** — propagate pixel-level uncertainty through the pipeline
- **Active learning** — flag uncertain cases for manual review, use those to improve rules

---

### 8. Missing Domain-Specific Risk Products

**Current risk flags are generic.** A real platform targeting a specific agri-domain would need tailored indicators:

| Domain | Example Risks to Detect |
|---|---|
| **Smallholder finance** | Fragmentation, encroachment, multi-cropping intensity |
| **Sugarcane** | Ratoon age detection, harvest timing, burning detection |
| **Rice** | Flooded field detection (SAR), transplanting date, multiple seasons |
| **Orchards / perennials** | Tree density, age estimation, disease stress (red-edge is critical here) |
| **Cotton** | Defoliation detection, harvest timing |
| **Conservation / carbon** | Cover cropping verification, tillage detection, woody encroachment |

---

### How I'd Prioritize

If this is for a professor / next-phase planning, here's the priority I'd recommend:

| Priority | What | Why |
|---|---|---|
| **P1** | Crop type classification | Everything downstream depends on knowing what's growing |
| **P2** | Region-adaptive seasonality | Fixed thresholds break outside your test region |
| **P3** | Sentinel-1 (SAR) integration | Optical-only is a dealbreaker in cloudy seasons |
| **P4** | Weather data integration | Without it, you can't explain WHY a season failed |
| **P5** | Within-field variability | Mean NDVI hides field-level problems |
| **P6** | Historical baselines | Anomaly detection requires knowing "normal" |
| **P7** | Yield estimation models | What lenders actually care about |
| **P8** | Peer comparison | Relative performance is more useful than absolute |

---

### The One-Sentence Summary

> *The current pipeline is an honest, explainable first system that proves you can go from satellite pixels to a defensible land activity assessment — but a production-ready system for agricultural finance needs crop type, yield estimates, weather integration, all-weather SAR capability, regional calibration, within-field spatial analysis, forward-looking monitoring, and a ground truth feedback loop, roughly in that order.*

## Current Metric Inventory

Here is the **complete inventory of every metric** the current pipeline produces, organized by stage.

---

### Stage 1: Ingestion — `indices_timeseries.csv`
*One row per satellite scene. These are raw, unfiltered.*

| # | Metric | What it is | Notes |
|---|---|---|---|
| 1 | `item_id` | Unique Sentinel-2 scene identifier | e.g. `S2B_36RTV_20260601_0_L2A` |
| 2 | `timestamp` | UTC acquisition datetime | ISO-8601 |
| 3 | `mgrs_tile` | UTM grid tile ID | e.g. `36RTV` |
| 4 | `eo_cloud_cover` | Tile-level cloud cover % from metadata | Not AOI-specific |
| 5 | `valid_fraction` | **Fraction of field pixels that are clear** | The core quality metric. 1.0 = perfectly clear over the polygon |
| 6 | `ndvi_mean` | Mean NDVI over clear pixels in the field | Vegetation greenness |
| 7 | `ndvi_p95` | 95th percentile NDVI | "Best pixels" — less affected by mixed conditions |
| 8 | `evi_mean` | Mean EVI | Better than NDVI in dense vegetation |
| 9 | `evi_p95` | 95th percentile EVI | |
| 10 | `ndmi_mean` | Mean NDMI | Moisture content |
| 11 | `ndmi_p95` | 95th percentile NDMI | |
| 12 | `ndwi_mean` | Mean NDWI | Open water detection |
| 13 | `ndwi_p95` | 95th percentile NDWI | |
| 14 | `mndwi_mean` | Mean MNDWI | Water, less affected by built-up areas |
| 15 | `mndwi_p95` | 95th percentile MNDWI | |

**Formula reference:**
- **NDVI** = (NIR - Red) / (NIR + Red)
- **EVI** = 2.5 × (NIR - Red) / (NIR + 6×Red - 7.5×Blue + 1)
- **NDMI** = (NIR - SWIR1) / (NIR + SWIR1)
- **NDWI** = (Green - NIR) / (Green + NIR)
- **MNDWI** = (Green - SWIR1) / (Green + SWIR1)

---

### Stage 2: Preprocessing — `ndvi_smoothed.csv`
*One row per real merged observation date. Only usable observations can receive smoothed values; tiny usable segments may keep raw values unchanged.*

| # | Metric | What it is | Notes |
|---|---|---|---|
| 16 | `timestamp` | UTC datetime of the observation | |
| 17 | `ndvi_raw` | NDVI after same-day weighted merge | Weighted by valid_fraction |
| 18 | `ndvi_smoothed` | Gap-aware local median then weighted-mean smoothed NDVI | Only filled if `is_usable = true` |
| 19 | `evi_raw` | Raw merged EVI | |
| 20 | `evi_smoothed` | Gap-aware smoothed EVI | |
| 21 | `ndmi_raw` | Raw merged NDMI | |
| 22 | `ndmi_smoothed` | Gap-aware smoothed NDMI | |
| 23 | `ndwi_raw` | Raw merged NDWI | |
| 24 | `ndwi_smoothed` | Gap-aware smoothed NDWI | |
| 25 | `valid_fraction` | Weighted valid_fraction for the merged day | |
| 26 | `is_usable` | `true` if `valid_fraction ≥ 0.90` | Controls whether it enters smoothing & seasonal analysis |
| 27 | `source_row_count` | How many raw scenes were merged into this row | 1 = single scene, 2+ = duplicate day |

---

### Stage 2b: Preprocessing — `quality_metrics.json`
*One object per AOI. Summarizes the entire preprocessed time series.*

| # | Metric | What it is | Notes |
|---|---|---|---|
| 28 | `total_observation_count` | Raw scenes from ingestion | Before any merging |
| 29 | `merged_observation_count` | Days after same-day collapse | |
| 30 | `usable_observation_count` | Days with `valid_fraction ≥ 0.90` | Core input to confidence |
| 31 | `dropped_observation_count` | Days below usability threshold | Present but not trusted for smoothing |
| 32 | `gap_ratio` | Sum of excess gap days ÷ total span | Range [0,1]. E.g. 0.12 = 12% of the time is "extra gap" beyond expected 5-day cadence |
| 33 | `max_gap_days` | **Longest gap between usable observations** | E.g. 14.2 = two weeks with no clear view |
| 34 | `median_gap_days` | Typical gap between usable observations | E.g. 4.8 = good (close to 5-day revisit) |
| 35 | `long_gap_count` | Number of gaps exceeding 10 days | 2 = two significant gaps |
| 36 | `long_gap_windows` | Array of `{start, end, gap_days}` for each long gap | Exact windows for season overlap check |
| 37 | `smoothing_method` | Algorithm name | Currently `gap_aware_local_median_weighted_mean` |
| 38 | `max_smoothing_gap_days` | Gap size that breaks smoothing continuity | Currently 12.0; gaps greater than this start a new segment |
| 39 | `local_window_days` | Local time window around each usable observation | Currently ±12 days |
| 40 | `minimum_local_neighbors` | Neighbor count required before smoothing | Currently 2, excluding the center point |
| 41 | `minimum_local_neighbors_excludes_center` | Whether the center observation counts as a neighbor | Currently `true` |
| 42 | `weighting_policy` | How weighted mean weights observations | `valid_fraction_time_distance` |
| 43 | `interpolation_policy` | Whether gaps are filled | `none` |
| 44 | `creates_synthetic_timestamps` | Whether preprocessing invents dates | `false` |
| 45 | `smooths_only_usable_observations` | Whether non-usable rows can be smoothed | `true` |
| 46 | `usable_valid_fraction_threshold` | The cutoff used | Currently 0.90 |
| 47 | `gap_risk` | **Classification of observation continuity** | `low` / `moderate` / `high` |
| 48 | `confidence_penalty` | How much gaps penalize assessment confidence | `low` / `moderate` / `high` |
| 49 | `gap_risk_reason` | Human-readable explanation | e.g. "Some continuity is missing..." |
| 50 | `confidence_inputs` | Raw numbers used for confidence calc | `usable_observation_count`, `gap_ratio`, `max_gap_days` |

---

### Stage 3: Seasonal Analysis — `season_windows.json`
*Per-season metrics. Multiple seasons per AOI.*

| # | Metric | What it is | Notes |
|---|---|---|---|
| 51 | `season_id` | `season_01`, `season_02`, ... | |
| 52 | `crossing_date` | First date of the accepted activity window | Legacy field name; this now points to the detected adaptive window boundary |
| 53 | `start_date` | Start date of the accepted activity window | Same boundary logic uses the local baseline and activity amplitude |
| 54 | `peak_date` | Date of **maximum smoothed NDVI** | |
| 55 | `end_date` | Last observation in the season | |
| 56 | `is_open` | Season still active at end of data? | `true` = we don't know when it ends yet |
| 57 | `peak_ndvi` | Maximum smoothed NDVI in the season | Core strength indicator |
| 58 | `duration_days` | Length of season in days | |
| 59 | `quality_label` | **Overall season quality** | `good` / `interrupted` / `weak` |
| 60 | `evidence_summary` | Concise text explaining the label | e.g. "Good season: peak_ndvi=0.550, rise_gain=0.350" |
| 61 | `confirmation_level` | How well do EVI/NDMI/NDWI support the NDVI signal? | `strong` / `moderate` / `weak` |
| 62 | `gap_overlap_count` | Number of long gaps overlapping this season | 0 is ideal |
| 63 | `gap_overlap_risk` | How seriously does gap overlap affect this season? | `low` / `moderate` / `high` |
| 64 | `gap_overlap_stage` | Which part of the season was obscured | `onset` / `peak` / `tail` / `multiple` / `none` |
| 65 | `season_confidence_note` | Overall confidence note | |

**Top-level in same file:**

| # | Metric | What it is |
|---|---|---|
| 66 | `season_count` | Number of seasons detected across the 2-year interval |
| 67 | `gap_risk` | Copied from quality_metrics for convenience |

---

### Stage 4: Land Assessment — `land_assessment.json`
*Final output. All the previous data is distilled into these fields. If evidence is insufficient, final automated public decisions are suppressed and manual review is required.*

**Core decisions:**

| # | Metric | What it is | Possible values |
|---|---|---|---|
| 68 | `assessment_status` | **Can the automated result be presented as final?** | `complete` / `manual_review_required` |
| 69 | `land_status` | **Is this land actively farmed?** | `active` / `intermittent` / `inactive`; `null` when manual review is required |
| 70 | `trend_2y` | **Is the land getting better or worse?** | `improving` / `stable` / `declining` / `uncertain`; `null` when manual review is required |
| 71 | `latest_season_performance.label` | How did the most recent season go? | `good` / `interrupted` / `weak`; `null` when manual review is required |
| 72 | `latest_season_performance.provisional` | Is the latest season still open? | `true` = not fully assessed yet |
| 73 | `latest_season_performance.confirmation_level` | Multi-index support for latest season | `strong` / `moderate` / `weak` |

**Confidence system:**

| # | Metric | What it is | Notes |
|---|---|---|---|
| 74 | `confidence.level` | **Overall assessment confidence** | `high` / `medium` / `low`; capped by evidence coverage |
| 75 | `confidence.reasons` | List of human-readable reasons | e.g. "Usable count is solid (72)" |
| 76 | `confidence.components.continuity` | Satellite coverage quality | `high` / `medium` / `low` |
| 77 | `confidence.components.season_clarity` | How clear were the season boundaries? | `high` / `medium` / `low` |
| 78 | `confidence.components.signal_strength` | How strong was the vegetation signal? | `high` / `medium` / `low` |

**Satellite evidence quality (separate from land quality):**

| # | Metric | What it is | Notes |
|---|---|---|---|
| 79 | `satellite_evidence_coverage.status` | **How good was the satellite data itself?** | `good` / `fair` / `limited` / `insufficient` |
| 80 | `satellite_evidence_coverage.rationale` | Why that status | Insufficient evidence triggers manual review |

**Risk flags (array, each entry):**

| # | Metric | What it is | Example values |
|---|---|---|---|
| 81 | `risk_flags[].code` | Machine-readable flag ID | `water_stress_risk`, `weak_activity_risk`, `possible_inactivity`, etc. |
| 82 | `risk_flags[].severity` | How seriously to take this flag | `high` / `moderate` / `low` |
| 83 | `risk_flags[].reason` | Human-readable explanation | "Latest season median NDMI is low" |

**Evidence trail (why the system said what it said):**

| # | Metric | What it is |
|---|---|---|
| 84 | `evidence.land_status_basis` | Text explaining why active/inactive, or why manual review is required |
| 85 | `evidence.trend_basis` | Text explaining improving/declining, or why trend is suppressed |
| 86 | `evidence.latest_season_basis` | Raw evidence for latest season |
| 87 | `evidence.gap_note` | Gap-related limitation note |

**Interval-level aggregate metrics:**

| # | Metric | What it is | Notes |
|---|---|---|---|
| 88 | `metrics_summary.active_observation_fraction` / `activity_coverage_fraction` | **Fraction of usable observations inside confirmed activity windows** | Key input to land_status. 0.55 = 55% of usable observations fall within confirmed windows |
| 89 | `metrics_summary.interval_max_ndvi` | Highest smoothed NDVI across the entire 2 years | |
| 90 | `metrics_summary.interval_max_evi` | Highest smoothed EVI across the 2 years | |
| 91 | `metrics_summary.interval_median_ndmi` | Typical NDMI across the 2 years | Negative = dry, positive = moist |
| 92 | `metrics_summary.interval_median_ndwi` | Typical NDWI across the 2 years | Negative = vegetation, positive = water |

**Per-season metrics (inside `metrics_summary.season_strength[]`):**

| # | Metric | What it is | Notes |
|---|---|---|---|
| 93 | `auc_ndvi` | **Area under the NDVI curve** during the season | Measures total "greenwork" — more complete than just peak |
| 94 | `peak_evi` | Max EVI during the season | Cross-check on density |
| 95 | `median_ndmi` | Typical moisture during the season | |
| 96 | `median_ndwi` | Typical wetness during the season | |

---

### Grand Total: **96 distinct metrics** across all 4 stages

For a **condensed reference** or one-pager for a professor, these are the most important:

**The 11 metrics that tell the whole story:**

| Metric | What it answers |
|---|---|
| `valid_fraction` | How clear was the satellite view of this field on this day? |
| `usable_observation_count` | How many usable days did we actually get over 2 years? |
| `gap_ratio` | How much did clouds blind us? |
| `season_count` | How many times did the farmer grow something? |
| `peak_ndvi` (per season) | How lush did it get? |
| `quality_label` (per season) | Did the season go well or poorly? |
| `assessment_status` | Can the automated result be shown, or is manual review required? |
| `land_status` | Is this field being actively farmed? |
| `trend_2y` | Getting better or worse over time? |
| `confidence.level` | How much should we trust this assessment? |
| `risk_flags` | What specific concerns should a lender investigate? |
