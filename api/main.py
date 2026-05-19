"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import init_db
from api.routers import jobs, lands
from api.schemas import HealthResponse


def _recover_stale_jobs() -> None:
    """Mark any jobs left in 'running' state as failed (server was killed mid-worker)."""
    from sqlmodel import Session, select
    from api.database import engine
    from api.models import Job, utc_now

    with Session(engine) as session:
        stale = session.exec(select(Job).where(Job.status == "running")).all()
        for job in stale:
            job.status = "failed"
            job.error = "Server stopped before job completed; please resubmit."
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            session.add(job)
        if stale:
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _recover_stale_jobs()
    yield


app = FastAPI(title="FarmTrust API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lands.router)
app.include_router(jobs.router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", time=datetime.now(timezone.utc))
