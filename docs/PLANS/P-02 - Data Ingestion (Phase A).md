# Data Ingestion — Phase A Workstream

## Links

- PROJECT: `PROJECT §Phase A ownership`
- ENGINEERING: `ENGINEERING §Architecture`, `§Data & signals`, `§Pipeline`

---

## Ownership & Boundaries

**Owner:** Data Ingestion

**Upstream dependencies:** None (fixtures used for Phase A)  
**Downstream consumers:** ML / Time-Series Preprocessing

---

## Role Summary

The Data Ingestion role in Phase A is responsible for making satellite data reliably available for downstream analysis. Given an Area of Interest (AOI), the ingestion pipeline fetches satellite imagery and produces raw index time-series covering the last 24 months.

The focus in Phase A is **data availability, correctness, and reproducibility**, not modeling sophistication. The output of this role is clean, well-defined time-series data that downstream ML roles can build on without needing to understand satellite access details.

Because the portal and API are not yet implemented, ingestion is validated end-to-end using **fixture AOIs** (sample polygons and point+area inputs). Once the full ingestion loop is stable, replacing fixtures with real AOIs should require only interface wiring, not architectural changes.

---

## Scope of Work

### In Scope

#### Satellite Access
- Primary source: **Sentinel-2** via STAC  
- Endpoint: Planetary Computer (Azure)
- Fallback source: **Landsat** (only when Sentinel-2 coverage is insufficient)

#### AOI Handling
- Supported AOI inputs:
  - Polygon geometries
  - Point + area (converted to polygon)
- Geometry validation and normalization

#### Time-Series Extraction
- Indices produced:
  - NDVI
  - EVI
  - NDMI
  - NDWI
  - MNDWI
- Temporal window:
  - Last **24 months**
- Output granularity:
  - Per-scene timestamps

#### Minimal Persistence
- Local persistence for Phase A development:
  - Index time-series per AOI
  - Minimal extraction metadata

#### Development Acceleration
- Local caching of STAC query results
- Cached outputs allow fast iteration without repeated remote calls

---

## Explicit Non-Goals

- Gap handling, smoothing, or interpolation
- Feature engineering beyond raw index computation
- Scoring, classification, or decision logic
- API or portal integration

---

## Expected Outcomes

1. Valid AOIs produce raw index time-series covering the last 24 months.
2. Results are persisted locally and retrievable.
3. The pipeline is reproducible using the shared UV environment.
4. Downstream ML work can run on cached data during development.

---

## Phase A Data Flow

1. **AOI Intake**  
   Validate or convert AOI → normalize geometry

2. **Imagery Query**  
   Sentinel-2 STAC query → Landsat fallback if needed

3. **Index Computation**  
   NDVI, EVI, NDMI, NDWI, MNDWI per timestamp

4. **Persistence**  
   AOI metadata + time-series + extraction metadata

5. **Caching**  
   STAC responses and intermediate outputs cached locally

---

## R&D Approach

- Exploration notebooks for STAC, AOI edge cases, and index validation
- Time-boxed research spikes (3–5 days)
- Promote stable approaches into ingestion modules
- Keep notebooks as evidence, not production

---

## Milestones

### Milestone 1 — Environment & Access
- UV environment and lockfile
- Proven Sentinel-2 STAC access
- STAC exploration notebook

### Milestone 2 — Index Extraction
- Working extraction for all indices
- Consistent timestamped outputs

### Milestone 3 — Minimal Persistence
- Local persistence verified

### Milestone 4 — Handoff Readiness
- Cached sample data
- Run instructions
- ML handoff notes

---

## Definition of Done

- UV environment committed (`uv.lock`)
- Exploration notebooks present and labeled
- AOI validation implemented
- Raw 24-month index series produced
- Persistence verified
- Cached dev path documented
- ML handoff documentation completed

---

## Consolidated implementation snapshot (Phase A)

This section is the canonical merged view of ingestion implementation details previously split across `docs/NOTES/`.

### Implemented behavior

- AOI handling
  - Polygon GeoJSON and point+area inputs are supported.
  - Geometry is normalized before use.
- STAC ingestion
  - Sentinel-2 L2A is primary.
  - Multiple STAC endpoints are supported.
  - Optional cloud-cover pre-filtering is supported.
  - Landsat fallback is used only when Sentinel-2 returns empty for AOI/window.
  - STAC query cache is enabled by default with TTL.
- Index schema contract
  - Time-series columns are fixed: `timestamp`, `source`, `ndvi`, `evi`, `ndmi`, `ndwi`, `mndwi`.
  - Scene cadence is per-item timestamp (irregular), not fixed intervals.
  - Fixed-interval (for example monthly) views are allowed as downstream/derived outputs.
  - Missing values remain null/NaN by design for downstream gap handling.
- Local persistence
  - STAC cache: `.cache/ingestion/stac/*.json`
  - AOI outputs: written to `--output-dir` (default `data/<aoi_id>/`)
  - Scene index: `<output-dir>/scenes_index.json`

### Current code inventory

- `farmtrust_core/ingest/stac_client.py`: reusable STAC search with endpoint fallback and soft Planetary Computer signing.
- `farmtrust_core/io/cache.py`: TTL-based STAC query cache with env var controls (`STAC_CACHE_DISABLE`, `STAC_CACHE_TTL_HOURS`).
- `farmtrust_core/ingest/indices.py`: index computation (NDVI, EVI, NDMI, NDWI, MNDWI).
- `farmtrust_core/ingest/utils.py`: shared helpers (`utc_now_iso`, `compute_fingerprint`, `safe_write_text`).
- `scripts/ingest_aoi.py`: end-to-end ingestion entry point (scene download, index extraction, output writing).

### End-to-end runbook (merged)

- Environment model: single project environment at repo root (`uv` + `.venv`).
- Setup from repo root:

```powershell
uv sync --extra data
```

- Run ingestion for an AOI:

```powershell
uv run ingest-aoi --config scripts/ingest_demo.json
```

- Persisted outputs:
  - `.cache/ingestion/stac/*.json` (STAC query cache)
  - `data/<aoi_id>/indices_timeseries.csv`
  - `data/<aoi_id>/scenes_index.json`
  - `data/<aoi_id>/chips/<item_id>/` (GeoTIFF bands)
- Cache controls:
  - Default TTL: `72` hours
  - Disable cache: `STAC_CACHE_DISABLE=1`
  - Override TTL: `STAC_CACHE_TTL_HOURS=<int>`

### ML handoff contract (merged)

- Time window:
  - Default lookback is last `24` months (UTC).
  - Metadata includes `window` and `lookback_months`.
- Output schema (per AOI hash parquet):
  - `timestamp` (ISO-8601 UTC from STAC properties)
  - `source` (`sentinel-2` or `landsat`)
  - `ndvi`, `evi`, `ndmi`, `ndwi`, `mndwi` (float; may be null before full raster extraction wiring)
- Timestamp semantics:
  - One row per scene timestamp in Phase A.
  - Fixed-interval series belongs to downstream preprocessing (resampling + gap rules).
- Missing data behavior:
  - Columns remain present; missing values are null/NaN.
  - Downstream stages must use observation-count and gap metrics; do not assume contiguous sampling.
- Coverage notes:
  - Metadata `coverage_notes` explains gaps/fallbacks.
  - Source selection remains Sentinel-2 primary, Landsat fallback on empty Sentinel-2 query.

### Teammate adoption guide (merged)

- Notebooks to inspect in order:
  1. `notebooks/ingest_stac_quickstart.ipynb`
  2. `notebooks/ingest_aoi_handling.ipynb`
  3. `notebooks/ingest_index_verification.ipynb`
  4. `notebooks/ingest_persistence_smoke.ipynb`
- Use notebooks for behavior understanding and evidence, not as production code.
- Use cached outputs for local experimentation and downstream contract checks.
- Keep ingestion outputs as Phase A source of truth for raw satellite signals.

### Intentionally missing in Phase A (merged)

- No gap filling or smoothing
- No monthly resampling as canonical output
- No scoring or classification
- No API endpoints
- No database-backed persistence

### Module ownership (resolved)

- Reusable ingestion logic lives in `farmtrust_core/` (stac_client, io/cache, indices, utils).
- `scripts/ingest_aoi.py` is the entry point — it imports from `farmtrust_core`, not the reverse.
- `worker/` has been removed. There is no separate worker layer.
