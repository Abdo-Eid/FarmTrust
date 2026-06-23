# PIPELINE

This document is the detailed implementation reference and runbook for the current FarmTrust build
pipeline. It describes the live end-to-end path from AOI input to ingestion, preprocessing, seasonal
analysis, and the final assessment output.

## Purpose

The current build is designed to produce an explainable, file-based land assessment for one AOI over a
selected interval, with enough evidence to support API and portal consumption.

The current-build output focuses on:

- smoothed vegetation and moisture signals
- vegetation activity-window count over the interval
- interval-based land status
- 2-year trend
- latest activity-window performance
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

Primary responsibilities (two phases, see `farmtrust_core/ingest/cube_pipeline.py`):

- **Phase 1 — `download_cubes`:** search Sentinel-2 L2A through STAC (Planetary Computer), filter by `eo:cloud_cover`, group items by solar day, and load each day as an AOI-clipped mosaic across all overlapping tiles via `odc.stac.load`. Fresh runs pre-allocate a time-sorted `cube.zarr`; reruns skip current days, append only missing date-range observations, backfill missing requested bands, then compact the local Zarr store back into physical time order. Repairing/deleting `B11` or adding `B05` does not re-download existing bands.
- **Phase 2 — `process_cubes`:** open `cube.zarr`, read 10m root bands plus native 20m grouped bands as needed, apply the AOI polygon mask + SCL validity classes, apply the BOA offset `(DN-1000)/10000`, compute per-day index statistics and `valid_fraction`, and emit `indices_timeseries.csv`. Derived stats are not written back into the source cube.
- Separating the phases means a policy change (offset, SCL classes, a new index) reprocesses via Phase 2 only; adding or repairing a source band backfills only that band.

Main code:

- `scripts/ingest_aoi.py` (CLI)
- `farmtrust_core/ingest/runner.py` (loader-agnostic seam: `run_ingestion`, `IngestCancelled`)
- `farmtrust_core/ingest/cube_pipeline.py` (two-phase orchestrator)
- `farmtrust_core/ingest/cube_loader.py` (`odc.stac.load` wrapper, per-band resampling, raw DN)
- `farmtrust_core/ingest/cube_stats.py` (BOA offset, AOI mask, per-day stats — pure, no I/O)
- `farmtrust_core/ingest/config.py`
- `farmtrust_core/ingest/utils.py`

Main outputs:

- `data/<aoi_id>/cube.zarr` — **primary source artifact**: raw-DN pixels, per-day provenance, and config. Root stores the 10m grid (`B02 B03 B04 B08`) plus time/provenance; the `20m` group stores native 20m source bands (`B05 B06 B07 B8A B11 B12 SCL`) when requested.
- `data/<aoi_id>/indices_timeseries.csv` — derived per-solar-day export (downstream handoff)
- `data/<aoi_id>/run_metadata.json` — run config (downstream contract; Phase 2 reads config here)
- `data/<aoi_id>/scenes_index.jsonl` — operational write-ahead ledger (v4+): one line per attempted solar day with `cache_key`, day `status`, and per-band `band_status` when backfill is used

AOI and window notes:

- intended assessment lookback is the last `24` months UTC
- demo and smoke-test runs may use shorter configured windows to validate code paths quickly
- metadata includes `window` and `lookback_months`
- one row is emitted per solar-day mosaic
- STAC search currently uses the AOI bbox
- `odc.stac.load` clips to the AOI bbox and aligns to centroid-estimated UTM, reading only the needed COG windows over HTTP; 10m bands are stored on the root grid and 20m bands are stored in the native `20m` group
- when polygon geometry is provided, the pipeline applies a polygon mask on the loaded cube grid
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

Current index output includes per-solar-day values for:

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

Observation cadence is irregular and keyed by solar-day mosaics. Fixed-interval views belong downstream in preprocessing or analysis. Missing values remain null/NaN so downstream stages can reason explicitly about observation count and gaps.

Local reuse behavior:

- the active pipeline still queries STAC on each run
- local reuse is solar-day based through `scenes_index.jsonl` (v4+ JSONL; one operational line per solar day, with per-band status when backfill is used)
- the ledger stores `cache_key` + `status` and can store `band_status`; provenance (`item_ids`, `mgrs_tiles`, `min_cloud_cover`) lives in `cube.zarr`, while derived stats live in `indices_timeseries.csv`
- the ledger — not the cube's time axis — is authoritative about which days are real, so failed/partial (zero-filled) slots are never processed
- Phase 1 skips day downloads when the stored `cache_key` matches, status is `downloaded`/legacy `ok`, and all requested bands exist; missing dates trigger day-level backfill, missing bands trigger band-only backfill, and the cube is physically sorted after local compaction. Phase 2 recomputes derived stats from cube pixels and rewrites `indices_timeseries.csv`
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
- Assessment confidence means confidence in FarmTrust's conclusion, given satellite coverage, observation continuity, activity-window clarity, and signal strength. It does not mean confidence in the land itself.
- Cloud gaps or weak coverage can lower assessment confidence, but they should not by themselves create a land risk flag such as abandonment, salinity, waterlogging, or encroachment.

Interpretation layers:

- Raw metrics: `valid_fraction`, `total_observation_count`, `usable_observation_count`, `dropped_observation_count`, `max_gap_days`, `median_gap_days`, `gap_ratio`, `long_gap_count`, `long_gap_windows`.
- Internal continuity classification: `gap_risk`, `confidence_penalty`, and `gap_risk_reason` describe how observation gaps affect evidence reliability.
- User-facing interpretation: `satellite_evidence_coverage` should be communicated as `good`, `fair`, `limited`, or `insufficient`.
- Assessment reliability: assessment confidence should be communicated as `high`, `medium`, or `low`, with a short reason tied to evidence coverage, activity-window clarity, and signal strength.

Current interpretation policy:

- `good` coverage: enough usable observations and no important long gaps; proceed normally.
- `fair` coverage: some gaps exist but they do not dominate the assessment window; proceed with normal labels and clear evidence notes.
- `limited` coverage: important gaps exist; proceed only with caution wording and lower assessment confidence.
- `insufficient` coverage: usable observations are too sparse or gaps dominate critical periods; assessment should be incomplete, retried with a different window/source, or sent to manual review.

Threshold note:

- The current code classifies continuity with `gap_risk` thresholds below.
- Final thresholds for user-facing `satellite_evidence_coverage` and the `insufficient` branch still need product/validation review before they become portal/report contract fields.

Operational notes:

- downstream activity-window analysis depends on `is_usable = true`, populated `ndvi_smoothed`, and required quality metric keys
- changes to `valid_fraction_threshold`, smoothing method, or expected cadence can shift activity-window boundaries and should be re-reviewed visually
- daily duplicate handling matters because overlapping tiles and scene variants can produce repeated observation days

### 3. Activity-window analysis

Entrypoint:

```powershell
python scripts/seasonal_analysis.py --aoi-id <aoi_id>
```

Primary responsibilities:

- detect vegetation activity windows from smoothed NDVI
- identify observed crossing/start/peak/end dates for the detected activity window
- label activity windows as `good`, `interrupted`, or `weak`
- confirm activity windows using EVI/NDMI/NDWI support signals
- record whether each activity window overlaps long observation gaps

Main code:

- `scripts/seasonal_analysis.py`
- `farmtrust_core/seasonal/seasons.py`

Input contract:

- input directory: `data/preprocess/<aoi_id>/`
- required files: `ndvi_smoothed.csv`, `quality_metrics.json`
- required CSV columns: `timestamp`, `ndvi_smoothed`, `evi_smoothed`, `ndmi_smoothed`, `ndwi_smoothed`, `is_usable`, `valid_fraction`, `source_row_count`
- required quality keys: `aoi_id`, `usable_observation_count`, `gap_ratio`, `max_gap_days`, `gap_risk`

Detector behavior:

- detection uses gap-aware smoothed NDVI as the primary activity signal
- output field names remain season-oriented for compatibility, but `season` means detected vegetation activity window, not an agronomic crop season
- detector model is `adaptive_prominence_to_noise`; it does not use a fixed NDVI activity floor or fixed NDVI amplitude gate
- low-envelope support uses the 20th percentile of smoothed NDVI within `±90.0` days; if fewer than `5` local observations exist, it falls back to the full-series 20th percentile
- peak candidates are local maxima in the smoothed NDVI curve, using only real usable observations
- each candidate is measured by `prominence_ndvi / noise_floor_ndvi`, where the noise floor is estimated from the field's own short-term movement and residual dispersion
- confirmed candidates require `prominence_to_noise_ratio >= 3.8`; borderline candidates require `>= 2.5` and are reported separately from confirmed seasons
- observed boundaries use a relative threshold of `20%` of candidate prominence from the local shoulder, not an absolute NDVI value
- no interpolation is performed and no synthetic dates or peaks are created
- a retained window needs at least `4` usable observations and at least `20.0` days of observed duration
- peak date is the timestamp with maximum `ndvi_smoothed` inside the retained window
- lifecycle status is explicit: `complete`, `open_right`, `open_left`, or `open_both`
- right-edge active windows are emitted with `is_open = true`, `provisional = true`, `lifecycle_status = "open_right"`, and `end_boundary_certainty = "open"`
- left-edge windows that were already active at the first observation are retained with `lifecycle_status = "open_left"`, `provisional = true`, and `start_boundary_certainty = "open"`

Quality labels:

- `good` means a complete window has strong field-relative prominence compared with estimated noise
- `interrupted` describes a large one-step NDVI drop relative to the candidate prominence, not a known crop-stage failure
- `weak` describes confirmed activity with weaker or provisional signal shape
- EVI/NDMI/NDWI confirmation is relative to each signal's own window behavior; it does not use fixed EVI/NDMI/NDWI cutoffs and does not by itself rewrite the NDVI shape label

Maximum drop is the largest one-step decrease between consecutive smoothed observations inside the activity window.

Main output:

- `data/seasonal/<aoi_id>/season_windows.json`

Top-level fields:

- `aoi_id`
- `season_count`
- `complete_window_count`
- `open_window_count`
- `borderline_window_count`
- `activity_detection_model`
- `seasons`
- `borderline_windows`

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
- `lifecycle_status`
- `detection_status`
- `prominence_ndvi`
- `noise_floor_ndvi`
- `prominence_to_noise_ratio`
- `season_confidence_note`
- `window_type`
- `provisional`
- `baseline_ndvi`
- `amplitude_ndvi`
- `boundary_threshold_ndvi`
- `usable_observation_count`
- `start_boundary_certainty`
- `peak_certainty`
- `end_boundary_certainty`
- `internal_gap_count`

Top-level terminology field:

- `terminology.season`: `detected vegetation activity window, not an agronomic crop season`

Activity-window boundaries should be reviewed with clear separation between adjacent windows rather than duplicated start/end boundary markers.

Gap context:

- observation gap classification does not directly create land or farming risk flags
- activity-window outputs record whether detected windows overlap long observation gaps
- onset zone is the first third of the observed window
- peak zone is `peak_date ± max(6 days, duration_days / 6)`
- tail zone is the last third of the observed window
- long gaps near onset/tail make boundary certainty limited and set `provisional = true`
- long gaps near peak set `peak_certainty = "limited"`
- internal long gaps increment `internal_gap_count`
- interpretation should become more cautious when satellite evidence coverage is limited or when long gaps overlap important activity-window stages

### 4. Land assessment

Entrypoint:

```powershell
python scripts/land_assessment.py --aoi-id <aoi_id>
```

Primary responsibilities:

- aggregate preprocessing and activity-window evidence
- classify interval-level `land_status`
- classify interval-level `trend_2y`
- determine latest activity-window performance in the compatibility field `latest_season_performance`
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

- `land_status` is inferred from observed interval-level vegetation activity and low-activity spans, not from one latest point
- `trend_2y` is derived from activity-window strength summaries such as peak NDVI and window AUC
- `latest_season_performance` uses the latest closed activity window when available; otherwise it uses the latest open activity window and marks it provisional
- risk flags stay conservative and should prefer `uncertain` or lower assessment confidence when continuity or activity-window clarity is weak
- assessment confidence surfaces component levels for satellite evidence coverage, activity-window clarity, and signal strength in addition to the final level
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

- uses interval-level vegetation activity-window behavior plus active-observation fraction
- does **not** decide status from the latest point alone

Current labels:

- `active`
- `intermittent`
- `inactive`

### Trend

Current behavior:

- compares activity-window strength across the interval
- currently uses peak NDVI and activity-window AUC as conservative strength summaries

Current labels:

- `improving`
- `stable`
- `declining`
- `uncertain`

### Latest activity-window performance

Current behavior:

- uses the latest closed activity window if available
- otherwise uses the latest open activity window and marks it provisional

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
- one activity-window entrypoint
- one assessment entrypoint

## Current limitations

- gap-risk thresholds are still static
- no interpolation is performed
- land status is rule-based, not region-calibrated
- crop category is deferred
- activity-window detection remains NDVI-primary
- CLI fixture input and portal/API polygon input both need validation when contracts change

These are acceptable for the current build as long as confidence and evidence remain explicit.
