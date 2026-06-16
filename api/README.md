# api

FastAPI backend for FarmTrust. Handles land submission, pipeline job lifecycle, real-time status streaming, and result serving. Pipeline logic lives in `farmtrust_core`; this layer wires it to HTTP.

## Run

```bash
uv run fastapi dev
```

Starts on `http://localhost:8000` with hot reload. Interactive docs at `/docs`.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `FARMTRUST_DATA_DIR` | `data/` | Root directory for all pipeline artifacts |

No other env vars required for local dev.

## Endpoints

### Lands

| Method | Path | Description |
|---|---|---|
| `POST` | `/lands` | Submit a new land; starts pipeline job immediately |
| `GET` | `/lands` | List all lands (ordered by submission date desc) |
| `GET` | `/lands/{id}` | Get a single land with current job state |
| `DELETE` | `/lands/{id}` | Delete land, all job rows, and all disk artifacts. Returns 409 if a job is active — stop the pipeline first |

### Jobs

| Method | Path | Description |
|---|---|---|
| `GET` | `/jobs/{id}` | Current job snapshot (status, phase, progress, scene counts) |
| `GET` | `/jobs/{id}/logs` | Raw pipeline log text |
| `POST` | `/jobs/{id}/cancel` | Request cancellation of a running/queued job |
| `GET` | `/jobs/{id}/events` | SSE stream — emits `job.update`, `job.done`, `job.error` at 1 s intervals until terminal |

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok", "time": "<utc>"}` |

## Job lifecycle

```
queued → running → succeeded
                 → failed
                 → cancelled   (after POST /jobs/{id}/cancel)
```

On startup, any job left in `running` (server killed mid-run) is automatically recovered to `failed`.

## Disk layout

All artifacts are keyed by `land_id` (which equals `aoi_id`):

```
data/
  {land_id}/                  # raw ingest: indices_timeseries.csv, run_metadata.json
  preprocess/{land_id}/       # smoothed NDVI, quality metrics
  seasonal/{land_id}/         # season windows
  assessment/{land_id}/       # land_assessment.json
```

Deleting a land via `DELETE /lands/{id}` removes all four directories.

## Database

SQLite at `farmtrust.db` (auto-created on first run). Schema is managed by SQLModel `create_all` + a lightweight `ALTER TABLE ADD COLUMN` migration in `database.py` that silently skips columns that already exist — no migration tool needed for the current build.

## Key modules

| File | Role |
|---|---|
| `main.py` | App factory, CORS, lifespan (init DB + stale-job recovery) |
| `models.py` | `Land` and `Job` SQLModel table definitions |
| `schemas.py` | Request/response Pydantic models |
| `database.py` | Engine, session dep, `init_db`, `_migrate_db` |
| `worker.py` | Background thread runner; cancel flags; scene progress; `progress_for_job` |
| `assessment_mapper.py` | Maps pipeline artifacts → `LandResponse` DTO |
| `routers/lands.py` | Land CRUD + delete |
| `routers/jobs.py` | Job status, logs, cancel, SSE stream |
