# ENGINEERING

Purpose: single place for engineering truth (architecture, pipeline, ops, interfaces, technical risks).

## Links

- DECISIONS entry: <YYYY-MM-DD — Decision: ...>
- PROJECT section: <PROJECT §...>
- PLAN: <P-xx — name>

## System overview

- Satellite time-series pipeline producing plot-level indicators, confidence, and risk flags.
- Outputs stored for fast portal rendering and report export.

## MVP stack

- Data access: Sentinel-2 via cloud STAC (Planetary Computer or AWS Open Data).
- Processing: Python (xarray, rasterio, pystac-client) for time-series features.
- API: FastAPI for job submission, results, and report export.
- Storage: Postgres + PostGIS for AOIs and results; object storage for PDFs/rasters.
- Portal: React/Next.js with MapLibre or Leaflet for AOI input and summaries.
- Jobs: lightweight worker (Celery or cron-driven) for analysis runs.

## Repo structure (Phase A)

- Root services with shared contracts:
    - api/ (FastAPI)
    - farmtrust_core/ (core pipeline package)
    - scripts/ (CLI entry points)
    - portal/ (Next.js)
    - contracts/ (schemas)
    - docs/ (documentation truth)
- `farmtrust_core/` is the single importable top-level Python package for core pipeline logic reused by worker and API services.
- `farmtrust_core/ingest/` submodules:
    - `config.py` — bbox parsing, default dates
    - `indices.py` — NDVI, EVI, NDMI, NDWI, MNDWI computation
    - `stac_client.py` — STAC search with endpoint fallback and PC signing
    - `utils.py` — fingerprint, safe_write_text, utc_now_iso
    - `window_read.py` — ChipGrid, COG window reads, reprojection, write_geotiff
    - `scene_index.py` — scenes_index.json CRUD + cache-skip logic
    - `dedup.py` — pre-download dedup (one best per date/spacecraft)
    - `processor.py` — SceneResult, process_one_scene (thread-safe worker)
    - `pipeline.py` — write_outputs orchestrator
- `farmtrust_core/io/` contains general I/O helpers only; the unused STAC query cache helper was removed.

## Contracts (source of truth)

- JSON Schema in `contracts/schemas/` is authoritative.
- Phase A schemas now exist for `land-create`, `land-result`, and `job-state`.
- Required fields in outputs: schema_version, pipeline_version.
- API validates requests/responses with jsonschema; internal models use Pydantic.
- Portal generates TS types from schemas; generated code is disposable.

## Architecture

- Components: ingest service, preprocessing + quality masking, feature extraction, scoring + rules,
  storage, API for portal, job worker/queue.
- Data flow: land input → imagery fetch → time-series build → smoothing/gap handling → indicators →
  scoring/flags → persisted results → API.
- Persistence: plot geometry, time-series features, scores/flags, reports, job status.

## Data & signals

- Sources: Sentinel-2 is the current implemented source. Broader satellite-source selection, including Landsat and when/why to use each source, remains a future exploration topic.
- Key indicators/metrics: NDVI/EVI peak, AUC, cropping intensity, season timing, within-season
  stability, mid-season shocks, spatial uniformity, NDMI, NDWI/MNDWI, trend vs neighbors.
- Confidence strategy: quality masks + observation count + season clarity; propagate to outputs.
- Phase A indicator set (locked):
    - Coverage (observation quality / cloud gaps)
    - Vegetation trend (2-year trend from NDVI/AUC)
    - Anomalies (mid-season drops / instability)
    - Confidence (quality + gap penalty)
    - Short reasons mapped to each output
    - Smoothed metric evidence charts for NDVI, EVI, NDMI, and NDWI

## Modeling approach (by output)

- Land activity/status (active/intermittent/inactive): rule-based time-series features (NDVI/EVI seasonality, AUC, threshold crossings), with classical ML (RF/XGBoost) on engineered features as labels improve.
- Trend (improving/stable/declining): linear trend on peak NDVI/AUC; Theil-Sen or Mann-Kendall for robust trend estimation under gaps/outliers.
- Season performance (good/interrupted/weak): change-point detection on NDVI curves and rule-based curve-shape classification (rise-peak-fall vs drop/flat).
- Risk flags:
    - Waterlogging: NDWI/MNDWI frequency + spatial persistence.
    - Salinity likelihood: persistent low NDVI patches + bare-soil brightness indices (proxy).
    - Abandonment: long fallow periods + lack of seasonal cycles.
    - Encroachment: persistent non-vegetation + land-use change cues.
    - Start rule-based; transition to ML-assisted scoring when labels are stable.
- Broad crop category (season + water-demand class): deferred beyond the current land assessment contract and revisited only after stronger validation evidence exists.
- Boundary refinement (later): segmentation model (U-Net/DeepLab) trained on public or weak labels to improve small-plot purity.

## Pipeline

- Ingest: current CLI uses bbox/time-window input; intended product input is a user-drawn polygon. The pipeline deduplicates to one best scene per (date, spacecraft) before downloading and uses parallel COG window reads via thread pool (default 4 workers).
  - Local reuse is scene/chip based: STAC is queried each run, then `scenes_index.json` + chip completeness + matching fingerprint determine which scenes can skip download/reprocessing.
  - There is no active STAC query-result cache; the unused TTL/env-var STAC cache helper was removed to avoid stale scene lists and dead-code confusion.
- Preprocess: cloud/shadow masking, compositing, smoothing/de-spiking, optional gap-fill.
  - Current Phase A implementation exports merged daily raw + smoothed values for `ndvi`, `evi`, `ndmi`, and `ndwi` in `ndvi_smoothed.csv`.
  - Preprocessing quality output now also includes explicit gap diagnostics such as `long_gap_count` and `long_gap_windows`.
- Feature extraction: plot-level time series and spatial stats; neighbor comparison window.
- Scoring / classification: conservative rule-based thresholds for land status, trend, season outcome, risks, and assessment confidence.
- Seasonal detection policy (current): NDVI remains the primary detector (threshold crossing + backtracked onset + duration checks). Multi-index confirmation from EVI/NDMI/NDWI is applied as a secondary confidence/label adjustment layer.
- Seasonal output now includes per-season gap-overlap diagnostics so reviewers can see whether a season window intersects one or more long observation gaps.
  - The current overlap diagnostic records both severity and the dominant season stage touched by the gap (`onset`, `peak`, `tail`, or `multiple`).
- Serving: persist results; expose summary and report endpoints for portal.

## Land assessment artifact

- Purpose: produce the internal assessment artifact that summarizes preprocessing and seasonal evidence into lender-facing land status, trend, season performance, risk flags, confidence, and evidence.
- Backend handoff: FastAPI runs or triggers the pipeline, reads `land_assessment.json`, maps it into API response DTOs, and sends those API responses to the portal. The frontend should not receive or depend on the raw file path or file name.
- Input files:
    - `data/<aoi_id>/run_metadata.json`
    - `data/preprocess/<aoi_id>/ndvi_smoothed.csv`
    - `data/preprocess/<aoi_id>/quality_metrics.json`
    - `data/seasonal/<aoi_id>/season_windows.json`
- Output file:
    - `data/assessment/<aoi_id>/land_assessment.json`
- Policy notes:
    - `land_status` must be inferred from interval-level behavior across seasons and low-activity spans, not from one latest point.
    - `trend_2y` is derived from season-level strength summaries such as peak NDVI and seasonal activity area.
    - `latest_season_performance` uses the latest closed season when available; otherwise it uses the latest open season and marks it provisional.
    - Risk flags stay conservative and should prefer `uncertain` or lower confidence when continuity or season clarity is weak.
    - Assessment outputs should surface explicit gap diagnostics, not only a single `gap_risk` label.
    - Assessment confidence now exposes component levels for continuity, season clarity, and signal strength in addition to the final level.
    - Phase A skips crop category output.

## Model evolution plan (collapsed phases)

Phase A — MVP Core

- Land status: rule-based features from NDVI/EVI time series.
- Trend: linear/robust trend tests on peak NDVI/AUC.
- Season performance: curve-shape rules + change-point detection.
- Risk flags: rule-based NDWI/NDMI + persistence checks.

Phase B — Hardening + credit layer

- Replace some rules with classical ML (RF/XGBoost) on engineered features.
- Calibrate thresholds by region (Delta/Valley/Reclaimed).
- Add confidence models (probability calibration + uncertainty bands).
- Introduce credit readiness layer (risk tiers) as an aggregation of indicators.
- Revisit broad crop category only if validation evidence and trust requirements are met.

Phase C — Expansion + advanced modeling

- Boundary refinement: segmentation model (U-Net/DeepLab) trained on weak labels + small manual set.
- Encroachment detection: land-use change model with multi-year change maps.
- Crop taxonomy with weak labels + domain adaptation.
- Add water-demand class + season length class.
- Yield potential bands using multi-year productivity proxies + regional calibration.
- Multimodal fusion (optical + SAR + thermal).
- Self-supervised pretraining on regional time series.
- Teacher-student distillation for Egypt-specific models.

## Teacher-student distillation (high-level)

- Collect global datasets (crop maps, land-use, time-series) and remove non-Egypt patterns.
- Train a large teacher model for generalized crop/behavior signals.
- Generate high-confidence pseudo-labels for Egypt.
- Train a smaller Egypt-specific student model (distillation).
- Use student outputs to improve accuracy and build higher-quality local datasets.

## Credit readiness layer (aggregation)

- Purpose: aggregate indicators into a lender-facing risk tier (low/medium/high) before a numeric score.
- Inputs: land status, trend, season performance, risk flags, confidence, neighbor comparison, irrigation stability.
- Approach: start as weighted rules; transition to ML when outcome labels are available.
- Note: this is decision support, not an automated financing decision.

## R&D exploration note

- The model evolution plan and distillation work are exploratory and may change as evidence accumulates.

## Interfaces

- Inputs: intended product input is polygon geometry drawn on a map; current Phase A CLI uses bbox/config input. Assessment window target is 24 months.
- Outputs (high-level schema): land_status, trend_2y, season_performance, flags[], confidence,
  indicators{...}, report_summary, evidence{...}, report_pdf_payload.
- File-based land assessment output: `land_assessment.json` with interval summary, season summary, risk flags, and metric evidence summaries. FastAPI reads this internal artifact and returns shaped API responses to the portal.
- Versioning notes: version indicators/thresholds to keep reports stable over time.
- API endpoints (Phase A):
    - GET /health
    - GET /jobs/{id}
    - GET /jobs/{id}/logs
    - POST /lands
    - GET /lands/{id}
    - GET /lands/{id}/report
- Job states: queued -> running -> succeeded/failed
- Job phases: fetching, processing, scoring, rendering

## Ops & scaling

- Jobs/queue: Phase A uses a direct worker execution path (single-job flow). Queue/broker integration is deferred to Phase B.
- Retries and failures: simple status update to failed/succeeded; no multi-user reliability guarantees in Phase A.
- Retries: bounded retries with backoff and alert on repeated failures.
- Monitoring: job success rate, data availability, anomaly rates, latency.
- Performance: cache intermediate composites; batch neighbor comparisons.
- Demo entry point (Phase A): scripts-driven (make demo or scripts/demo.ps1), no Docker requirement.

## Dev workflow (Phase A)

- Environment manager: `uv` with a single repo-level `.venv`.
- Dependency model:
    - Main deps: minimal shared runtime (`farmtrust_core`-level needs).
    - Extra `data`: ingestion/geospatial dependencies.
    - Extra `ml`: reserved placeholder for later ML framework selection (empty in Phase A).
    - Dev group: local analysis and developer tooling.
- Role setup:
    - Core/API work: `uv sync`
    - Ingestion/geospatial work: `uv sync --extra data`
    - Team reproducibility install: `uv sync --frozen --extra data`
- Scripts in `scripts/` import pipeline logic from `farmtrust_core`.
- Standard ingestion command: `uv run ingest-aoi --config scripts/ingest_demo.json`.
- Integration path: portal -> API -> worker, used for demo validation.

## Phase scope notes

- Phase A: minimal persistence only; no cross-run comparability requirements.
- Phase B: add schema governance, QA gates, metadata/versioning, and reproducibility discipline.
- Phase B: introduce queue/broker for multi-user concurrency and reliability.

## Technical risks

- [risk] Boundary accuracy and mixed pixels distort plot-level indicators.
- [risk] Cloud gaps create artificial trend shifts if not handled well.
- [risk] Local environmental variance reduces generalization across regions.
- [risk] False alerts undermine trust; thresholds must be conservative.
- [risk] Scaling costs for large plot counts and repeated time-series updates.
- [risk] Evidence language may be too technical for lender adoption.
