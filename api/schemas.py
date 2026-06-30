"""Pydantic schemas for API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class PacketInterval(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None


class PacketHeadline(BaseModel):
    state_label: str
    cropping_intensity: Optional[str] = None
    overall_confidence: Literal["high", "medium", "low"]
    summary: str


class PacketClaim(BaseModel):
    id: str
    layer: Literal["observed", "interpreted", "confidence", "watch"]
    claim: str
    confidence: Literal["strong", "moderate", "limited", "provisional", "none"]
    rests_on: str


class PacketCycle(BaseModel):
    season_id: Optional[str] = None
    start_date: Optional[str] = None
    peak_date: Optional[str] = None
    end_date: Optional[str] = None
    season_calendar_label: Optional[str] = None
    lifecycle_status: Optional[str] = None
    is_open: Optional[bool] = None
    peak_ndvi: Optional[float] = None
    duration_days: Optional[float] = None
    detection_status: Optional[str] = None
    cycle_split_merged: Optional[bool] = None


class PacketActivityRecord(BaseModel):
    cycles: list[PacketCycle] = Field(default_factory=list)
    complete_window_count: int = 0
    open_window_count: int = 0
    borderline_window_count: int = 0


class PacketTrackRecord(BaseModel):
    seasons_observed: int
    seasons_for_certifiable_trend: int
    fraction: float
    status_so_far: Literal["improving", "declining", "stable", "too_soon_to_tell"]
    provisional: bool
    note: str


class PacketRiskItem(BaseModel):
    item: str
    kind: Literal["land_risk", "evidence_limitation"]
    severity: Literal["high", "moderate", "low"]
    reason: str
    code: Optional[str] = None


class PacketIndicators(BaseModel):
    values: dict[str, Optional[float]] = Field(default_factory=dict)
    interpretation_notes: dict[str, str] = Field(default_factory=dict)


class EvidencePacketResponse(BaseModel):
    # The packet's "schema" key shadows BaseModel.schema; expose it via an alias.
    model_config = ConfigDict(populate_by_name=True)

    packet_version: str
    packet_schema: str = Field(alias="schema")
    aoi_id: str
    assessment_status: Optional[str] = None
    source_artifacts: list[str] = Field(default_factory=list)
    interval: PacketInterval
    headline: PacketHeadline
    claims: list[PacketClaim] = Field(default_factory=list)
    layers: dict[str, list[str]] = Field(default_factory=dict)
    activity_record: PacketActivityRecord
    track_record: PacketTrackRecord
    risk_register: list[PacketRiskItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    indicators: PacketIndicators
    local_context: list[Any] = Field(default_factory=list)


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
