# PIPELINE

This document is the detailed implementation reference and runbook for the current FarmTrust build
pipeline. It describes the live end-to-end path from AOI input to ingestion, preprocessing, seasonal
analysis, and the final assessment output.

## Purpose

The current build is designed to produce an explainable, file-based land assessment for one AOI over a
selected interval, with enough evidence to support API and portal consumption.

The current-build output focuses on:

- smoothed vegetation and moisture signals
- season count over the interval
- interval-based land status
- 2-year trend
- latest-season performance
- conservative risk flags
- satellite evidence coverage
- assessment confidence and supporting evidence
- explicit gap diagnostics

The current build does **not** currently output crop category.

## Boundaries and handoffs

Current pipeline boundaries:

- current product input is user-drawn polygon AOI geometry from the portal
- current local/demo CLI fixtures can still use bbox/config input for repeatable pipeline validation
- current stage handoffs are file-based so each stage can be tested independently
- FastAPI runs or triggers the pipeline, reads the generated assessment artifact, maps it into API DTOs, and sends shaped responses to the portal
- the frontend should not depend on raw runtime artifact paths or filenames

Current runtime artifacts are useful for local validation and backend handoff, but generated data files do not need to be committed for the implementation to be considered present.

## Canonical pipeline stages

### 1. Ingestion

Entrypoint:

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
```

Primary responsibilities:

- search Sentinel-2 L2A scenes for the AOI and interval through STAC, currently Planetary Computer
- apply optional cloud-cover filtering and deduplicate to one best scene per date/spacecraft before download
- read AOI chip windows, reproject/write GeoTIFF chips, and compute per-scene index statistics
- compute quality values such as valid fraction
- maintain local scene/chip reuse state
- write the base ingestion outputs

Main code:

- `scripts/ingest_aoi.py`
- `farmtrust_core/ingest/config.py`
- `farmtrust_core/ingest/dedup.py`
- `farmtrust_core/ingest/indices.py`
- `farmtrust_core/ingest/pipeline.py`
- `farmtrust_core/ingest/processor.py`
- `farmtrust_core/ingest/scene_index.py`
- `farmtrust_core/ingest/stac_client.py`
- `farmtrust_core/ingest/utils.py`
- `farmtrust_core/ingest/window_read.py`

Main outputs:

- `data/<aoi_id>/indices_timeseries.csv`
- `data/<aoi_id>/run_metadata.json`
- `data/<aoi_id>/scenes_index.json`
- `data/<aoi_id>/chips/...`

AOI and window notes:

- intended assessment lookback is the last `24` months UTC
- demo and smoke-test runs may use shorter configured windows to validate code paths quickly
- metadata includes `window` and `lookback_months`
- one row is emitted per scene timestamp in the current build
- STAC search currently uses the AOI bbox
- COG reads use the bbox as a rectangular raster window for efficient HTTP range reads
- when polygon geometry is provided, the pipeline applies a polygon mask inside that COG window
- index statistics and `valid_fraction` are computed only over pixels inside the polygon mask
- for bbox-only CLI fixtures, the whole bbox window is treated as the AOI

`valid_fraction` meaning:

- polygon AOI: usable pixels inside polygon / all pixels inside polygon
- bbox-only AOI: usable pixels inside bbox window / all pixels inside bbox window
- usable pixels are pixels not excluded by the current scene classification mask

Satellite access notes:

- Sentinel-2 L2A is the current implemented source
- STAC access uses Planetary Computer and supports endpoint fallback
- Planetary Computer signing is handled softly where needed
- broader satellite source strategy is unresolved and tracked in `OPEN_ITEMS.md`, including when and why to use Sentinel-2, Landsat, or other possible sources

Current index output includes per-scene values for:

- NDVI
- EVI
- NDMI
- NDWI
- MNDWI

Required downstream columns include:

- `timestamp`
- `source`
- `ndvi`
- `evi`
- `ndmi`
- `ndwi`
- `mndwi` where available

Scene cadence is irregular and per item timestamp. Fixed-interval views belong downstream in preprocessing or analysis. Missing values remain null/NaN so downstream stages can reason explicitly about observation count and gaps.

Local reuse behavior:

- the active pipeline still queries STAC on each run
- local reuse is scene/chip based through `scenes_index.json`
- `scenes_index.json` stores per-scene status, fingerprint, stats, and provenance
- a scene can skip download/reprocessing only when its stored fingerprint matches the current AOI/config/date/mask settings, its status is `ok`, and all expected chip files exist
- cached scenes rebuild `indices_timeseries.csv` rows from `scenes_index.json`
- there is no active STAC query-result TTL/env-var cache

### 2. Preprocessing

Entrypoint:

```powershell
python scripts/preprocess_timeseries.py --aoi-id <aoi_id>
```

Primary responsibilities:

- collapse same-day duplicates
- filter usable observations with `valid_fraction >= 0.90`
- smooth core vegetation and moisture signals
- compute continuity metrics and gap diagnostics
- interpret satellite evidence coverage separately from land condition

Main code:

- `scripts/preprocess_timeseries.py`
- `farmtrust_core/preprocess/pipeline.py`
- `farmtrust_core/preprocess/gaps.py`
- `farmtrust_core/preprocess/smoothing.py`

Input contract:

- input directory: `data/<aoi_id>/`
- required files: `indices_timeseries.csv`, `run_metadata.json`
- required CSV columns: `item_id`, `timestamp`, `valid_fraction`, `ndvi_mean`

Processing behavior:

- timestamps are parsed and normalized to UTC
- observations are sorted before merge/filter operations
- duplicate observations are grouped by UTC calendar day
- same-day duplicates are merged using valid-fraction-weighted averaging
- negative weights are clamped to `0`; when total weight is `0`, a simple arithmetic mean is used
- usable observations require `valid_fraction >= 0.90`
- non-usable rows remain in the output for review, but do not receive smoothed values
- smoothing is applied only to real usable observations
- the current smoothing method is `gap_aware_local_median_weighted_mean`
- usable-observation gaps greater than `12` days break smoothing continuity; gaps exactly `12` days remain continuous
- local smoothing uses a `±12` day window inside each continuous segment
- smoothing uses a local median pass followed by a weighted-mean pass
- weighted mean uses `valid_fraction / (1 + abs(delta_days) / 12.0)`
- observations with fewer than `2` usable neighbors inside the same segment/window keep raw values
- 1-point and 2-point continuous segments keep raw values
- no synthetic timestamps are created
- no interpolation is performed

Current smoothed signals:

- `ndvi_smoothed`
- `evi_smoothed`
- `ndmi_smoothed`
- `ndwi_smoothed`

Main outputs:

- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`

`ndvi_smoothed.csv` fields:

- `timestamp`
- `ndvi_raw`
- `ndvi_smoothed`
- `evi_raw`
- `evi_smoothed`
- `ndmi_raw`
- `ndmi_smoothed`
- `ndwi_raw`
- `ndwi_smoothed`
- `valid_fraction`
- `is_usable`
- `source_row_count`

Important quality fields:

- `aoi_id`
- `total_observation_count`
- `merged_observation_count`
- `usable_observation_count`
- `dropped_observation_count`
- `gap_ratio`
- `max_gap_days`
- `median_gap_days`
- `smoothing_method`
- `max_smoothing_gap_days`
- `local_window_days`
- `minimum_local_neighbors`
- `minimum_local_neighbors_excludes_center`
- `weighting_policy`
- `interpolation_policy`
- `creates_synthetic_timestamps`
- `smooths_only_usable_observations`
- `usable_valid_fraction_threshold`
- `gap_risk`
- `confidence_penalty`
- `gap_risk_reason`
- `confidence_inputs`
- `long_gap_count`
- `long_gap_windows`

`long_gap_windows` records explicit high-caution continuity windows using the current preprocessing
threshold logic. This is intentionally visible output, not hidden internal state.

`gap_ratio` is the sum of gap days beyond expected cadence divided by the usable-series span, bounded to `[0, 1]`.

Evidence coverage interpretation:

- Raw gap metrics describe satellite observation quality, not land or farmer quality.
- Internal fields such as `gap_risk`, `confidence_penalty`, and `gap_risk_reason` are pipeline interpretation helpers; they should not be shown as land risk flags.
- User-facing wording should use `satellite_evidence_coverage`, `evidence limitations`, and `assessment confidence`.
- Assessment confidence means confidence in FarmTrust's conclusion, given satellite coverage, observation continuity, season clarity, and signal strength. It does not mean confidence in the land itself.
- Cloud gaps or weak coverage can lower assessment confidence, but they should not by themselves create a land risk flag such as abandonment, salinity, waterlogging, or encroachment.

Interpretation layers:

- Raw metrics: `valid_fraction`, `total_observation_count`, `usable_observation_count`, `dropped_observation_count`, `max_gap_days`, `median_gap_days`, `gap_ratio`, `long_gap_count`, `long_gap_windows`.
- Internal continuity classification: `gap_risk`, `confidence_penalty`, and `gap_risk_reason` describe how observation gaps affect evidence reliability.
- User-facing interpretation: `satellite_evidence_coverage` should be communicated as `good`, `fair`, `limited`, or `insufficient`.
- Assessment reliability: assessment confidence should be communicated as `high`, `medium`, or `low`, with a short reason tied to evidence coverage, season clarity, and signal strength.

Current interpretation policy:

- `good` coverage: enough usable observations and no important long gaps; proceed normally.
- `fair` coverage: some gaps exist but they do not dominate the assessment window; proceed with normal labels and clear evidence notes.
- `limited` coverage: important gaps exist; proceed only with caution wording and lower assessment confidence.
- `insufficient` coverage: usable observations are too sparse or gaps dominate critical periods; assessment should be incomplete, retried with a different window/source, or sent to manual review.

Threshold note:

- The current code classifies continuity with `gap_risk` thresholds below.
- Final thresholds for user-facing `satellite_evidence_coverage` and the `insufficient` branch still need product/validation review before they become portal/report contract fields.

Operational notes:

- downstream seasonal analysis depends on `is_usable = true`, populated `ndvi_smoothed`, and required quality metric keys
- changes to `valid_fraction_threshold`, smoothing method, or expected cadence can shift seasonal boundaries and should be re-reviewed visually
- daily duplicate handling matters because overlapping tiles and scene variants can produce repeated observation days

### 3. Seasonal analysis

Entrypoint:

```powershell
python scripts/seasonal_analysis.py --aoi-id <aoi_id>
```

Primary responsibilities:

- detect season windows from smoothed NDVI
- identify crossing/start/peak/end dates
- label seasons as `good`, `interrupted`, or `weak`
- confirm seasons using EVI/NDMI/NDWI
- record whether each season overlaps long gap windows

Main code:

- `scripts/seasonal_analysis.py`
- `farmtrust_core/seasonal/seasons.py`

Input contract:

- input directory: `data/preprocess/<aoi_id>/`
- required files: `ndvi_smoothed.csv`, `quality_metrics.json`
- required CSV columns: `timestamp`, `ndvi_smoothed`, `evi_raw`, `ndmi_raw`, `ndwi_raw`, `is_usable`, `valid_fraction`, `source_row_count`
- required quality keys: `aoi_id`, `usable_observation_count`, `gap_ratio`, `max_gap_days`, `gap_risk`

Detector behavior:

- detection uses smoothed NDVI only in the current baseline
- activity threshold is fixed at `0.18`
- the threshold confirms active-period crossing; it is not treated as the literal agronomic start date
- active periods are contiguous usable smoothed observations where `ndvi_smoothed >= 0.18`
- after the first threshold crossing, the detector backtracks to the earlier local low that begins the sustained rise
- `crossing_date` records threshold crossing
- `start_date` records the backtracked onset
- left-edge partial tails are excluded when the series begins active and peaks at the first observation
- a segment is retained only when it has at least `4` active observations and at least `20.0` days of duration
- peak date is the timestamp with maximum `ndvi_smoothed` inside the retained window
- end-of-series active windows are emitted as seasons and marked `is_open = true`

Quality labels:

- `weak` if `peak_ndvi < 0.24` or duration is under `20` days
- `interrupted` if the maximum single-step drop is `>= 0.05`
- `good` if `peak_ndvi >= 0.30` and rise gain from start to peak is `>= 0.08`
- otherwise, the season is `weak`

`rise_gain` is `peak_ndvi - start_ndvi`. Maximum drop is the largest one-step decrease between consecutive smoothed observations inside the season window.

Main output:

- `data/seasonal/<aoi_id>/season_windows.json`

Top-level fields:

- `aoi_id`
- `season_count`
- `seasons`

Important season fields:

- `season_id`
- `crossing_date`
- `start_date`
- `peak_date`
- `end_date`
- `is_open`
- `peak_ndvi`
- `duration_days`
- `quality_label`
- `confirmation_level`
- `gap_overlap_count`
- `gap_overlap_risk`
- `gap_overlap_stage`
- `evidence_summary`
- `season_confidence_note`

Season boundaries should be reviewed with clear separation between adjacent seasons rather than duplicated start/end boundary markers.

Gap context:

- observation gap classification does not directly change season boundaries
- seasonal outputs record whether season windows overlap long observation gaps
- overlap diagnostics include severity and dominant touched stage: `onset`, `peak`, `tail`, or `multiple`
- interpretation should become more cautious when satellite evidence coverage is limited or when long gaps overlap important season stages

### 4. Land assessment

Entrypoint:

```powershell
python scripts/land_assessment.py --aoi-id <aoi_id>
```

Primary responsibilities:

- aggregate preprocessing and seasonal evidence
- classify interval-level `land_status`
- classify interval-level `trend_2y`
- determine `latest_season_performance`
- emit conservative `risk_flags`
- compute assessment confidence, meaning confidence in the assessment reliability

Main code:

- `scripts/land_assessment.py`
- `farmtrust_core/scoring/rules.py`
- `farmtrust_core/scoring/evidence.py`

Input files:

- `data/<aoi_id>/run_metadata.json`
- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`
- `data/seasonal/<aoi_id>/season_windows.json`

Main output:

- `data/assessment/<aoi_id>/land_assessment.json`

Backend handoff:

- `land_assessment.json` is an internal pipeline artifact.
- FastAPI runs or triggers the pipeline, reads this artifact, maps it into API response DTOs, and sends those shaped responses to the portal.
- The frontend should not depend on the raw file path or file name.

Top-level fields:

- `aoi_id`
- `interval`
- `land_status`
- `trend_2y`
- `season_count`
- `latest_season_performance`
- `risk_flags`
- `confidence`
- `evidence`
- `metrics_summary`

Assessment policy notes:

- `land_status` is inferred from interval-level behavior across seasons and low-activity spans, not from one latest point
- `trend_2y` is derived from season-level strength summaries such as peak NDVI and season AUC
- `latest_season_performance` uses the latest closed season when available; otherwise it uses the latest open season and marks it provisional
- risk flags stay conservative and should prefer `uncertain` or lower assessment confidence when continuity or season clarity is weak
- assessment confidence surfaces component levels for satellite evidence coverage, season clarity, and signal strength in addition to the final level
- satellite evidence limitations should be documented as evidence limitations, not as land/farmer problems
- crop category is skipped in the current build

Important assessment diagnostics:

- `metrics_summary.long_gap_count`
- `metrics_summary.long_gap_windows`
- `metrics_summary.season_strength[].gap_overlap_count`
- `metrics_summary.season_strength[].gap_overlap_risk`

## Current decision rules

### Observation continuity classification

`gap_risk` is the current internal field name for observation continuity classification. It describes satellite evidence reliability, not land risk.

Current preprocessing cadence assumption:

- `EXPECTED_CADENCE_DAYS = 5.0`

Current classification logic:

- `high` if `max_gap_days > 15` or `gap_ratio > 0.30`
- `moderate` if `max_gap_days > 10` or `gap_ratio > 0.15`
- `low` otherwise

Important note:

- the system does **not** blindly fill long gaps in the current build
- instead, it exposes them explicitly and lowers assessment confidence conservatively
- user-facing surfaces should not label this as `gap risk`; they should explain satellite evidence coverage and assessment reliability

### Land status

Current behavior:

- uses interval-level seasonal behavior plus active-observation fraction
- does **not** decide status from the latest point alone

Current labels:

- `active`
- `intermittent`
- `inactive`

### Trend

Current behavior:

- compares season-level strength across the interval
- currently uses peak NDVI and season AUC as conservative strength summaries

Current labels:

- `improving`
- `stable`
- `declining`
- `uncertain`

### Latest season performance

Current behavior:

- uses the latest closed season if available
- otherwise uses the latest open season and marks it provisional

Current labels:

- `good`
- `interrupted`
- `weak`

## Recommended execution order

For a clean AOI rerun:

```powershell
uv sync --extra data
```

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
python scripts/preprocess_timeseries.py --aoi-id aoi_demo_01
python scripts/seasonal_analysis.py --aoi-id aoi_demo_01
python scripts/land_assessment.py --aoi-id aoi_demo_01
```

## What was intentionally removed

The repo previously contained older exploratory artifacts around ingestion path exploration, satellite fallback exploration, and ad hoc diagnostics. Those were useful during early experimentation, but they are not part of the current canonical build path.

The current-build surface should stay focused on:

- one ingestion entrypoint
- one preprocessing entrypoint
- one seasonal entrypoint
- one assessment entrypoint

## Current limitations

- gap-risk thresholds are still static
- no interpolation is performed
- land status is rule-based, not region-calibrated
- crop category is deferred
- seasonal detection remains NDVI-primary
- CLI fixture input and portal/API polygon input both need validation when contracts change

These are acceptable for the current build as long as confidence and evidence remain explicit.
