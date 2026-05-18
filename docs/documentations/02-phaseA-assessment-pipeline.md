# Phase A Assessment Pipeline

This document is the detailed implementation reference for the current FarmTrust Phase A pipeline.
It describes the live end-to-end path from ingestion to preprocessing to seasonal analysis to the
final assessment output.

## Purpose

Phase A is designed to produce an explainable, file-based land assessment for one AOI over a
selected interval, with enough evidence to support later frontend and API integration.

The current Phase A output focuses on:

- smoothed vegetation and moisture signals
- season count over the interval
- interval-based land status
- 2-year trend
- latest-season performance
- conservative risk flags
- confidence and supporting evidence
- explicit gap diagnostics

Phase A does **not** currently output crop category.

## Canonical pipeline stages

### 1. Ingestion

Entrypoint:

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
```

Primary responsibilities:

- search Sentinel-2 scenes for the AOI and interval
- deduplicate scenes before download
- download AOI chips
- compute per-scene indices and quality values
- write the base ingestion outputs

Main code:

- `scripts/ingest_aoi.py`
- `farmtrust_core/ingest/`

Main outputs:

- `data/<aoi_id>/indices_timeseries.csv`
- `data/<aoi_id>/run_metadata.json`
- `data/<aoi_id>/scenes_index.json`
- `data/<aoi_id>/chips/...`

### 2. Preprocessing

Entrypoint:

```powershell
python scripts/preprocess_timeseries.py --aoi-id <aoi_id>
```

Primary responsibilities:

- collapse same-day duplicates
- filter usable observations with `valid_fraction >= 0.90`
- smooth the most valuable signals
- compute continuity metrics and gap diagnostics

Main code:

- `scripts/preprocess_timeseries.py`
- `farmtrust_core/preprocess/pipeline.py`
- `farmtrust_core/preprocess/gaps.py`
- `farmtrust_core/preprocess/smoothing.py`

Current smoothed signals:

- `ndvi_smoothed`
- `evi_smoothed`
- `ndmi_smoothed`
- `ndwi_smoothed`

Main outputs:

- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`

Important quality fields:

- `gap_ratio`
- `max_gap_days`
- `median_gap_days`
- `gap_risk`
- `long_gap_count`
- `long_gap_windows`

`long_gap_windows` records explicit high-caution continuity windows using the current preprocessing
threshold logic. This is intentionally visible output, not hidden internal state.

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

Main output:

- `data/seasonal/<aoi_id>/season_windows.json`

Important season fields:

- `season_count`
- `quality_label`
- `confirmation_level`
- `gap_overlap_count`
- `gap_overlap_risk`
- `evidence_summary`

Season boundaries should be reviewed with clear separation between adjacent seasons rather than duplicated start/end boundary markers.

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
- compute assessment `confidence`

Main code:

- `scripts/land_assessment.py`
- `farmtrust_core/scoring/rules.py`
- `farmtrust_core/scoring/evidence.py`

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

Important assessment diagnostics:

- `metrics_summary.long_gap_count`
- `metrics_summary.long_gap_windows`
- `metrics_summary.season_strength[].gap_overlap_count`
- `metrics_summary.season_strength[].gap_overlap_risk`

## Current decision rules

### Gap risk

Current preprocessing cadence assumption:

- `EXPECTED_CADENCE_DAYS = 5.0`

Current classification logic:

- `high` if `max_gap_days > 15` or `gap_ratio > 0.30`
- `moderate` if `max_gap_days > 10` or `gap_ratio > 0.15`
- `low` otherwise

Important note:

- the system does **not** blindly fill long gaps in Phase A
- instead, it exposes them explicitly and lowers confidence conservatively

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
uv run ingest-aoi --config scripts/ingest_demo.json
python scripts/preprocess_timeseries.py --aoi-id aoi_demo_01
python scripts/seasonal_analysis.py --aoi-id aoi_demo_01
python scripts/land_assessment.py --aoi-id aoi_demo_01
```

## What was intentionally removed

The repo previously contained older exploratory artifacts around ingestion path exploration, satellite fallback exploration, and ad hoc diagnostics. Those were useful during early experimentation, but they are not part of the current canonical Phase A path.

The current Phase A surface should stay focused on:

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
- frontend/API integration is still downstream from the file-based outputs

These are acceptable for Phase A as long as confidence and evidence remain explicit.
