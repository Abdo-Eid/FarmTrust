"""Pydantic schemas for API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
JobPhase = Literal[
    "aoi_validation",
    "satellite_fetch",
    "vegetation_analysis",
    "risk_modeling",
    "report_generation",
]


class CreateLandPayload(BaseModel):
    name: str
    governorate: str
    district: Optional[str] = None
    notes: Optional[str] = None
    method: Literal["polygon"] = "polygon"
    geometry: dict[str, Any]
    area_feddan: float = Field(gt=0)
    lookback_days: int = Field(default=730, ge=90, le=1825)


class Confidence(BaseModel):
    status: Literal["high", "medium", "low"]
    rationale: str


class Indicators(BaseModel):
    ndvi_peak: Optional[float] = None
    ndvi_auc: Optional[float] = None
    cloud_free_scenes: Optional[int] = None
    neighbor_comparison: Optional[Literal["above_avg", "avg", "below_avg"]] = None
    observation_coverage: Optional[float] = None


class NDVIPoint(BaseModel):
    date: str
    ndvi: float
    evi: Optional[float] = None
    cloud_coverage: float
    flag: Optional[str] = None


class SeasonRecord(BaseModel):
    season: str
    start_date: str
    end_date: str
    ndvi_peak: float
    outcome: Literal["good", "interrupted", "weak"]
    anomaly: Optional[str] = None


class LandResponse(BaseModel):
    id: str
    name: str
    governorate: str
    district: Optional[str] = None
    area_feddan: float
    submitted_at: str
    job_id: str
    job_status: JobStatus
    geometry: Optional[dict[str, Any]] = None
    land_status: Optional[Literal["active", "intermittent", "inactive", "encroachment"]] = None
    trend_2y: Optional[Literal["improving", "stable", "declining"]] = None
    season_performance: Optional[Literal["good", "interrupted", "weak"]] = None
    flags: Optional[list[Literal["waterlogging", "salinity", "abandonment", "encroachment"]]] = None
    confidence: Optional[Confidence] = None
    risk_tier: Optional[Literal["low", "medium", "high"]] = None
    indicators: Optional[Indicators] = None
    report_summary: Optional[str] = None
    ndvi_series: Optional[list[NDVIPoint]] = None
    season_records: Optional[list[SeasonRecord]] = None


class JobResponse(BaseModel):
    id: str
    land_id: str
    status: JobStatus
    phase: Optional[JobPhase] = None
    progress: int
    scene_total: Optional[int] = None
    scene_done: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    logs: list[str]


class JobLogsResponse(BaseModel):
    id: str
    logs: list[str]


class HealthResponse(BaseModel):
    status: str
    time: datetime
