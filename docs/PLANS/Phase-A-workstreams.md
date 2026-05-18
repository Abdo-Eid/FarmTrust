# Phase A Workstreams

This document consolidates the active Phase A workstream notes that were previously split across separate plan files. It is documentation, not a checklist or planning board.

Source files merged:
- `P-01-starter-pipeline.md`
- `P-02 - Data Ingestion (Phase A).md`
- `P-02-time-series-preprocessing.md`
- `P-03-seasonal-analysis.md`

The reusable template remains separate at `P-00-template.md`.

## Phase A Purpose

Phase A proves a file-based satellite assessment pipeline that can run locally before the portal, API, production storage, or full schema governance are introduced.

The pipeline turns an Area of Interest (AOI) into raw satellite index time series, preprocessing quality signals, detected season windows, and a downstream assessment handoff. The emphasis is reliability, reproducibility, explainability, and clear role handoffs.

## Shared Pipeline

The Phase A flow is:

1. AOI ingestion produces per-scene index statistics and run metadata.
2. Time-series preprocessing collapses duplicate observation days, filters weak observations, smooths core metrics, and computes quality/gap signals.
3. Seasonal analysis detects season windows from smoothed NDVI and assigns rule-based quality labels.
4. Scoring consumes season windows, quality metrics, and basic index statistics to produce a conservative land assessment.

Current handoffs are file-based so each role can test independently without waiting for API or database work.

## Ownership

- Data ingestion owns satellite access, AOI handling, scene selection, chip reads, index computation, caching, and raw AOI outputs.
- ML/time-series preprocessing owns duplicate-day merge logic, usability filtering, smoothing, gap metrics, and preprocessing outputs.
- ML/seasonal analysis owns season-window detection, onset/peak/end derivation, season quality labels, and the seasonal JSON handoff.
- ML/scoring owns interval-level land status, trend, latest-season summary, risk flags, confidence, and evidence summaries.

## Shared Boundaries

In scope:
- Sentinel-2 based AOI ingestion for the current implemented path.
- Local file outputs for Phase A development.
- Deterministic preprocessing and seasonal rules.
- Reusable local outputs for repeated development runs.

Out of scope:
- Database-backed persistence.
- Full schema governance in `contracts/schemas/`.
- Automated tests; no test suite is present yet.
- Learned seasonal detectors or credit scoring models.
- Ground sensors or field visits.
- Canonical monthly resampling, interpolation, or synthetic timestamps.

Phase A integration status:
- The frontend portal is implemented with mock data as the current UI fixture, and those fixtures are intentionally retained to show succeeded, queued/running, failed, risk, confidence, and evidence states.
- The Add Land portal flow now uses draw-only polygon AOI input: users click land corners on the map, click near the first corner to close, can drag corners before submission, and submit calculated feddan area plus GeoJSON polygon geometry.
- New portal submissions currently enter the queued/processing mock path; backend integration is the path for making newly submitted polygon inputs trigger real land assessment processing while preserving the fixture lands for UI/demo coverage.
- FastAPI backend integration is part of Phase A and is the path for replacing new-submission mock processing with real land assessment results.
- FastAPI runs or triggers the pipeline, reads the generated `land_assessment.json` artifact, maps it into API response DTOs, and sends those responses to the portal. The portal should not depend on the raw artifact path or filename.

## Data Ingestion

### Role Summary

Data ingestion makes satellite data reliably available for downstream analysis. Given an AOI, it fetches satellite imagery and produces raw index time-series for the intended 24-month assessment window.

The focus is data availability, correctness, reproducibility, and a clean handoff to downstream ML roles. The portal UI exists, but backend processing is not yet connected to new portal submissions, so ingestion remains validated using configurable fixture AOIs and local runtime outputs.

### AOI Handling

- Current implemented CLI input is bbox-based through args/config.
- The portal implements product AOI capture as draw-only polygon input: click land corners, close near the first corner, edit vertices before submit, and calculate area client-side.
- Polygon ingestion is the correct backend target behavior, but it is not yet the active CLI input path or connected worker path.

### Satellite Access

- Sentinel-2 L2A is the primary source.
- STAC access uses Planetary Computer and supports multiple endpoints.
- Planetary Computer signing is handled softly where needed.
- Optional cloud-cover pre-filtering is supported.
- Current implemented ingestion path uses Sentinel-2.
- Satellite options are a future technical discussion: compare Sentinel-2, Landsat, and other possible sources, including when and why each should be used.

### Index Output

Ingestion produces per-scene timestamps and index values for:
- NDVI
- EVI
- NDMI
- NDWI
- MNDWI

Scene cadence is irregular and per item timestamp. Fixed-interval views belong downstream in preprocessing or analysis. Missing values remain null/NaN so downstream roles can explicitly reason about observation count and gaps.

### Persistence

- Scene index: `data/<aoi_id>/scenes_index.json`
- AOI outputs: `data/<aoi_id>/`
- Time series: `data/<aoi_id>/indices_timeseries.csv`
- Run metadata: `data/<aoi_id>/run_metadata.json`
- Chips and manifests: `data/<aoi_id>/chips/<item_id>/`

### Local Reuse Behavior

- The active pipeline still queries STAC on each run.
- The kept reuse mechanism is local scene/chip reuse: `scenes_index.json` stores per-scene status, fingerprint, stats, and provenance.
- A scene is skipped only when the scene exists in `scenes_index.json`, its fingerprint matches the current AOI/config/date/mask settings, its status is `ok`, and all expected chip files exist.
- Cached scenes rebuild `indices_timeseries.csv` rows from `scenes_index.json` instead of re-downloading and reprocessing raster chips.
- The unused STAC query-result cache was removed; there is no TTL/env-var cache for STAC search responses.

### Code Inventory

- `farmtrust_core/ingest/stac_client.py`: reusable STAC search with endpoint fallback and soft Planetary Computer signing.
- `farmtrust_core/ingest/indices.py`: NDVI, EVI, NDMI, NDWI, and MNDWI computation.
- `farmtrust_core/ingest/config.py`: bbox parsing, default dates, and config loading.
- `farmtrust_core/ingest/utils.py`: `utc_now_iso`, `safe_write_text`, and fingerprint helpers.
- `farmtrust_core/ingest/window_read.py`: AOI window reads, reprojection, and GeoTIFF writes.
- `scripts/ingest_aoi.py`: end-to-end ingestion entrypoint.

### Runtime

Setup from repo root:

```powershell
uv sync --extra data
```

Run ingestion for an AOI:

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
```

### ML Handoff Contract

- Intended assessment lookback is last `24` months UTC.
- Demo and smoke-test runs may use shorter date windows to test code paths quickly; this is a configurable fixture choice, not a pipeline limitation.
- The same ingestion entrypoint can be configured for the intended assessment window when demo or validation evidence requires it.
- Metadata includes `window` and `lookback_months`.
- One row is emitted per scene timestamp in Phase A.
- Required downstream columns include `timestamp`, `source`, `ndvi`, `evi`, `ndmi`, `ndwi`, and `mndwi` where available.
- Downstream stages must use observation-count and gap metrics instead of assuming contiguous sampling.
- Metadata should explain gaps and coverage limits.

## Time-Series Preprocessing

### Role Summary

Time-series preprocessing consumes ingestion output, validates the input contract, collapses duplicate observation days, filters weak observations, smooths core metrics, and computes quality/confidence inputs for seasonal and scoring work.

Implementation baseline exists and is runnable through the CLI. Output files are generated runtime artifacts and do not need to be committed exactly for the implementation to be considered present.

### Current Status

- Core preprocessing code exists in `farmtrust_core/preprocess/`.
- CLI entrypoint exists at `scripts/preprocess_timeseries.py`.
- Preprocessing outputs are runtime artifacts under `data/preprocess/<aoi_id>/`; their absence from the repo snapshot does not mean the code path is missing.

### Input Contract

Input directory: `data/<aoi_id>/`

Required input files:
- `indices_timeseries.csv`
- `run_metadata.json`

Required CSV columns:
- `item_id`
- `timestamp`
- `valid_fraction`
- `ndvi_mean`

### Processing Behavior

- Timestamps are parsed and normalized to UTC.
- Observations are sorted before merge/filter operations.
- Duplicate observations are grouped by UTC calendar day.
- Same-day duplicates are merged using valid-fraction-weighted averaging.
- Negative weights are clamped to `0`; when total weight is `0`, a simple arithmetic mean is used.
- Usable observations require `valid_fraction >= 0.90`.
- Non-usable rows remain in the output for review, but do not receive smoothed values.
- Smoothing is applied only to usable values.
- The smoothing method is `rolling_median_3_then_mean_3`.
- No synthetic timestamps are created.
- No interpolation is performed.

### Smoothed Metrics

Current preprocessing smooths:
- NDVI
- EVI
- NDMI
- NDWI

### Gap Metrics

Gap metrics are computed from usable timestamps with an expected cadence of `5.0` days.

Computed fields include:
- `gap_ratio`
- `max_gap_days`
- `median_gap_days`
- `gap_risk`
- `confidence_penalty`
- `gap_risk_reason`
- plus gap diagnostics such as `long_gap_count` and `long_gap_windows`

`gap_ratio` is the sum of gap days beyond expected cadence divided by the usable-series span, bounded to `[0, 1]`.

Gap risk classification:
- `high` when `max_gap_days > 15` or `gap_ratio > 0.30`
- `moderate` when `max_gap_days > 10` or `gap_ratio > 0.15`
- `low` otherwise

Seasonal analysis should keep running when gap risk is moderate or high, but downstream interpretation should become more cautious.

### Output Contract

Output directory: `data/preprocess/<aoi_id>/`

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

`quality_metrics.json` fields:
- `aoi_id`
- `total_observation_count`
- `merged_observation_count`
- `usable_observation_count`
- `dropped_observation_count`
- `gap_ratio`
- `max_gap_days`
- `median_gap_days`
- `smoothing_method`
- `usable_valid_fraction_threshold`
- `gap_risk`
- `confidence_penalty`
- `gap_risk_reason`
- `confidence_inputs`
- plus gap diagnostics such as `long_gap_count` and `long_gap_windows`

### Runtime

```powershell
python scripts\preprocess_timeseries.py --aoi-id aoi_demo_01
```

```powershell
python scripts\preprocess_timeseries.py --input-dir data\aoi_demo_01 --output-dir data\preprocess\aoi_demo_01
```

### Operational Notes

- Downstream seasonal analysis depends on `is_usable = true`, populated `ndvi_smoothed`, and required quality metric keys.
- Changes to `valid_fraction_threshold`, smoothing method, or expected cadence can shift seasonal boundaries and should be re-reviewed visually.
- Gap diagnostics need a dedicated downstream-use discussion: define which pipeline stages consume long-gap windows, how they affect season interpretation, and how they surface in final assessment confidence.
- If accepted as stable shared truth, finalized handoff details should be reflected in `docs/ENGINEERING.md`.

### Learning

Daily duplicate handling matters. Overlapping tiles and scene variants produced repeated observation days; merging by calendar day made smoothing and gap metrics more meaningful.

## Seasonal Analysis

### Role Summary

Seasonal analysis consumes preprocessing outputs, detects season windows from smoothed NDVI, assigns rule-based quality labels, and produces a JSON handoff for assessment/scoring.

Implementation baseline exists and is runnable through the CLI. Output files are generated runtime artifacts and do not need to be committed exactly for the implementation to be considered present.

### Current Status

- Seasonal-analysis code exists in `farmtrust_core/seasonal/seasons.py`.
- CLI entrypoint exists at `scripts/seasonal_analysis.py`.
- Seasonal outputs are runtime artifacts under `data/seasonal/<aoi_id>/`; their absence from the repo snapshot does not mean the code path is missing.

Example demo season values from a local runtime output:
- `crossing_date = 2025-10-07`
- `start_date = 2025-09-24`
- `peak_date = 2025-12-31`
- `is_open = true`

### Input Contract

Input directory: `data/preprocess/<aoi_id>/`

Required input files:
- `ndvi_smoothed.csv`
- `quality_metrics.json`

Required CSV columns:
- `timestamp`
- `ndvi_smoothed`
- `evi_raw`
- `ndmi_raw`
- `ndwi_raw`
- `is_usable`
- `valid_fraction`
- `source_row_count`

Required quality metrics keys:
- `aoi_id`
- `usable_observation_count`
- `gap_ratio`
- `max_gap_days`
- `gap_risk`

The detector keeps only rows where `is_usable = true` and `ndvi_smoothed` is populated.

### Detector Behavior

- Detection uses smoothed NDVI only in the current baseline.
- Activity threshold is fixed at `0.18`.
- The threshold confirms active-period crossing; it is not treated as the literal agronomic start date.
- Active periods are contiguous usable smoothed observations where `ndvi_smoothed >= 0.18`.
- After the first threshold crossing, the detector backtracks to the earlier local low that begins the sustained rise.
- `crossing_date` records threshold crossing.
- `start_date` records the backtracked onset.
- Left-edge partial tails are excluded when the series begins active and peaks at the first observation.
- A segment is retained only when it has at least `4` active observations and at least `20.0` days of duration.
- Peak date is the timestamp with maximum `ndvi_smoothed` inside the retained window.
- End-of-series active windows are emitted as seasons and marked `is_open = true`.

### Quality Labels

Quality is rule-based:
- `weak` if `peak_ndvi < 0.24` or duration is under `20` days.
- `interrupted` if the maximum single-step drop is `>= 0.05`.
- `good` if `peak_ndvi >= 0.30` and rise gain from start to peak is `>= 0.08`.
- Otherwise, the season is `weak`.

`rise_gain` is `peak_ndvi - start_ndvi`. Maximum drop is the largest one-step decrease between consecutive smoothed observations inside the season window.

### Gap Context

Seasonal analysis reads `gap_risk` from `quality_metrics.json`. Gap risk does not directly change season boundaries, but interpretation becomes more cautious when continuity risk is moderate or high. This prevents false certainty without fabricating data through gap filling.

### Output Contract

Output directory: `data/seasonal/<aoi_id>/`

`season_windows.json` top-level fields:
- `aoi_id`
- `season_count`
- `seasons`

Per-season fields:
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
- `evidence_summary`
- `season_confidence_note`
- plus gap diagnostics such as `gap_overlap_count`, `gap_overlap_risk`, and `gap_overlap_stage`

### Runtime

```powershell
python scripts\seasonal_analysis.py --aoi-id aoi_demo_01
```

```powershell
python scripts\seasonal_analysis.py --input-dir data\preprocess\aoi_demo_01 --output-dir data\seasonal\aoi_demo_01
```

### Operational Notes

- Season boundaries should be re-reviewed if preprocessing changes threshold choices, smoothing method, valid-fraction threshold, or gap behavior.
- Seasonal gap-overlap diagnostics need a dedicated downstream-use discussion: define how overlap count, risk, and dominant season stage affect scoring, evidence, and final reviewer confidence.

### Learning

End-of-series seasons must be handled explicitly. The demo AOI contains an active late-season rise that is still increasing at the end of the available NDVI series. The detector keeps these windows instead of requiring a closed decline, preventing the latest season from being dropped before scoring.

## Scoring Baseline

Scoring is implemented as a Phase A baseline. It consumes run metadata, smoothed preprocessing output, quality metrics, and season windows.

Code locations:
- `scripts/land_assessment.py`
- `farmtrust_core/scoring/rules.py`
- `farmtrust_core/scoring/evidence.py`

Runtime:

```powershell
python scripts\land_assessment.py --aoi-id aoi_demo_01
```

Output path:
- `data/assessment/<aoi_id>/land_assessment.json`

This output is a generated runtime artifact. It is useful for local validation and backend handoff, but it does not need to be committed exactly for the scoring implementation to be considered present. FastAPI should read this artifact and expose shaped API responses rather than sending the raw JSON file directly to the frontend.

Implemented output fields include:
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

The scoring role should remain conservative and interval-based. It should preserve evidence links back to preprocessing and seasonal outputs rather than producing opaque labels.

## Current Phase A Constraints

- Ingestion outputs are the source of truth for raw satellite signals.
- Preprocessing outputs are the source of truth for usable smoothed series and gap/confidence metrics.
- Seasonal outputs are the source of truth for season boundaries and season quality labels.
- Production behavior belongs in `farmtrust_core/` and `scripts/`.
- Wider shared-truth changes belong in `docs/ENGINEERING.md` or `docs/PROJECT.md` after agreement.
