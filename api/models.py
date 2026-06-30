"""Database table models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Land(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    governorate: str
    district: Optional[str] = None
    geometry: str
    area_feddan: float
    method: str = "polygon"
    notes: Optional[str] = None
    aoi_id: str
    job_id: str = Field(index=True)
    lookback_days: int = Field(default=730)
    land_status: Optional[str] = None
    trend_2y: Optional[str] = None
    season_performance: Optional[str] = None
    risk_tier: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class AssessmentGroup(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    governorate: str
    district: Optional[str] = None
    notes: Optional[str] = None
    job_id: str = Field(index=True, unique=True)
    primary_land_id: str = Field(index=True)
    aoi_count: int = Field(default=1)
    total_area_feddan: float
    lookback_days: int = Field(default=730)
    created_at: datetime = Field(default_factory=utc_now)


class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)
    land_id: str = Field(index=True)
    status: str = Field(default="queued", index=True)
    phase: Optional[str] = None
    logs: str = ""
    error: Optional[str] = None
    cancel_requested: bool = Field(default=False)
    scene_total: Optional[int] = None
    scene_done: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
