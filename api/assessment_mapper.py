"""Map pipeline assessment artifacts to portal DTOs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from api.models import Job, Land
from api.schemas import Confidence, Indicators, LandResponse, NDVIPoint, SatelliteEvidenceCoverage, SeasonRecord
from farmtrust_core.io.paths import land_assessment_path, season_windows_path, smoothed_timeseries_path


VALID_TRENDS = {"improving", "stable", "declining"}
VALID_SEASON_LABELS = {"good", "interrupted", "weak"}
MANUAL_REVIEW_STATUS = "manual_review_required"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _split_logs(job: Job) -> list[str]:
    return [line for line in job.logs.splitlines() if line.strip()]


def _base_response(land: Land, job: Job) -> dict[str, Any]:
    return {
        "id": land.id,
        "name": land.name,
        "governorate": land.governorate,
        "district": land.district,
        "area_feddan": land.area_feddan,
        "submitted_at": land.created_at.isoformat(),
        "job_id": land.job_id,
        "job_status": job.status,
        "assessment_status": None,
        "geometry": json.loads(land.geometry),
        "land_status": land.land_status,
        "trend_2y": land.trend_2y if land.trend_2y in VALID_TRENDS else None,
        "season_performance": land.season_performance if land.season_performance in VALID_SEASON_LABELS else None,
        "risk_tier": land.risk_tier,
    }


def _risk_flags(assessment: dict[str, Any]) -> list[str]:
    mapped: list[str] = []
    for flag in assessment.get("risk_flags", []):
        code = str(flag.get("code", ""))
        if "waterlogging" in code:
            mapped.append("waterlogging")
        elif "salinity" in code:
            mapped.append("salinity")
        elif "inactivity" in code:
            mapped.append("abandonment")
        elif "encroachment" in code:
            mapped.append("encroachment")
    return sorted(set(mapped))


def _risk_tier(assessment: dict[str, Any]) -> str:
    severities = [
        str(flag.get("severity", "low"))
        for flag in assessment.get("risk_flags", [])
        if not str(flag.get("code", "")).startswith(("continuity_gap", "season_gap_overlap", "provisional"))
    ]
    if "high" in severities:
        return "high"
    if "moderate" in severities:
        return "medium"
    return "low"


def _confidence(assessment: dict[str, Any]) -> Confidence | None:
    raw = assessment.get("confidence")
    if not isinstance(raw, dict):
        return None
    reasons = raw.get("reasons", [])
    rationale = " ".join(str(reason) for reason in reasons) if isinstance(reasons, list) else str(reasons)
    return Confidence(status=str(raw.get("level", "medium")), rationale=rationale)


def _satellite_evidence_coverage(assessment: dict[str, Any]) -> SatelliteEvidenceCoverage | None:
    raw = assessment.get("satellite_evidence_coverage")
    if not isinstance(raw, dict):
        return None
    return SatelliteEvidenceCoverage(
        status=str(raw.get("status", "fair")),
        rationale=str(raw.get("rationale", "Satellite evidence coverage was assessed from usable observations.")),
    )


def _indicators(assessment: dict[str, Any]) -> Indicators:
    metrics = assessment.get("metrics_summary", {})
    season_strength = metrics.get("season_strength", [])
    latest = season_strength[-1] if season_strength else {}
    usable_count = metrics.get("usable_observation_count")
    return Indicators(
        ndvi_peak=metrics.get("interval_max_ndvi"),
        ndvi_auc=latest.get("auc_ndvi"),
        cloud_free_scenes=int(usable_count) if usable_count is not None else None,
        neighbor_comparison="avg",
        observation_coverage=metrics.get("active_observation_fraction"),
    )


def _report_summary(assessment: dict[str, Any]) -> str:
    if assessment.get("assessment_status") == MANUAL_REVIEW_STATUS:
        coverage = assessment.get("satellite_evidence_coverage", {})
        rationale = coverage.get("rationale", "") if isinstance(coverage, dict) else ""
        return (
            "Manual review is required because satellite evidence is insufficient "
            f"for a final automated assessment. {rationale}"
        ).strip()

    status = str(assessment.get("land_status", "unknown"))
    trend = str(assessment.get("trend_2y", "uncertain"))
    latest = assessment.get("latest_season_performance", {})
    latest_label = latest.get("label", "unknown") if isinstance(latest, dict) else "unknown"
    evidence = assessment.get("evidence", {})
    basis = evidence.get("land_status_basis", "") if isinstance(evidence, dict) else ""
    return f"Assessment classified this parcel as {status} with a {trend} trend. Latest season performance is {latest_label}. {basis}".strip()


def _ndvi_series(aoi_id: str) -> list[NDVIPoint]:
    path = smoothed_timeseries_path(aoi_id)
    if not path.exists():
        return []
    points: list[NDVIPoint] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ndvi = row.get("ndvi_smoothed") or row.get("ndvi_raw")
            if not ndvi:
                continue
            valid_fraction = float(row.get("valid_fraction") or 0)
            points.append(
                NDVIPoint(
                    date=str(row["timestamp"]).split("T")[0],
                    ndvi=float(ndvi),
                    evi=float(row["evi_smoothed"] or row["evi_raw"]),
                    cloud_coverage=max(0.0, min(1.0, 1.0 - valid_fraction)),
                )
            )
    return points


def _season_records(aoi_id: str) -> list[SeasonRecord]:
    payload = _load_json(season_windows_path(aoi_id))
    if not payload:
        return []
    records: list[SeasonRecord] = []
    for season in payload.get("seasons", []):
        label = str(season.get("quality_label", "weak"))
        if label not in VALID_SEASON_LABELS:
            label = "weak"
        records.append(
            SeasonRecord(
                season=str(season.get("season_id", "Season")),
                start_date=str(season.get("start_date")),
                end_date=str(season.get("end_date")),
                ndvi_peak=float(season.get("peak_ndvi", 0)),
                outcome=label,
                anomaly=str(season.get("evidence_summary")) if label != "good" else None,
            )
        )
    return records


def map_land_response(land: Land, job: Job) -> LandResponse:
    payload = _base_response(land, job)
    assessment = _load_json(land_assessment_path(land.aoi_id))
    if assessment:
        assessment_status = str(assessment.get("assessment_status", "complete"))
        latest = assessment.get("latest_season_performance", {})
        latest_label = latest.get("label") if isinstance(latest, dict) else None
        is_manual_review = assessment_status == MANUAL_REVIEW_STATUS
        payload.update(
            {
                "assessment_status": assessment_status,
                "land_status": None if is_manual_review else assessment.get("land_status"),
                "trend_2y": None
                if is_manual_review
                else assessment.get("trend_2y")
                if assessment.get("trend_2y") in VALID_TRENDS
                else None,
                "season_performance": None
                if is_manual_review
                else latest_label
                if latest_label in VALID_SEASON_LABELS
                else None,
                "flags": [] if is_manual_review else _risk_flags(assessment),
                "satellite_evidence_coverage": _satellite_evidence_coverage(assessment),
                "confidence": _confidence(assessment),
                "risk_tier": None if is_manual_review else _risk_tier(assessment),
                "indicators": _indicators(assessment),
                "report_summary": _report_summary(assessment),
                "ndvi_series": _ndvi_series(land.aoi_id),
                "season_records": _season_records(land.aoi_id),
            }
        )
    return LandResponse(**payload)


def job_logs(job: Job) -> list[str]:
    return _split_logs(job)
