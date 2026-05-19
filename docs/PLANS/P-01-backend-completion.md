# P-01 — Backend Completion (Phase A)

## Links

- PROJECT: `PROJECT §MVP scope`, `PROJECT §Roadmap`
- ENGINEERING: `ENGINEERING §Architecture`, `ENGINEERING §API endpoints (Phase A)`, `ENGINEERING §Land assessment artifact`
- DECISIONS: `2026-05-18 — Direct worker flow for Phase A`

---

## Architecture

### What exists today vs what's needed

| Layer | Status |
|---|---|
| `farmtrust_core/` pipeline (CLI) | **Complete** |
| `portal/` Next.js UI + mock routes | **Complete (mocked)** |
| `api/` FastAPI backend | **Does not exist** |
| Portal ↔ API integration | **Not connected** |
| Polygon support in pipeline | **Missing** (bbox only) |
| Contracts / JSON schemas | **Empty** |

---

### High-Level Architecture

```
Browser
  │
  ▼
Next.js Portal (port 3000)
  │
  │  GET  /api/lands      → MOCK_LANDS (static demo fixtures)
  │                         + fetch real lands from FastAPI → merged list
  │
  │  POST /api/lands      → forward directly to FastAPI (new real submission)
  │
  │  GET  /api/lands/[id] → mock ID?  return MOCK_LANDS entry
  │                         real ID?  proxy to FastAPI
  │
  │  GET  /api/jobs/[id]  → mock job ID?  return getMockJob()
  │                         real job ID?  proxy to FastAPI
  │
  ▼  (server-to-server, no auth)
FastAPI (port 8000)
  │
  ├── POST /lands         → store land record in SQLite → launch background job
  ├── GET  /lands         → list real lands from SQLite only
  ├── GET  /lands/{id}    → read land + assessment result from SQLite/file
  ├── GET  /lands/{id}/report  → serve land_assessment.json content as DTO
  ├── GET  /jobs/{id}     → poll job status + logs from SQLite
  ├── GET  /jobs/{id}/logs
  └── GET  /health
       │
       └── Background Thread (one per job)
             │
             ├── 1. Ingest      → farmtrust_core/ingest  (GeoJSON Polygon)
             ├── 2. Preprocess  → farmtrust_core/preprocess
             ├── 3. Seasonal    → farmtrust_core/seasonal
             └── 4. Score       → farmtrust_core/scoring
                                ↓
                           data/<aoi_id>/assessment/land_assessment.json
                                ↓
                           FastAPI reads → returns DTO to portal
```

---

### Implementation Work Breakdown

#### 1. Extend `farmtrust_core/ingest` — Polygon support
**Files:** `ingest/config.py`, `ingest/pipeline.py` (or new `ingest/polygon.py`)

- Accept `geometry: dict` (GeoJSON Polygon) alongside or instead of `bbox`
- Compute chip bbox from polygon exterior ring
- Apply polygon mask when reading COG windows (clip to polygon boundary for accurate plot-level stats)
- Update `ingest_aoi.py` CLI script to accept `--geometry` flag

#### 2. Implement `farmtrust_core/io/paths.py`
**File:** `farmtrust_core/io/paths.py` (currently empty stub)

- Central path helper: `aoi_dir()`, `assessment_dir()`, `timeseries_path()`, etc.
- Used by all pipeline stages and by the FastAPI worker

#### 3. Build `api/` — FastAPI backend
**New directory:** `api/`

```
api/
├── main.py             # FastAPI app, CORS, lifespan
├── database.py         # SQLite setup (SQLModel / SQLAlchemy)
├── models.py           # ORM: Land, Job tables
├── schemas.py          # Pydantic DTOs (request/response)
├── routers/
│   ├── lands.py        # POST /lands, GET /lands, GET /lands/{id}, GET /lands/{id}/report
│   └── jobs.py         # GET /jobs/{id}, GET /jobs/{id}/logs
├── worker.py           # Background thread runner — calls farmtrust_core stages in sequence
└── assessment_mapper.py # Maps land_assessment.json → LandResult DTO
```

**SQLite tables (2):**

```
Land
  id            TEXT PK (uuid)
  name          TEXT
  governorate   TEXT
  geometry      TEXT (GeoJSON stored as string)
  area_feddan   REAL
  aoi_id        TEXT (= id, used as folder name)
  job_id        TEXT FK
  land_status   TEXT nullable
  trend_2y      TEXT nullable
  created_at    DATETIME

Job
  id            TEXT PK (uuid)
  land_id       TEXT FK
  status        TEXT (queued/running/succeeded/failed)
  phase         TEXT (fetching/processing/scoring/rendering)
  logs          TEXT (newline-joined log entries)
  error         TEXT nullable
  created_at    DATETIME
  updated_at    DATETIME
```

**Worker flow (background thread):**

```python
def run_job(job_id, land_id, geometry, aoi_id):
    update_job(job_id, status="running", phase="fetching")
    ingest(aoi_id, polygon=geometry)          # stage 1

    update_job(job_id, phase="processing")
    preprocess(aoi_id)                        # stage 2
    seasonal_analysis(aoi_id)                # stage 3

    update_job(job_id, phase="scoring")
    land_assessment(aoi_id)                  # stage 4

    update_job(job_id, status="succeeded", phase="rendering")
    # write key fields back to Land row from land_assessment.json
```

#### 4. Smart-routing Next.js API routes
**Files:** `portal/src/app/api/lands/route.ts`, `portal/src/app/api/lands/[id]/route.ts`, `portal/src/app/api/jobs/[id]/route.ts`

Mock data is **permanent demo content** — it stays in the portal forever to demonstrate states and functionality. No flag, no modes.

- `GET /api/lands` → return `MOCK_LANDS` merged with live lands fetched from FastAPI (`GET http://localhost:8000/lands`). If FastAPI is unreachable, only mock lands are shown.
- `POST /api/lands` → forward body directly to FastAPI; return FastAPI response.
- `GET /api/lands/[id]` → if `id` matches a mock entry, return it immediately. Otherwise proxy to FastAPI.
- `GET /api/jobs/[id]` → if `id` matches a mock job, return it immediately. Otherwise proxy to FastAPI.

FastAPI URL lives in `portal/.env.local` as `FASTAPI_URL=http://localhost:8000` (required for real submissions to work; mock data always works regardless).

#### 5. Write JSON Schema contracts
**Directory:** `contracts/schemas/`

- `land-create.json` — POST /lands request body
- `land-result.json` — GET /lands/{id} response
- `job-state.json` — GET /jobs/{id} response

---

### File Change Summary

| File | Action |
|---|---|
| `farmtrust_core/io/paths.py` | Fill stub with path helpers |
| `farmtrust_core/ingest/config.py` | Add polygon input support |
| `farmtrust_core/ingest/pipeline.py` | Wire polygon → chip bbox |
| `scripts/ingest_aoi.py` | Add `--geometry` CLI flag |
| `api/main.py` | Create FastAPI app |
| `api/database.py` | SQLite setup |
| `api/models.py` | Land + Job ORM models |
| `api/schemas.py` | Pydantic DTOs |
| `api/routers/lands.py` | Land endpoints |
| `api/routers/jobs.py` | Job endpoints |
| `api/worker.py` | Background pipeline runner |
| `api/assessment_mapper.py` | `land_assessment.json` → DTO |
| `portal/src/app/api/lands/route.ts` | GET: merge mock + real; POST: forward to FastAPI |
| `portal/src/app/api/lands/[id]/route.ts` | Mock ID → mock; real ID → proxy FastAPI |
| `portal/src/app/api/jobs/[id]/route.ts` | Mock job ID → mock; real job ID → proxy FastAPI |
| `portal/.env.local` | Add `FASTAPI_URL=http://localhost:8000` |
| `pyproject.toml` | Add `fastapi`, `uvicorn`, `sqlmodel` deps |
| `contracts/schemas/*.json` | Write 3 JSON Schema files |

---

### Dependencies to add

```toml
# pyproject.toml
fastapi>=0.115
uvicorn[standard]>=0.30
sqlmodel>=0.0.21      # SQLAlchemy + Pydantic in one
shapely               # already in data extras, needed for polygon bbox
```

---

### Out of scope (Phase A)

- No Celery / Redis queue
- No Postgres / PostGIS
- No PDF report endpoint (remains client-side)
- No email sharing
- No role-based authorization
- No neighbor comparison computation

---

## Build Plan

### Milestone 1 — Pipeline polygon support + path helpers

- [x] Fill `farmtrust_core/io/paths.py` with `aoi_dir()`, `assessment_dir()`, `timeseries_path()`, `quality_metrics_path()`, `season_windows_path()`, `land_assessment_path()`
- [x] Add polygon → bbox conversion in `farmtrust_core/ingest/config.py`
- [x] Accept `geometry` (GeoJSON Polygon dict) in pipeline entry point alongside bbox
- [x] Apply polygon mask in COG window reads (`window_read.py`) so stats are clipped to drawn boundary
- [x] Update `scripts/ingest_aoi.py` CLI to accept `--geometry` as alternative to bbox in config
- [ ] Smoke-test polygon input on `aoi_demo_01` bbox converted from polygon

**Acceptance:** `uv run ingest-aoi` with a polygon geometry config produces the same output structure as today

---

### Milestone 2 — FastAPI backend

- [x] Add `fastapi[standard]`, `uvicorn[standard]`, `sqlmodel` to `pyproject.toml`
- [x] `api/database.py` — SQLite engine, session factory, `create_all()`
- [x] `api/models.py` — `Land` and `Job` SQLModel table classes
- [x] `api/schemas.py` — `CreateLandPayload`, `LandResponse`, `JobResponse`, `JobLogsResponse` Pydantic models
- [x] `api/assessment_mapper.py` — reads `land_assessment.json`, maps to `LandResponse` fields
- [x] `api/worker.py` — background thread: run all 4 pipeline stages in sequence, update job status + logs at each phase, write back summary fields to Land row on success, mark failed on exception
- [x] `api/routers/lands.py` — `POST /lands`, `GET /lands`, `GET /lands/{id}`, `GET /lands/{id}/report`
- [x] `api/routers/jobs.py` — `GET /jobs/{id}`, `GET /jobs/{id}/logs`
- [x] `api/main.py` — app wiring, CORS (allow localhost:3000), lifespan (DB init), include routers, `GET /health`
- [ ] Manual smoke-test: `uv run fastapi dev`, POST a land, poll job until succeeded, GET result
- [x] API startup smoke test: import app, initialize SQLite schema, `GET /health`, `GET /lands`

**Acceptance:** All 6 endpoints respond correctly; a submitted land reaches `succeeded` status and returns real assessment fields

---

### Milestone 3 — Portal smart routing

Mock data is permanent demo content and is never removed. The portal routes gain smart ID-based routing for real submissions.

- [x] Add `FASTAPI_URL=http://localhost:8000` to `portal/.env.local`
- [x] Update `GET /api/lands`: return `MOCK_LANDS` merged with results from `GET http://FASTAPI_URL/lands`; gracefully skip FastAPI fetch if unreachable
- [x] Update `POST /api/lands`: forward body to `POST http://FASTAPI_URL/lands`; return real response (real land + job IDs)
- [x] Update `GET /api/lands/[id]`: check if `id` is in `MOCK_LANDS`; if yes return mock entry; if no proxy to `GET http://FASTAPI_URL/lands/{id}`
- [x] Update `GET /api/jobs/[id]`: check if `id` is a known mock job ID; if yes return `getMockJob()`; if no proxy to `GET http://FASTAPI_URL/jobs/{id}`
- [x] Verify existing mock lands still render correctly at route/type level (portal typecheck passes; GET route keeps mock fallback)
- [ ] Verify new submission: polygon draw → POST → real job ID → polling → result page with real assessment data

**Acceptance:** Mock lands always visible; newly submitted real lands appear in the list and complete end-to-end

---

### Milestone 4 — Contracts

- [x] Write `contracts/schemas/land-create.json`
- [x] Write `contracts/schemas/land-result.json`
- [x] Write `contracts/schemas/job-state.json`
- [x] Update `ENGINEERING.md` §Contracts to note schemas now exist

**Acceptance:** Schemas match actual request/response shapes from Milestone 2

---

## Open Questions

- [ ] Should the pipeline reuse an existing `aoi_id` folder if the same polygon is submitted twice, or always create a fresh run? [clarification needed]
- [ ] What is the intended polling interval for job status in the portal? (current mock uses no polling — portal re-renders on navigate)
- [ ] Should logs be streamed (SSE) or polled? Phase A decision assumed polling.

## Verification Log

- 2026-05-18: Ran `uv sync --extra data`; installed FastAPI/SQLModel/Uvicorn dependencies and refreshed `uv.lock`.
- 2026-05-18: Switched to `fastapi[standard]` so the modern `uv run fastapi dev` command is supported; reran `uv sync --extra data`.
- 2026-05-18: Verified FastAPI CLI with `uv run fastapi --help` and `uv run fastapi dev --help`. On Windows, help output may need `PYTHONIOENCODING=utf-8` because Rich prints emoji.
- 2026-05-18: Ran `uv run python -c "import api.main; ..."`; API imports and routes register.
- 2026-05-18: Ran `uv run python -c "from api.database import init_db; init_db(); ..."`; SQLite schema initializes. Fixed `api/database.py` to import models before `SQLModel.metadata.create_all()`.
- 2026-05-18: Ran FastAPI `TestClient` smoke test for `GET /health` and `GET /lands`; both returned 200.
- 2026-05-18: Ran `uv run python -m compileall farmtrust_core scripts api`; passed.
- 2026-05-18: Ran `bun run typecheck` in `portal/`; passed.

## Decisions

| Date | Decision |
|---|---|
| 2026-05-18 | SQLite for Phase A persistence (minimal; swap to Postgres in Phase B) |
| 2026-05-18 | Background thread execution (no Celery in Phase A) |
| 2026-05-18 | Add full polygon support to pipeline (not just bbox conversion) |
| 2026-05-18 | No auth anywhere for Phase A; portal proxies all calls server-side |
| 2026-05-18 | Mock lands are permanent demo fixtures; only new real submissions are forwarded to FastAPI; routing is ID-based, no env flag or mode toggle |

## Done Summary

- Implemented path helpers, polygon parsing/bbox derivation, polygon raster masking, FastAPI backend, portal smart routing, and Phase A JSON schemas.
- Synced Python dependencies with `uv sync --extra data`; backend dev server should now use `uv run fastapi dev`.
- Verified Python syntax with `uv run python -m compileall farmtrust_core scripts api`, portal TypeScript with `bun run typecheck`, API import/route registration, SQLite schema initialization, and FastAPI `TestClient` smoke tests for `GET /health` and `GET /lands`.
- Remaining full E2E verification requires running a real polygon submission through Planetary Computer, which can be slow/network-dependent.
