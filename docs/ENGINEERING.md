# ENGINEERING

Purpose: single place for engineering truth (architecture, stack, interfaces, ops, technical risks).
Detailed pipeline runbook content lives in `PIPELINE.md`.

## Links

- DECISIONS entry: <YYYY-MM-DD — Decision: ...>
- PROJECT section: <PROJECT §...>
- Pipeline reference: `PIPELINE.md`
- TASK: <T-xx — name>

## System overview

- Satellite time-series pipeline producing plot-level indicators, assessment confidence, satellite evidence coverage, and land risk flags.
- Outputs stored for fast portal rendering and report export.

## MVP stack

- Data access: Sentinel-2 via cloud STAC, currently Planetary Computer.
- Processing: Python (xarray, rasterio, pystac-client) for time-series features.
- API: FastAPI for job submission, results, job status, and mapped report DTOs.
- Storage: SQLite for current-build lands/jobs plus local file artifacts under `data/`.
- Portal: React/Next.js with Leaflet for AOI input and summaries.
- Jobs: FastAPI background worker using a direct single-job path.

## Repo structure (current build)

- `api/`: FastAPI service for lands, jobs, health, and report endpoints.
- `farmtrust_core/`: single importable Python package for core pipeline logic reused by workers and scripts.
- `scripts/`: CLI entrypoints for local/demo pipeline validation.
- `portal/`: Next.js portal for AOI input, summaries, evidence, and report export.
- `contracts/`: shared request/response schemas and generated client types.
- `docs/`: documentation truth.
- Pipeline stage implementation lives under `farmtrust_core/ingest/`, `farmtrust_core/preprocess/`, `farmtrust_core/seasonal/`, and `farmtrust_core/scoring/`; exact commands, artifacts, fields, and thresholds belong in `PIPELINE.md`.

## Contracts (source of truth)

- JSON Schema in `contracts/schemas/` is authoritative.
- Current-build schemas now exist for `land-create`, `land-result`, and `job-state`.
- Required fields in outputs: schema_version, pipeline_version.
- API validates requests/responses with jsonschema; internal models use Pydantic.
- Portal generates TS types from schemas; generated code is disposable.

## Architecture

- Components: ingest service, preprocessing + quality masking, feature extraction, scoring + rules,
  storage, API for portal, and direct job worker.
- Data flow: land input → imagery fetch → time-series build → smoothing/gap handling → indicators →
  scoring/flags → persisted results → API.
- Persistence: plot geometry and job status in SQLite; time-series features, scores, flags, and assessment artifacts in local files.

### Current-build backend flow

```text
Browser
  |
  v
Next.js Portal (port 3000)
  |
  |  GET  /api/lands      -> mock fixture lands + live lands from FastAPI
  |  POST /api/lands      -> forward new real submissions to FastAPI
  |  GET  /api/lands/{id} -> mock ID returns fixture; real ID proxies FastAPI
  |  GET  /api/jobs/{id}  -> mock job returns fixture; real ID proxies FastAPI
  v
FastAPI (port 8000)
  |
  |-- POST /lands              -> store land in SQLite and launch background job
  |-- GET  /lands              -> list real lands from SQLite
  |-- GET  /lands/{id}         -> read land + assessment result
  |-- GET  /lands/{id}/report  -> serve mapped assessment DTO
  |-- GET  /jobs/{id}          -> poll job status and logs
  |-- GET  /jobs/{id}/logs
  `-- GET  /health
       |
       `-- Background worker thread
             |
             |-- 1. Ingest      -> farmtrust_core/ingest (GeoJSON polygon)
             |-- 2. Preprocess  -> farmtrust_core/preprocess
             |-- 3. Seasonal    -> farmtrust_core/seasonal
             `-- 4. Score       -> farmtrust_core/scoring
                                   -> data/assessment/<aoi_id>/land_assessment.json
                                   -> FastAPI maps artifact to portal DTO
```

## Data & signals

- Sources: Sentinel-2 is the current implemented source. Broader satellite-source strategy, including Landsat and when/why to use each source, remains unresolved and is tracked in `OPEN_ITEMS.md`.
- Key indicators/metrics: NDVI/EVI peak, AUC, season timing, within-season stability, mid-season shocks, spatial uniformity, NDMI, and NDWI/MNDWI.
- Assessment confidence strategy: quality masks + observation count + season clarity; propagate as confidence in the assessment, not confidence in the land itself.
- Current-build indicator set (locked):
    - Coverage (observation quality / cloud gaps)
    - Vegetation trend (2-year trend from NDVI/AUC)
    - Anomalies (mid-season drops / instability)
    - Assessment confidence (quality + observation continuity impact)
    - Short reasons mapped to each output
    - Smoothed metric evidence charts for NDVI, EVI, NDMI, and NDWI

## Modeling approach (by output)

- Land activity/status (active/intermittent/inactive): rule-based time-series features from NDVI/EVI seasonality, AUC, and threshold crossings.
- Trend (improving/stable/declining): conservative comparison of season-level strength summaries such as peak NDVI and season AUC.
- Season performance (good/interrupted/weak): change-point detection on NDVI curves and rule-based curve-shape classification (rise-peak-fall vs drop/flat).
- Risk flags:
    - Waterlogging: NDWI/MNDWI frequency + spatial persistence.
    - Salinity likelihood: persistent low NDVI patches + bare-soil brightness indices (proxy).
    - Abandonment: long fallow periods + lack of seasonal cycles.
    - Encroachment: persistent non-vegetation + land-use change cues.
    - Current build uses conservative rule-based scoring.
- Crop category is not part of the current land assessment contract.

## Pipeline boundary

- Current pipeline stages: ingest -> preprocess -> seasonal analysis -> score.
- Product/API input is user-drawn polygon geometry; local/demo CLI fixtures may use bbox/config input for repeatable validation.
- Stage handoffs remain file-based in the current build so each stage can be validated independently.
- FastAPI runs or triggers the pipeline, reads the internal assessment artifact, maps it into API DTOs, and sends shaped responses to the portal.
- Architecture commitments: Sentinel-2 current source, explicit gap diagnostics, no interpolation or synthetic timestamps, conservative rule-based scoring, NDVI-primary seasonal detection with EVI/NDMI/NDWI confirmation.
- Local scene/chip reuse is supported to reduce repeated raster work; exact reuse rules belong in `PIPELINE.md`.
- Detailed commands, runtime artifacts, field contracts, thresholds, and detector behavior belong in `PIPELINE.md`.

## Assessment artifact boundary

- `land_assessment.json` is an internal pipeline artifact, not a frontend contract.
- The artifact summarizes preprocessing and seasonal evidence into lender-facing land status, trend, season performance, land risk flags, satellite evidence coverage, assessment confidence, and evidence.
- Assessment logic must remain interval-based, evidence-preserving, conservative under weak continuity, and explicit that gap diagnostics are evidence limitations rather than land/farmer problems.
- FastAPI maps the artifact into versioned API response DTOs for the portal and report endpoints.

## Exploration boundary

- Non-committed model, credit, crop, yield, and expansion ideas are parked in `FUTURE.md`; they are not architecture truth until promoted by decision.

## Interfaces

- Inputs: intended product input is polygon geometry drawn on a map; current CLI uses bbox/config input. Assessment window target is 24 months.
- Outputs (high-level schema): land_status, trend_2y, season_performance, flags[], satellite_evidence_coverage, assessment_confidence, indicators{...}, report_summary, evidence{...}, report_pdf_payload.
- File-based land assessment output: `land_assessment.json` with interval summary, season summary, risk flags, and metric evidence summaries. FastAPI reads this internal artifact and returns shaped API responses to the portal.
- Versioning notes: version indicators/thresholds to keep reports stable over time.
- API endpoints (current build):
    - GET /health
    - GET /jobs/{id}
    - GET /jobs/{id}/logs
    - POST /lands
    - GET /lands/{id}
    - GET /lands/{id}/report
- Job states: queued -> running -> succeeded/failed
- Job stage values: fetching, processing, scoring, rendering

## Ops & scaling

- Jobs/queue: The current build uses a direct worker execution path (single-job flow). Queue/broker integration is deferred until multi-user reliability is needed.
- Retries and failures: simple status update to failed/succeeded; no multi-user reliability guarantees in the current build.
- Monitoring: job success rate, data availability, anomaly rates, latency.
- Performance: reuse local scene/chip outputs and cache intermediate artifacts where current code supports it.
- Demo entry point (current build): scripts-driven (make demo or scripts/demo.ps1), no Docker requirement.

## Dev workflow (current build)

- Environment manager: `uv` with a single repo-level `.venv`.
- Dependency model:
    - Main deps: minimal shared runtime (`farmtrust_core`-level needs).
    - Extra `data`: ingestion/geospatial dependencies.
    - Extra `ml`: reserved placeholder for later ML framework selection (empty in the current build).
    - Dev group: local analysis and developer tooling.
- Role setup:
    - Core/API work: `uv sync`
    - Ingestion/geospatial work: `uv sync --extra data`
    - Team reproducibility install: `uv sync --frozen --extra data`
- Scripts in `scripts/` import pipeline logic from `farmtrust_core`; local validation commands are documented in `PIPELINE.md`.
- Integration path: portal -> API -> worker, used for demo validation.

## Scope notes

- Current Build: minimal persistence only; no cross-run comparability requirements.
- Non-current technical ideas are parked in `FUTURE.md` and must be re-evaluated before becoming architecture or a live task.

## Technical risks

- [risk] Boundary accuracy and mixed pixels distort plot-level indicators.
- [risk] Cloud gaps create artificial trend shifts if not handled well.
- [risk] Local environmental variance reduces generalization across regions.
- [risk] False alerts undermine trust; thresholds must be conservative.
- [risk] Scaling costs for large plot counts and repeated time-series updates.
- [risk] Evidence language may be too technical for lender adoption.
