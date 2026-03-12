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
    - worker/ (Python)
    - farmtrust_core/ (core pipeline package)
    - portal/ (Next.js)
    - contracts/ (schemas)
    - infra/ (scripts/CI)
    - docs/ (Aha!Kit truth)
- `farmtrust_core/` is the single importable top-level Python package for core pipeline logic reused by worker and API services.

## Contracts (source of truth)

- JSON Schema in `contracts/schemas/` is authoritative.
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

- Sources: Sentinel-2 (primary) with Landsat fallback for gap coverage.
- Key indicators/metrics: NDVI/EVI peak, AUC, cropping intensity, season timing, within-season
  stability, mid-season shocks, spatial uniformity, NDMI, NDWI/MNDWI, trend vs neighbors.
- Confidence strategy: quality masks + observation count + season clarity; propagate to outputs.
- Phase A indicator set (locked):
    - Coverage (observation quality / cloud gaps)
    - Vegetation trend (2-year trend from NDVI/AUC)
    - Anomalies (mid-season drops / instability)
    - Confidence (quality + gap penalty)
    - Short reasons mapped to each output

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
- Broad crop category (season + water-demand class): heuristic classification using timing + NDVI/NDMI curves; weakly supervised RF/XGBoost from public datasets when feasible.
- Boundary refinement (later): segmentation model (U-Net/DeepLab) trained on public or weak labels to improve small-plot purity.

## Pipeline

- Ingest: fetch imagery for polygon/time window; validate geometry.
- Preprocess: cloud/shadow masking, compositing, smoothing/de-spiking, optional gap-fill.
- Feature extraction: plot-level time series and spatial stats; neighbor comparison window.
- Scoring / classification: conservative rule-based thresholds for land status, trend, season outcome, risks.
- Serving: persist results; expose summary and report endpoints for portal.

## Model evolution plan (collapsed phases)

Phase A — MVP Core

- Land status: rule-based features from NDVI/EVI time series.
- Trend: linear/robust trend tests on peak NDVI/AUC.
- Season performance: curve-shape rules + change-point detection.
- Risk flags: rule-based NDWI/NDMI + persistence checks.
- Crop category: heuristic + weakly supervised RF/XGBoost if possible.

Phase B — Hardening + credit layer

- Replace some rules with classical ML (RF/XGBoost) on engineered features.
- Calibrate thresholds by region (Delta/Valley/Reclaimed).
- Add confidence models (probability calibration + uncertainty bands).
- Introduce credit readiness layer (risk tiers) as an aggregation of indicators.

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

- Inputs: polygon geometry or point+area; time window (default 24 months).
- Outputs (high-level schema): land_status, trend_2y, season_performance, flags[], confidence,
  indicators{...}, report_summary, evidence{...}, report_pdf_payload.
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
    - Dev group: notebook + local tooling.
- Role setup:
    - Core/API work: `uv sync`
    - Ingestion/geospatial work: `uv sync --extra data`
    - Team reproducibility install: `uv sync --frozen --extra data`
- Worker scripts and services import pipeline logic from `farmtrust_core`.
- Standard ingestion command: `uv run ingest-aoi --config worker/scripts/ingest_demo.json`.
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
