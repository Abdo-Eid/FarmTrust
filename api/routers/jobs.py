"""Job endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterable
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlmodel import Session

from api.assessment_mapper import job_logs
from api.database import engine, get_session
from api.models import Job, utc_now
from api.schemas import JobLogsResponse, JobResponse
from api.worker import progress_for_job, request_cancel


router = APIRouter(prefix="/jobs", tags=["jobs"])
SessionDep = Annotated[Session, Depends(get_session)]

_TERMINAL = {"succeeded", "failed", "cancelled"}


def _job_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        land_id=job.land_id,
        status=job.status,
        phase=job.phase,
        progress=progress_for_job(job),
        scene_total=job.scene_total,
        scene_done=job.scene_done,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error,
        logs=job_logs(job),
    )


def _event_name(status: str) -> str:
    if status == "succeeded":
        return "job.done"
    if status in ("failed", "cancelled"):
        return "job.error"
    return "job.update"


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: SessionDep) -> JobResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job)


@router.get("/{job_id}/logs", response_model=JobLogsResponse)
def get_job_logs(job_id: str, session: SessionDep) -> JobLogsResponse:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobLogsResponse(id=job.id, logs=job_logs(job))


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, session: SessionDep) -> JobResponse:
    """Request cancellation of a running or queued job."""
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in _TERMINAL:
        raise HTTPException(status_code=409, detail=f"Job is already {job.status}")

    job.cancel_requested = True
    if job.status == "queued":
        job.status = "cancelled"
        job.completed_at = utc_now()
    job.updated_at = utc_now()
    session.add(job)
    session.commit()
    session.refresh(job)

    # Signal in-memory worker thread if running
    request_cancel(job_id)

    return _job_response(job)


@router.get("/{job_id}/events", response_class=EventSourceResponse)
async def stream_job_events(job_id: str) -> AsyncIterable[ServerSentEvent]:
    """Stream job status updates as Server-Sent Events.

    Events:
    - ``job.update`` — job is still running; payload is the current JobResponse snapshot.
    - ``job.done``   — job succeeded; stream closes after this event.
    - ``job.error``  — job failed; stream closes after this event.
    """
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        snap = _job_response(job)
        terminal = job.status in _TERMINAL
        last_ts = job.updated_at

    yield ServerSentEvent(data=snap.model_dump(), event=_event_name(snap.status), id="0")

    if terminal:
        return

    seq = 0
    while True:
        await anyio.sleep(1)
        with Session(engine) as s:
            job = s.get(Job, job_id)
            if job is None:
                return
            if job.updated_at == last_ts:
                continue
            last_ts = job.updated_at
            seq += 1
            snap = _job_response(job)
            terminal = job.status in _TERMINAL

        yield ServerSentEvent(data=snap.model_dump(), event=_event_name(snap.status), id=str(seq))
        if terminal:
            return
