"""Rule-based Phase A assessment helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from farmtrust_core.ingest.utils import safe_write_text
from farmtrust_core.seasonal.seasons import ACTIVITY_THRESHOLD

from .evidence import build_confidence_payload, build_risk_flag


REQUIRED_PREPROCESS_COLUMNS = (
    "timestamp",
    "ndvi_smoothed",
    "evi_smoothed",
    "ndmi_smoothed",
    "ndwi_smoothed",
    "is_usable",
)
REQUIRED_QUALITY_KEYS = (
    "aoi_id",
    "usable_observation_count",
    "gap_risk",
    "gap_risk_reason",
)
REQUIRED_SEASON_PAYLOAD_KEYS = (
    "aoi_id",
    "season_count",
    "gap_risk",
    "seasons",
)


@dataclass(frozen=True)
class AssessmentObservation:
    timestamp: datetime
    ndvi_smoothed: float
    evi_smoothed: float
    ndmi_smoothed: float
    ndwi_smoothed: float


@dataclass(frozen=True)
class SeasonMetric:
    season_id: str
    start_date: date
    end_date: date
    peak_date: date
    quality_label: str
    confirmation_level: str
    is_open: bool
    duration_days: float
    peak_ndvi: float
    auc_ndvi: float
    peak_evi: float
    median_ndmi: float
    median_ndwi: float
    evidence_summary: str
    gap_overlap_count: int
    gap_overlap_risk: str
    gap_overlap_stage: str


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return float((ordered[middle - 1] + ordered[middle]) / 2.0)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_assessment_observations(csv_path: Path) -> list[AssessmentObservation]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")

        missing = [column for column in REQUIRED_PREPROCESS_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Preprocess CSV is missing required columns {missing}: {csv_path}")

        observations: list[AssessmentObservation] = []
        for row in reader:
            if row["is_usable"].strip().lower() != "true":
                continue
            if not row["ndvi_smoothed"].strip():
                continue
            observations.append(
                AssessmentObservation(
                    timestamp=_parse_timestamp(row["timestamp"]),
                    ndvi_smoothed=float(row["ndvi_smoothed"]),
                    evi_smoothed=float(row["evi_smoothed"]),
                    ndmi_smoothed=float(row["ndmi_smoothed"]),
                    ndwi_smoothed=float(row["ndwi_smoothed"]),
                )
            )

    if not observations:
        raise ValueError(f"No usable smoothed observations found in {csv_path}")

    observations.sort(key=lambda item: item.timestamp)
    return observations


def _validate_quality_metrics(data: dict[str, Any], path: Path) -> dict[str, Any]:
    missing = [key for key in REQUIRED_QUALITY_KEYS if key not in data]
    if missing:
        raise ValueError(f"Quality metrics missing required keys {missing}: {path}")
    return data


def _validate_season_payload(data: dict[str, Any], path: Path) -> dict[str, Any]:
    missing = [key for key in REQUIRED_SEASON_PAYLOAD_KEYS if key not in data]
    if missing:
        raise ValueError(f"Season payload missing required keys {missing}: {path}")
    return data


def _rows_for_season(
    observations: list[AssessmentObservation],
    start_date: date,
    end_date: date,
) -> list[AssessmentObservation]:
    return [
        row
        for row in observations
        if start_date <= row.timestamp.date() <= end_date
    ]


def _compute_auc(rows: list[AssessmentObservation]) -> float:
    if len(rows) < 2:
        return 0.0

    auc = 0.0
    for left, right in zip(rows[:-1], rows[1:]):
        delta_days = (right.timestamp - left.timestamp).total_seconds() / 86400.0
        auc += ((left.ndvi_smoothed + right.ndvi_smoothed) / 2.0) * delta_days
    return float(auc)


def _build_season_metrics(
    observations: list[AssessmentObservation],
    seasons: list[dict[str, Any]],
) -> list[SeasonMetric]:
    metrics: list[SeasonMetric] = []
    for season in seasons:
        start_date = _parse_date(str(season["start_date"]))
        end_date = _parse_date(str(season["end_date"]))
        rows = _rows_for_season(observations, start_date, end_date)
        if not rows:
            continue

        metrics.append(
            SeasonMetric(
                season_id=str(season["season_id"]),
                start_date=start_date,
                end_date=end_date,
                peak_date=_parse_date(str(season["peak_date"])),
                quality_label=str(season["quality_label"]),
                confirmation_level=str(season.get("confirmation_level", "unknown")),
                is_open=bool(season["is_open"]),
                duration_days=float(season["duration_days"]),
                peak_ndvi=float(season["peak_ndvi"]),
                auc_ndvi=round(_compute_auc(rows), 6),
                peak_evi=round(max(row.evi_smoothed for row in rows), 6),
                median_ndmi=round(_median([row.ndmi_smoothed for row in rows]), 6),
                median_ndwi=round(_median([row.ndwi_smoothed for row in rows]), 6),
                evidence_summary=str(season["evidence_summary"]),
                gap_overlap_count=int(season.get("gap_overlap_count", 0)),
                gap_overlap_risk=str(season.get("gap_overlap_risk", "low")),
                gap_overlap_stage=str(season.get("gap_overlap_stage", "none")),
            )
        )

    return metrics


def _active_fraction(observations: list[AssessmentObservation]) -> float:
    active_count = sum(1 for row in observations if row.ndvi_smoothed >= ACTIVITY_THRESHOLD)
    return active_count / len(observations)


def _recent_season_metrics(
    season_metrics: list[SeasonMetric],
    *,
    latest_timestamp: datetime,
) -> list[SeasonMetric]:
    cutoff = latest_timestamp.date() - timedelta(days=365)
    return [season for season in season_metrics if season.end_date >= cutoff]


def _derive_land_status(
    season_metrics: list[SeasonMetric],
    *,
    active_fraction: float,
    latest_timestamp: datetime,
) -> tuple[str, str]:
    if not season_metrics:
        return "inactive", "No confirmed seasons were detected across the interval."

    recent_seasons = _recent_season_metrics(season_metrics, latest_timestamp=latest_timestamp)
    recent_good = sum(1 for season in recent_seasons if season.quality_label == "good")
    recent_any = len(recent_seasons)

    if recent_any >= 2 and recent_good >= 1 and active_fraction >= 0.35:
        return (
            "active",
            f"{recent_any} recent seasons were detected with active_fraction={active_fraction:.2f}.",
        )

    if recent_any >= 1 and active_fraction >= 0.18:
        return (
            "intermittent",
            f"Seasonal activity exists but continuity is weaker (recent_seasons={recent_any}, active_fraction={active_fraction:.2f}).",
        )

    return (
        "inactive",
        f"Detected activity is too sparse for a stable active classification (active_fraction={active_fraction:.2f}).",
    )


def _derive_trend(season_metrics: list[SeasonMetric]) -> tuple[str, str]:
    reference = [season for season in season_metrics if not season.is_open]
    if len(reference) < 2:
        reference = season_metrics
    if len(reference) < 2:
        return "uncertain", "Trend needs at least two season observations."

    first = reference[0]
    last = reference[-1]
    peak_delta = last.peak_ndvi - first.peak_ndvi
    auc_ratio = 0.0
    if first.auc_ndvi > 0:
        auc_ratio = (last.auc_ndvi - first.auc_ndvi) / first.auc_ndvi

    if peak_delta >= 0.03 or auc_ratio >= 0.10:
        return (
            "improving",
            f"Season strength improved from peak_ndvi={first.peak_ndvi:.3f} to {last.peak_ndvi:.3f} with auc_ratio={auc_ratio:.2f}.",
        )
    if peak_delta <= -0.03 or auc_ratio <= -0.10:
        return (
            "declining",
            f"Season strength declined from peak_ndvi={first.peak_ndvi:.3f} to {last.peak_ndvi:.3f} with auc_ratio={auc_ratio:.2f}.",
        )
    return (
        "stable",
        f"Season strength stayed within conservative stability bounds (peak_delta={peak_delta:.3f}, auc_ratio={auc_ratio:.2f}).",
    )


def _latest_season_payload(season_metrics: list[SeasonMetric]) -> tuple[dict[str, Any], SeasonMetric]:
    closed = [season for season in season_metrics if not season.is_open]
    selected = closed[-1] if closed else season_metrics[-1]
    return (
        {
            "season_id": selected.season_id,
            "label": selected.quality_label,
            "provisional": selected.is_open,
            "confirmation_level": selected.confirmation_level,
            "evidence_summary": selected.evidence_summary,
        },
        selected,
    )


def _derive_confidence(
    quality_metrics: dict[str, Any],
    latest_season: SeasonMetric,
) -> dict[str, Any]:
    continuity_score = 3.0
    season_clarity_score = 3.0
    signal_strength_score = 3.0
    reasons: list[str] = []

    gap_risk = str(quality_metrics["gap_risk"])
    if gap_risk == "high":
        continuity_score -= 1.5
        reasons.append("Satellite evidence coverage is limited, so timing and boundary confidence are reduced.")
    elif gap_risk == "moderate":
        continuity_score -= 0.75
        reasons.append("Satellite evidence coverage is fair, so some season interpretation remains cautious.")
    else:
        reasons.append("Gap continuity is strong enough for a confident baseline.")

    usable_count = int(quality_metrics["usable_observation_count"])
    if usable_count < 30:
        continuity_score -= 1.0
        reasons.append("Usable observation count is low for a two-year interval.")
    elif usable_count < 60:
        continuity_score -= 0.5
        reasons.append("Usable observation count is acceptable but still somewhat thin.")
    else:
        reasons.append(f"Usable observation count is solid ({usable_count}).")

    if latest_season.confirmation_level == "weak":
        season_clarity_score -= 0.75
        reasons.append("Latest season has weak multi-index confirmation.")
    elif latest_season.confirmation_level == "moderate":
        season_clarity_score -= 0.25
        reasons.append("Latest season has moderate multi-index confirmation.")
    else:
        reasons.append("Latest season has strong multi-index confirmation.")

    if latest_season.quality_label == "weak":
        signal_strength_score -= 0.75
        reasons.append("Latest season quality is weak.")
    elif latest_season.quality_label == "interrupted":
        signal_strength_score -= 0.5
        reasons.append("Latest season shows interruption risk.")

    if latest_season.gap_overlap_risk == "high":
        continuity_score -= 0.5
        reasons.append(
            f"The latest season overlaps one or more long gap windows near {latest_season.gap_overlap_stage}."
        )
    elif latest_season.gap_overlap_risk == "moderate":
        continuity_score -= 0.25
        reasons.append(
            f"The latest season partially overlaps a long gap window near {latest_season.gap_overlap_stage}."
        )

    continuity_level = _score_to_level(continuity_score)
    season_clarity_level = _score_to_level(season_clarity_score)
    signal_strength_level = _score_to_level(signal_strength_score)
    final_score = min(continuity_score, season_clarity_score, signal_strength_score)

    if final_score >= 2.5:
        level = "high"
    elif final_score >= 1.5:
        level = "medium"
    else:
        level = "low"

    payload = build_confidence_payload(level, reasons)
    payload["components"] = {
        "continuity": continuity_level,
        "season_clarity": season_clarity_level,
        "signal_strength": signal_strength_level,
    }
    return payload


def _derive_satellite_evidence_coverage(quality_metrics: dict[str, Any]) -> dict[str, str]:
    gap_risk = str(quality_metrics["gap_risk"])
    usable_count = int(quality_metrics["usable_observation_count"])
    reason = str(quality_metrics.get("gap_risk_reason", "")).strip()

    if usable_count < 10:
        status = "insufficient"
        rationale = "Too few usable satellite observations for a complete automated assessment."
    elif gap_risk == "high" or usable_count < 30:
        status = "limited"
        rationale = reason or "Large observation gaps limit satellite evidence coverage."
    elif gap_risk == "moderate" or usable_count < 60:
        status = "fair"
        rationale = reason or "Some observation gaps are present, but evidence remains usable."
    else:
        status = "good"
        rationale = reason or "Satellite observations are continuous enough for the assessment window."

    return {"status": status, "rationale": rationale}


def _score_to_level(score: float) -> str:
    if score >= 2.5:
        return "high"
    if score >= 1.5:
        return "medium"
    return "low"


def _derive_risk_flags(
    quality_metrics: dict[str, Any],
    season_metrics: list[SeasonMetric],
    latest_season: SeasonMetric,
    *,
    land_status: str,
) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []

    if any(season.quality_label == "interrupted" for season in season_metrics):
        flags.append(
            build_risk_flag(
                "interruption_risk",
                "moderate",
                "At least one detected season shows interruption-like behavior.",
            )
        )

    if latest_season.quality_label == "weak":
        flags.append(
            build_risk_flag(
                "weak_activity_risk",
                "high",
                "The latest interpreted season is weak.",
            )
        )
    elif latest_season.peak_ndvi < 0.30:
        flags.append(
            build_risk_flag(
                "weak_activity_risk",
                "moderate",
                "The latest season peak NDVI stayed below the strong-growth band.",
            )
        )

    if latest_season.median_ndmi < 0.05:
        flags.append(
            build_risk_flag(
                "water_stress_risk",
                "moderate",
                f"Latest season median NDMI is low ({latest_season.median_ndmi:.3f}).",
            )
        )

    if latest_season.median_ndwi > -0.05:
        flags.append(
            build_risk_flag(
                "waterlogging_risk",
                "moderate",
                f"Latest season median NDWI is elevated ({latest_season.median_ndwi:.3f}).",
            )
        )

    if land_status == "inactive":
        flags.append(
            build_risk_flag(
                "possible_inactivity",
                "high",
                "Interval-level activity is too sparse for a stable active land classification.",
            )
        )
    elif land_status == "intermittent":
        flags.append(
            build_risk_flag(
                "possible_inactivity",
                "moderate",
                "Activity exists, but continuity is not strong enough for a stable active label.",
            )
        )

    if latest_season.is_open:
        flags.append(
            build_risk_flag(
                "provisional_latest_season",
                "low",
                "The latest season is still open at the right edge of the available series.",
            )
        )

    return flags


def build_land_assessment(
    *,
    run_metadata_path: Path,
    smoothed_csv_path: Path,
    quality_metrics_path: Path,
    season_payload_path: Path,
) -> dict[str, Any]:
    run_metadata = _load_json(run_metadata_path)
    quality_metrics = _validate_quality_metrics(_load_json(quality_metrics_path), quality_metrics_path)
    season_payload = _validate_season_payload(_load_json(season_payload_path), season_payload_path)
    observations = load_assessment_observations(smoothed_csv_path)
    season_metrics = _build_season_metrics(observations, list(season_payload["seasons"]))
    if not season_metrics:
        raise ValueError("Season payload did not produce usable season metrics for assessment.")

    active_fraction = _active_fraction(observations)
    land_status, land_status_basis = _derive_land_status(
        season_metrics,
        active_fraction=active_fraction,
        latest_timestamp=observations[-1].timestamp,
    )
    trend_2y, trend_basis = _derive_trend(season_metrics)
    latest_season_payload, latest_season = _latest_season_payload(season_metrics)
    confidence = _derive_confidence(quality_metrics, latest_season)
    satellite_evidence_coverage = _derive_satellite_evidence_coverage(quality_metrics)
    risk_flags = _derive_risk_flags(
        quality_metrics,
        season_metrics,
        latest_season,
        land_status=land_status,
    )

    return {
        "aoi_id": str(quality_metrics["aoi_id"]),
        "interval": {
            "start_date": str(run_metadata.get("start_date", observations[0].timestamp.date().isoformat())),
            "end_date": str(run_metadata.get("end_date", observations[-1].timestamp.date().isoformat())),
        },
        "land_status": land_status,
        "trend_2y": trend_2y,
        "season_count": int(season_payload["season_count"]),
        "latest_season_performance": latest_season_payload,
        "risk_flags": risk_flags,
        "satellite_evidence_coverage": satellite_evidence_coverage,
        "confidence": confidence,
        "evidence": {
            "land_status_basis": land_status_basis,
            "trend_basis": trend_basis,
            "latest_season_basis": latest_season.evidence_summary,
            "gap_note": str(quality_metrics.get("gap_risk_reason", "")),
        },
        "metrics_summary": {
            "usable_observation_count": int(quality_metrics["usable_observation_count"]),
            "gap_risk": str(quality_metrics["gap_risk"]),
            "long_gap_count": int(quality_metrics.get("long_gap_count", 0)),
            "long_gap_windows": quality_metrics.get("long_gap_windows", []),
            "active_observation_fraction": round(active_fraction, 4),
            "interval_max_ndvi": round(max(row.ndvi_smoothed for row in observations), 6),
            "interval_max_evi": round(max(row.evi_smoothed for row in observations), 6),
            "interval_median_ndmi": round(_median([row.ndmi_smoothed for row in observations]), 6),
            "interval_median_ndwi": round(_median([row.ndwi_smoothed for row in observations]), 6),
            "season_strength": [
                {
                    "season_id": season.season_id,
                    "peak_ndvi": season.peak_ndvi,
                    "auc_ndvi": season.auc_ndvi,
                    "peak_evi": season.peak_evi,
                    "median_ndmi": season.median_ndmi,
                    "median_ndwi": season.median_ndwi,
                    "quality_label": season.quality_label,
                    "confirmation_level": season.confirmation_level,
                    "is_open": season.is_open,
                    "gap_overlap_count": season.gap_overlap_count,
                    "gap_overlap_risk": season.gap_overlap_risk,
                    "gap_overlap_stage": season.gap_overlap_stage,
                }
                for season in season_metrics
            ],
        },
    }


def write_land_assessment(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "land_assessment.json"
    safe_write_text(output_path, json.dumps(payload, indent=2, sort_keys=True))
    return output_path
