"""Pydantic schemas for API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
AssessmentStatus = Literal["complete", "manual_review_required"]
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


class SatelliteEvidenceCoverage(BaseModel):
    status: Literal["good", "fair", "limited", "insufficient"]
    rationale: str


class HistoryCoverage(BaseModel):
    status: Literal["sufficient_history", "limited_history", "insufficient_history"]
    rationale: str
    observed_activity_cycle_count: Optional[int] = None
    complete_activity_cycle_count: Optional[int] = None
    assessment_interval_days: Optional[int] = None


class AbsenceAssessment(BaseModel):
    status: Literal[
        "activity_present",
        "absence_supported",
        "absence_uncertain",
        "not_assessed",
        "insufficient_evidence",
    ]
    rationale: str


class Indicators(BaseModel):
    ndvi_peak: Optional[float] = None
    ndvi_p95_peak: Optional[float] = None
    ndvi_spread_median: Optional[float] = None
    ndvi_auc: Optional[float] = None
    evi_peak: Optional[float] = None
    ndmi_median: Optional[float] = None
    mndwi_median: Optional[float] = None
    cloud_free_scenes: Optional[int] = None
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
    assessment_status: Optional[AssessmentStatus] = None
    geometry: Optional[dict[str, Any]] = None
    land_status: Optional[Literal["active", "intermittent", "inactive", "encroachment"]] = None
    trend_2y: Optional[Literal["improving", "stable", "declining"]] = None
    season_performance: Optional[Literal["good", "interrupted", "weak"]] = None
    flags: Optional[list[Literal["waterlogging", "salinity", "abandonment", "encroachment"]]] = None
    satellite_evidence_coverage: Optional[SatelliteEvidenceCoverage] = None
    history_coverage: Optional[HistoryCoverage] = None
    absence_assessment: Optional[AbsenceAssessment] = None
    confidence: Optional[Confidence] = None
    risk_tier: Optional[Literal["low", "medium", "high"]] = None
    indicators: Optional[Indicators] = None
    report_summary: Optional[str] = None
    ndvi_series: Optional[list[NDVIPoint]] = None
    season_records: Optional[list[SeasonRecord]] = None


class AssessmentGroupResponse(BaseModel):
    id: str
    name: str
    governorate: str
    district: Optional[str] = None
    notes: Optional[str] = None
    area_feddan: float
    submitted_at: str
    job_id: str
    primary_land_id: str
    aoi_count: int
    job_status: JobStatus
    assessment_status: Optional[AssessmentStatus] = None
    land_status: Optional[Literal["active", "intermittent", "inactive", "encroachment"]] = None
    trend_2y: Optional[Literal["improving", "stable", "declining"]] = None
    season_performance: Optional[Literal["good", "interrupted", "weak"]] = None
    risk_tier: Optional[Literal["low", "medium", "high"]] = None
    confidence: Optional[Confidence] = None
    satellite_evidence_coverage: Optional[SatelliteEvidenceCoverage] = None
    children: list[LandResponse] = Field(default_factory=list)


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
