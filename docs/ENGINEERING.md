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

## Current-build stack

- Data access: Sentinel-2 via cloud STAC, currently Planetary Computer.
- Processing: Python (xarray, odc-stac, dask, rasterio, pystac-client) for time-series features. Ingestion uses odc.stac.load for solar-day cube mosaics; rasterio is a transitive raster dependency (AOI rasterization, warp), not a separate ingestion path.
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

- Land activity/status (active/intermittent/inactive): rule-based time-series features from adaptive vegetation activity windows, activity coverage, and season-level strength summaries.
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
- Architecture commitments: Sentinel-2 current source, explicit gap diagnostics, linear interpolation across usable anchors for the analysis curve followed by Savitzky-Golay smoothing (no synthetic timestamps), conservative rule-based scoring, and hybrid-threshold activity-window detection (fixed floor + dynamic baseline margin) with EVI/NDMI/NDWI as supporting evidence.
- **Ingestion architecture:** odc.stac.load cube path, the single ingestion path, run in two phases. **Download** searches STAC, mosaics each solar day across overlapping tiles, and region-writes raw-DN pixels into `cube.zarr`; fresh cubes start on a sorted time axis, while existing cubes append newly discovered days without re-downloading old chunks, then compact the local Zarr store back into physical time order. **Process** opens the cube, applies the AOI polygon + SCL validity masks and the BOA offset (DN-1000)/10000, computes per-day statistics, and emits sorted `indices_timeseries.csv` rows (one row = one solar-day mosaic). `cube.zarr` is the primary, self-describing source artifact (raw pixels + provenance + config in root attrs); derived stats live in `indices_timeseries.csv`, not in the cube. Root `cube.zarr` stores the 10m grid/provenance/time; native 20m source bands (`B05`, `B06`, `B07`, `B8A`, `B11`, `B12`, `SCL`) are stored in a `20m` Zarr group and are aligned temporarily in memory for derived statistics. `scenes_index.jsonl` (v4+) is an operational ledger of per-day and per-band download status and is authoritative about which days/bands are real; `run_metadata.json` carries run config and is Phase 2's config read-path. Separating download from process lets a policy change (offset, SCL classes, new index) reprocess without re-downloading. Cache is keyed per solar day, while band repair/backfill is keyed per missing band; adding dates or repairing bands does not re-download existing bands.
- Callers (API worker, CLI) depend on the loader-agnostic seam `farmtrust_core.ingest.runner.run_ingestion` and catch `IngestCancelled`; they never import a concrete loader. Swapping or adding an ingestion implementation changes only the runner's dispatch table.
- The legacy rasterio per-scene path (`pipeline.py`, `processor.py`, `window_read.py`, `dedup.py`, `scene_index.py`) was removed once the cube path passed equivalence and the full preprocess→seasonal→scoring chain ran on cube output.
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
- Performance: reuse local `cube.zarr` source bands and cache intermediate artifacts where current code supports it.
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
