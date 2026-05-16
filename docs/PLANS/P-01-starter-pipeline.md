# P-01 — Starter pipeline for three roles

This plan provides a minimal, testable end-to-end pipeline so ingestion, time-series, seasonal, and scoring roles can validate integration quickly and refine later. It defines a small shared contract and acceptance checks to avoid drift.

## Links

- PROJECT: <PROJECT §Phase A ownership>
- ENGINEERING: <ENGINEERING §Pipeline>
- DECISIONS: <2026-01-29 — Decision: Phase A role breakdown adjusted>

## Ownership & boundaries

**Owner:** Data ingestion (handoff to ML/time-series, ML/seasonal, ML/scoring)

## Overview of my task

Deliver a minimal pipeline contract and test flow that all three ML roles can run locally. The contract keeps ingestion lightweight (AOI-only, per-scene stats) and lets downstream roles test smoothing, season detection, and scoring without waiting for production storage or full schema hardening.

### In scope

- Shared starter contract: minimal input and output fields for each stage.
- Simple file-based handoffs (CSV + JSON) for quick testing.
- Callable ingestion script with AOI chip export and scene-index caching for fast re-runs.
- Acceptance checks that confirm each stage produced usable output.

### Out of scope (explicit non-goals)

- Full schema governance or long-term storage.
- Cross-run comparability and versioning discipline.
- Landsat fallback and multi-source fusion.

## Outcomes (what “done” looks like)

1. Ingestion produces per-scene time series + run metadata for one AOI and 12–24 months.
2. Time-series preprocessing outputs smoothed NDVI plus gap metrics and confidence inputs.
3. Seasonal and scoring outputs are generated from the preprocessing output, with labels and evidence.

## Role details (starter)

- **Data ingestion**
    - Inputs: AOI bbox (EPSG:4326), time window, cloud filter.
    - Responsibilities: STAC search, AOI-only window reads, SCL mask, per-scene indices, chip export, and scene-index caching.
    - Runtime mode: download chips + compute stats in one pass.
    - Code location: `scripts/ingest_aoi.py`.
    - Outputs: per-scene CSV + run metadata JSON + `scenes_index.json` + per-scene chips/manifest.
    - Fast test: re-run the same AOI and confirm skip/reuse behavior for existing scenes.

- **ML/time-series preprocessing**
    - Inputs: per-scene CSV from ingestion.
    - Responsibilities: filter by `valid_fraction`, smooth NDVI, compute gap metrics and confidence inputs.
    - Code location: `farmtrust_core.preprocess` for logic; `scripts/` for entrypoints.
    - Outputs: smoothed NDVI series + quality metrics JSON.
    - Fast test: confirm `gap_ratio` and `max_gap_days` are non-null and stable.

- **ML/seasonal analysis**
    - Inputs: smoothed NDVI series + quality metrics.
    - Responsibilities: detect season windows, label season quality, record key dates.
    - Code location: `farmtrust_core.seasonal` for logic; `scripts/` for entrypoints.
    - Outputs: season windows JSON with start/end dates and quality label.
    - Fast test: at least one season window in a 12-24 month span.

- **ML/scoring**
    - Inputs: season windows + quality metrics + basic NDVI stats.
    - Responsibilities: interval-based land status, trend, latest-season summary, conservative flags, evidence summary.
    - Code location: `farmtrust_core.scoring` for logic; `scripts/` for entrypoints.
    - Outputs: assessment JSON with `land_status`, `trend_2y`, `latest_season_performance`, `risk_flags`, `confidence`, and evidence summaries.
    - Fast test: assessment output generated without missing required fields and matches interval-level seasonal evidence.

## Workflow

1. **Ingest AOI time series**
   Produce per-scene index stats and quality for a single AOI.
2. **Preprocess time series**
   Smooth NDVI, compute gap metrics, and derive confidence inputs.
3. **Seasonal analysis**
   Identify season windows and label season quality.
4. **Scoring**
   Produce interval-based land assessment, season summary, and risk flags with evidence.

## R&D approach

- Keep each stage file-based with a small fixed schema.
- Validate with one AOI and one time window before adding complexity.
- Promote any shared-truth changes to ENGINEERING or PROJECT only after agreement.

## Plan & milestones

### Milestone 1 — Ingestion baseline

**Deliverables**

- `scripts/ingest_aoi.py` (callable ingestion entrypoint)
- `data/<aoi_id>/chips/<item_id>/` (AOI chips + `manifest.json`)
- `data/<aoi_id>/indices_timeseries.csv`
- `data/<aoi_id>/scenes_index.json`
- `data/<aoi_id>/run_metadata.json`

**Acceptance**

- Script can be invoked with AOI + time window inputs and writes outputs to `data/<aoi_id>/`.
- CSV contains per-scene rows with `timestamp`, `valid_fraction`, and NDVI/EVI/NDMI/NDWI/MNDWI stats.
- JSON records AOI, time window, invalid SCL classes, and thresholds.
- `scenes_index.json` records per-scene paths/status for rerun reuse.
- Chips are written per scene with expected bands and `manifest.json`.

### Milestone 1.5 — Ingestion core migration (stable parts first)

**Deliverables**

- `farmtrust_core/ingest/indices.py` with stable index/stat helpers moved from the script.
- `farmtrust_core/ingest/window_read.py` with stable AOI window read, reproject, and GeoTIFF write helpers.
- `farmtrust_core/ingest/stac_client.py` with stable STAC open/search/sort helpers.
- `scripts/ingest_aoi.py` remains runnable as CLI/orchestration and imports the migrated helpers.
- A simple loader script for downstream use.

**Acceptance**

- Output contract unchanged: `indices_timeseries.csv`, `scenes_index.json`, `run_metadata.json`, chips + manifests.
- Fingerprint + skip/reuse behavior unchanged.
- Existing config path (`scripts/ingest_demo.json`) still runs without changes.
- Migration only covers stable logic; optimizations are explicitly deferred.

### Milestone 1.6 — Ingestion optimization + selection research spike

**Intent**

Research and validate selection/throughput improvements before implementation. Capture findings and the chosen approach.
Willing to optimize the search and post-search of the script for faster, performant but keeping the quality.
thinking of add a post-search step to enforce min gap (e.g., 2–3 weeks) and prefer best cloud cover via a config flag; allow user-selected bands for faster retrieval; explore faster download over time; finalize the notebook with the run command, RGB TIFF plot, and a simple NDVI-over-time POC.

**Deliverables**

- Short research note (1–2 pages) summarizing findings, options, and recommended approach.
- Proposed config flags for scene selection, band selection, and download strategy.
- Updated acceptance targets for the implementation step that follows.

**Acceptance**

- 2–3 options documented with tradeoffs, evidence needed, and decision triggers.
- One recommended path selected (or explicitly deferred).
- No production code changes in this milestone.

### Milestone 2 — Time-series preprocessing baseline

**Deliverables**

- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`

**Acceptance**

- Smoothed NDVI series has no missing timestamps for the chosen smoothing window.
- Quality metrics include `usable_observation_count`, `gap_ratio`, and `max_gap_days`.

### Milestone 3 – Seasonal + scoring baseline

**Deliverables**

- `data/seasonal/<aoi_id>/season_windows.json`
- `data/assessment/<aoi_id>/phase_a_assessment.json`

**Acceptance**

- Season windows include start/end dates and a season quality label.
- Assessment summary includes `land_status`, `trend_2y`, `season_count`, `latest_season_performance`, `risk_flags[]`, and `confidence`.

## Checklist (Definition of Done)

- [X] Ingestion output exists for one AOI and 12–24 months
    - Notes: AOI-only window reads; no full tiles; chips + scene-index caching enabled.
    - [x] Script runs with AOI + time window args
    - [x] CSV has required columns
    - [x] JSON has required metadata
    - [x] `scenes_index.json` populated
    - [x] Chips directory populated with per-scene manifest
    - [X] 12–24 month target run validated for production AOI
- [ ] Ingestion core migration complete (stable parts only)
    - [X] `farmtrust_core/ingest/indices.py` populated
        - Moved: compute_stats, compute_ndvi, compute_evi, compute_ndmi, compute_ndwi, compute_mndwi
        - Why: pure math + no I/O; least likely to change during optimization work
    - [X] `farmtrust_core/ingest/config.py` populated
        - Moved: parse_bbox, normalize_bbox, default_dates, load_config
        - Why: stable parsing and config load with minimal coupling to processing logic
    - [X] `farmtrust_core/ingest/utils.py` populated
        - Moved: utc_now_iso, safe_write_text, compute_fingerprint
        - Why: shared utilities used across ingestion; low behavior risk
    - [ ] `farmtrust_core/ingest/window_read.py` populated
    - [ ] `farmtrust_core/ingest/stac_client.py` populated
    - [ ] Script still produces unchanged outputs
- [ ] Simple loader script planned for downstream users
- [ ] Milestone 1.6 research spike complete (notes + recommended approach)
    - [ ] Scene-spacing filter options evaluated (min-gap, best-cloud, buckets)
    - [ ] User-selected band/indices options evaluated
    - [ ] Retrieval speed options evaluated
    - [ ] Notebook POC finalization scope defined
- [ ] Preprocessing output exists and references ingestion output
    - Notes: smoothing + gap metrics only.
    - [ ] Smoothed NDVI file generated
    - [ ] Quality metrics file generated
- [ ] Seasonal output exists and references preprocessing output
    - Notes: simple season windows only.
    - [ ] Season windows file generated
- [ ] Scoring output exists and references seasonal output
    - Notes: conservative interval-based labels and evidence.
    - [ ] Assessment file generated

## Findings & learnings

[Migration and optimization research notes](../documentations/00-phaseA_ingestion_full_writeup.md)
<finding title>
Short note on what happened, why it matters, and what you learned for yourself.
