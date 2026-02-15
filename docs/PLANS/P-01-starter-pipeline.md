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
- Callable ingestion script with local cache for fast re-runs.
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
    - Responsibilities: STAC search, AOI-only window reads, SCL mask, per-scene indices, local cache.
    - Code location: `farmtrust_core.ingest` for logic; `worker/scripts/` for entrypoints.
    - Outputs: per-scene CSV + run metadata JSON for one AOI.
    - Fast test: re-run the same AOI and confirm cache reuse.

- **ML/time-series preprocessing**
    - Inputs: per-scene CSV from ingestion.
    - Responsibilities: filter by `valid_fraction`, smooth NDVI, compute gap metrics and confidence inputs.
    - Code location: `farmtrust_core.preprocess` for logic; `worker/scripts/` for entrypoints.
    - Outputs: smoothed NDVI series + quality metrics JSON.
    - Fast test: confirm `gap_ratio` and `max_gap_days` are non-null and stable.

- **ML/seasonal analysis**
    - Inputs: smoothed NDVI series + quality metrics.
    - Responsibilities: detect season windows, label season quality, record key dates.
    - Code location: `farmtrust_core.seasonal` for logic; `worker/scripts/` for entrypoints.
    - Outputs: season windows JSON with start/end dates and quality label.
    - Fast test: at least one season window in a 12-24 month span.

- **ML/scoring**
    - Inputs: season windows + quality metrics + basic NDVI stats.
    - Responsibilities: status/trend/season labels, conservative flags, evidence summary.
    - Code location: `farmtrust_core.scoring` for logic; `worker/scripts/` for entrypoints.
    - Outputs: scoring summary JSON with `land_status`, `trend_2y`, `season_performance`, `flags`, `confidence`.
    - Fast test: scoring output generated without missing required fields.

## Workflow

1. **Ingest AOI time series**
   Produce per-scene index stats and quality for a single AOI.
2. **Preprocess time series**
   Smooth NDVI, compute gap metrics, and derive confidence inputs.
3. **Seasonal analysis**
   Identify season windows and label season quality.
4. **Scoring**
   Produce status/trend/season labels and risk flags with evidence.

## R&D approach

- Keep each stage file-based with a small fixed schema.
- Validate with one AOI and one time window before adding complexity.
- Promote any shared-truth changes to ENGINEERING or PROJECT only after agreement.

## Plan & milestones

### Milestone 1 — Ingestion baseline

**Deliverables**

- `worker/scripts/ingest_aoi.py` (callable ingestion entrypoint importing `farmtrust_core.ingest`)
- `data/ingest/<aoi_id>/indices_timeseries.csv`
- `data/ingest/<aoi_id>/run_metadata.json`
- `data/cache/ingest/<aoi_id>/` (local cache for signed assets and windows)

**Acceptance**

- Script can be invoked with AOI + time window inputs and writes outputs to `data/ingest/<aoi_id>/`.
- CSV contains per-scene rows with `timestamp`, `valid_fraction`, and NDVI/EVI/NDMI/NDWI/MNDWI stats.
- JSON records AOI, time window, invalid SCL classes, and thresholds.
- Cache is used by default and can be cleared between runs.

### Milestone 2 — Time-series preprocessing baseline

**Deliverables**

- `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
- `data/preprocess/<aoi_id>/quality_metrics.json`

**Acceptance**

- Smoothed NDVI series has no missing timestamps for the chosen smoothing window.
- Quality metrics include `usable_observation_count`, `gap_ratio`, and `max_gap_days`.

### Milestone 3 — Seasonal + scoring baseline

**Deliverables**

- `data/seasonal/<aoi_id>/season_windows.json`
- `data/scoring/<aoi_id>/summary.json`

**Acceptance**

- Season windows include start/end dates and a season quality label.
- Scoring summary includes `land_status`, `trend_2y`, `season_performance`, `flags[]`, and `confidence`.

## Checklist (Definition of Done)

- [ ] Ingestion output exists for one AOI and 12–24 months
    - Notes: AOI-only window reads; no full tiles; local cache enabled.
    - [ ] Script runs with AOI + time window args
    - [ ] CSV has required columns
    - [ ] JSON has required metadata
    - [ ] Cache directory populated and re-used on re-run
- [ ] Preprocessing output exists and references ingestion output
    - Notes: smoothing + gap metrics only.
    - [ ] Smoothed NDVI file generated
    - [ ] Quality metrics file generated
- [ ] Seasonal output exists and references preprocessing output
    - Notes: simple season windows only.
    - [ ] Season windows file generated
- [ ] Scoring output exists and references seasonal output
    - Notes: conservative labels and evidence.
    - [ ] Summary file generated

## Findings & learnings

<finding title>
Short note on what happened, why it matters, and what you learned for yourself.
