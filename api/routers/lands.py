"""Land endpoints."""

from __future__ import annotations

import json
import math
import shutil
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.assessment_mapper import map_land_response
from api.database import get_session
from api.models import AssessmentGroup, Job, Land
from api.schemas import AssessmentGroupResponse, CreateLandPayload, LandResponse
from api.worker import start_job
from farmtrust_core.ingest.config import normalize_geometries
from farmtrust_core.io.paths import aoi_dir, assessment_dir, preprocess_dir, seasonal_dir


router = APIRouter(prefix="/lands", tags=["lands"])
SessionDep = Annotated[Session, Depends(get_session)]
FEDDAN_TO_SQM = 4200.833


def _polygon_area_feddan(geometry: dict) -> float:
    """Mirror the portal's spherical ring-area estimate for backend fan-out."""
    points = geometry["coordinates"][0]
    if len(points) > 1 and points[0][0] == points[-1][0] and points[0][1] == points[-1][1]:
        points = points[:-1]
    if len(points) < 3:
        return 0.0

    radius_m = 6_371_000
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        lon1, lat1 = float(point[0]), float(point[1])
        lon2, lat2 = float(next_point[0]), float(next_point[1])
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        area += delta_lon * (2 + math.sin(phi1) + math.sin(phi2))
    return abs((area * radius_m * radius_m) / 2) / FEDDAN_TO_SQM


_RISK_ORDER = {None: 0, "low": 1, "medium": 2, "high": 3}
_CONFIDENCE_ORDER = {None: 0, "high": 1, "medium": 2, "low": 3}


def _group_response(group: AssessmentGroup, job: Job, lands: list[Land]) -> AssessmentGroupResponse:
    children = [map_land_response(land, job) for land in lands]
    completed_children = [child for child in children if child.assessment_status]
    primary = children[0] if children else None
    land_statuses = {child.land_status for child in completed_children if child.land_status}
    trends = {child.trend_2y for child in completed_children if child.trend_2y}
    seasons = {child.season_performance for child in completed_children if child.season_performance}
    risk_tier = max((child.risk_tier for child in completed_children), key=lambda value: _RISK_ORDER[value], default=None)
    confidence = max(
        (child.confidence for child in completed_children if child.confidence),
        key=lambda value: _CONFIDENCE_ORDER[value.status],
        default=None,
    )
    return AssessmentGroupResponse(
        id=group.id,
        name=group.name,
        governorate=group.governorate,
        district=group.district,
        notes=group.notes,
        area_feddan=group.total_area_feddan,
        submitted_at=group.created_at.isoformat(),
        job_id=group.job_id,
        primary_land_id=group.primary_land_id,
        aoi_count=group.aoi_count,
        job_status=job.status,
        assessment_status=primary.assessment_status if len(children) == 1 and primary else None,
        land_status=next(iter(land_statuses)) if len(land_statuses) == 1 else None,
        trend_2y=next(iter(trends)) if len(trends) == 1 else None,
        season_performance=next(iter(seasons)) if len(seasons) == 1 else None,
        risk_tier=risk_tier,
        confidence=confidence,
        satellite_evidence_coverage=primary.satellite_evidence_coverage if len(children) == 1 and primary else None,
        children=children,
    )


def _lands_for_job(session: Session, job_id: str) -> list[Land]:
    return session.exec(select(Land).where(Land.job_id == job_id).order_by(Land.created_at)).all()


@router.post("", response_model=LandResponse, status_code=201)
def create_land(payload: CreateLandPayload, session: SessionDep) -> LandResponse:
    try:
        geometries = normalize_geometries(payload.geometry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job_id = f"job-{uuid4().hex}"
    lands: list[Land] = []
    for index, geometry in enumerate(geometries, start=1):
        land_id = f"land-{uuid4().hex}"
        name = payload.name if len(geometries) == 1 else f"{payload.name} {index}"
        area_feddan = payload.area_feddan if len(geometries) == 1 else _polygon_area_feddan(geometry)
        land = Land(
            id=land_id,
            name=name,
            governorate=payload.governorate,
            district=payload.district,
            notes=payload.notes,
            method=payload.method,
            geometry=json.dumps(geometry),
            area_feddan=area_feddan,
            aoi_id=land_id,
            job_id=job_id,
            lookback_days=payload.lookback_days,
        )
        lands.append(land)
        session.add(land)

    primary_land = lands[0]
    total_area_feddan = sum(land.area_feddan for land in lands)
    group = AssessmentGroup(
        id=f"group-{uuid4().hex}",
        name=payload.name,
        governorate=payload.governorate,
        district=payload.district,
        notes=payload.notes,
        job_id=job_id,
        primary_land_id=primary_land.id,
        aoi_count=len(lands),
        total_area_feddan=total_area_feddan,
        lookback_days=payload.lookback_days,
    )
    queued_message = "[INFO] Job queued, waiting for worker..."
    if len(lands) > 1:
        queued_message = f"[INFO] Job queued for {len(lands)} AOIs, waiting for worker..."
    job = Job(id=job_id, land_id=primary_land.id, status="queued", logs=queued_message)
    session.add(group)
    session.add(job)
    session.commit()
    for land in lands:
        session.refresh(land)
    session.refresh(job)

    start_job(job_id, primary_land.id)
    return map_land_response(primary_land, job)


@router.get("/groups", response_model=list[AssessmentGroupResponse])
def list_assessment_groups(session: SessionDep) -> list[AssessmentGroupResponse]:
    groups = session.exec(select(AssessmentGroup).order_by(AssessmentGroup.created_at.desc())).all()
    responses: list[AssessmentGroupResponse] = []
    for group in groups:
        job = session.get(Job, group.job_id)
        if job is None:
            continue
        lands = _lands_for_job(session, group.job_id)
        responses.append(_group_response(group, job, lands))

    grouped_job_ids = {group.job_id for group in groups}
    legacy_jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    for job in legacy_jobs:
        if job.id in grouped_job_ids:
            continue
        lands = _lands_for_job(session, job.id)
        if not lands:
            continue
        primary = lands[0]
        legacy_group = AssessmentGroup(
            id=f"group-{job.id}",
            name=primary.name,
            governorate=primary.governorate,
            district=primary.district,
            notes=primary.notes,
            job_id=job.id,
            primary_land_id=primary.id,
            aoi_count=len(lands),
            total_area_feddan=sum(land.area_feddan for land in lands),
            lookback_days=primary.lookback_days,
            created_at=primary.created_at,
        )
        responses.append(_group_response(legacy_group, job, lands))
    return responses


@router.get("/groups/{group_id}", response_model=AssessmentGroupResponse)
def get_assessment_group(group_id: str, session: SessionDep) -> AssessmentGroupResponse:
    group = session.get(AssessmentGroup, group_id)
    if group is None and group_id.startswith("group-job-"):
        job_id = group_id.removeprefix("group-")
        job = session.get(Job, job_id)
        lands = _lands_for_job(session, job_id)
        if job is not None and lands:
            primary = lands[0]
            legacy_group = AssessmentGroup(
                id=group_id,
                name=primary.name,
                governorate=primary.governorate,
                district=primary.district,
                notes=primary.notes,
                job_id=job.id,
                primary_land_id=primary.id,
                aoi_count=len(lands),
                total_area_feddan=sum(land.area_feddan for land in lands),
                lookback_days=primary.lookback_days,
                created_at=primary.created_at,
            )
            return _group_response(legacy_group, job, lands)
    if group is None:
        raise HTTPException(status_code=404, detail="Assessment group not found")
    job = session.get(Job, group.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _group_response(group, job, _lands_for_job(session, group.job_id))


@router.delete("/groups/{group_id}", status_code=204)
def delete_assessment_group(group_id: str, session: SessionDep) -> None:
    group = session.get(AssessmentGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Assessment group not found")
    job = session.get(Job, group.job_id)
    if job is not None and job.status in {"queued", "running"}:
        raise HTTPException(
            status_code=409,
            detail="An active shared job is running. Stop the pipeline before deleting this submission.",
        )

    for land in _lands_for_job(session, group.job_id):
        for path_fn in (aoi_dir, preprocess_dir, seasonal_dir, assessment_dir):
            p = path_fn(land.aoi_id)
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
        session.delete(land)

    shared_dir = aoi_dir(f"batch-{group.job_id}")
    if shared_dir.exists():
        shutil.rmtree(shared_dir, ignore_errors=True)
    if job is not None:
        session.delete(job)
    session.delete(group)
    session.commit()


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

    # Block delete if this land's shared job is still active.
    job = session.get(Job, land.job_id)
    if job is not None and job.status in {"queued", "running"}:
        raise HTTPException(
            status_code=409,
            detail="An active job is running. Stop the pipeline before deleting.",
        )

    # Remove disk artifacts (ignore if already absent)
    aoi_id = land.aoi_id
    for path_fn in (aoi_dir, preprocess_dir, seasonal_dir, assessment_dir):
        p = path_fn(aoi_id)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    other_lands = session.exec(
        select(Land).where(Land.job_id == land.job_id, Land.id != land.id)
    ).all()
    if not other_lands:
        group = session.exec(select(AssessmentGroup).where(AssessmentGroup.job_id == land.job_id)).first()
        if group is not None:
            session.delete(group)
        shared_dir = aoi_dir(f"batch-{land.job_id}")
        if shared_dir.exists():
            shutil.rmtree(shared_dir, ignore_errors=True)
        if job is not None:
            session.delete(job)

    session.delete(land)
    session.commit()


@router.get("/{land_id}/report", response_model=LandResponse)
def get_land_report(land_id: str, session: SessionDep) -> LandResponse:
    return get_land(land_id, session)
