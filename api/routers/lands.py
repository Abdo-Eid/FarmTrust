"""Land endpoints."""

from __future__ import annotations

import json
import shutil
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.assessment_mapper import map_land_response
from api.database import get_session
from api.models import Job, Land
from api.schemas import CreateLandPayload, LandResponse
from api.worker import start_job
from farmtrust_core.ingest.config import normalize_geometry
from farmtrust_core.io.paths import aoi_dir, assessment_dir, preprocess_dir, seasonal_dir


router = APIRouter(prefix="/lands", tags=["lands"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=LandResponse, status_code=201)
def create_land(payload: CreateLandPayload, session: SessionDep) -> LandResponse:
    try:
        geometry = normalize_geometry(payload.geometry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    land_id = f"land-{uuid4().hex}"
    job_id = f"job-{uuid4().hex}"
    land = Land(
        id=land_id,
        name=payload.name,
        governorate=payload.governorate,
        district=payload.district,
        notes=payload.notes,
        method=payload.method,
        geometry=json.dumps(geometry),
        area_feddan=payload.area_feddan,
        aoi_id=land_id,
        job_id=job_id,
        lookback_days=payload.lookback_days,
    )
    job = Job(id=job_id, land_id=land_id, status="queued", logs="[INFO] Job queued, waiting for worker...")
    session.add(land)
    session.add(job)
    session.commit()
    session.refresh(land)
    session.refresh(job)

    start_job(job_id, land_id)
    return map_land_response(land, job)


@router.get("", response_model=list[LandResponse])
def list_lands(session: SessionDep) -> list[LandResponse]:
    lands = session.exec(select(Land).order_by(Land.created_at.desc())).all()
    responses: list[LandResponse] = []
    for land in lands:
        job = session.get(Job, land.job_id)
        if job is not None:
            responses.append(map_land_response(land, job))
    return responses


@router.get("/{land_id}", response_model=LandResponse)
def get_land(land_id: str, session: SessionDep) -> LandResponse:
    land = session.get(Land, land_id)
    if land is None:
        raise HTTPException(status_code=404, detail="Land not found")
    job = session.get(Job, land.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return map_land_response(land, job)


@router.delete("/{land_id}", status_code=204)
def delete_land(land_id: str, session: SessionDep) -> None:
    land = session.get(Land, land_id)
    if land is None:
        raise HTTPException(status_code=404, detail="Land not found")

    # Block delete if any job is still active
    active_jobs = session.exec(
        select(Job).where(
            Job.land_id == land_id,
            Job.status.in_(["queued", "running"]),  # type: ignore[attr-defined]
        )
    ).all()
    if active_jobs:
        raise HTTPException(
            status_code=409,
            detail="An active job is running. Stop the pipeline before deleting.",
        )

    # Delete all job rows for this land
    all_jobs = session.exec(select(Job).where(Job.land_id == land_id)).all()
    for job in all_jobs:
        session.delete(job)

    # Remove disk artifacts (ignore if already absent)
    aoi_id = land.aoi_id
    for path_fn in (aoi_dir, preprocess_dir, seasonal_dir, assessment_dir):
        p = path_fn(aoi_id)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    session.delete(land)
    session.commit()


@router.get("/{land_id}/report", response_model=LandResponse)
def get_land_report(land_id: str, session: SessionDep) -> LandResponse:
    return get_land(land_id, session)
