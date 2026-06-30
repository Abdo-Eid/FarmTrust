"""Rule-based Phase A assessment helpers."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from farmtrust_core.ingest.utils import safe_write_text
from .evidence import build_confidence_payload, build_risk_flag


REQUIRED_PREPROCESS_COLUMNS = (
    "timestamp",
    "ndvi_smoothed",
    "ndvi_p95_raw",
    "ndvi_spread_raw",
    "evi_smoothed",
    "ndmi_smoothed",
    "ndwi_smoothed",
    "mndwi_smoothed",
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
COVERAGE_CONFIDENCE_CAPS = {
    "good": None,
    "fair": "medium",
    "limited": "low",
    "insufficient": "low",
}
CONFIDENCE_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
}
ABSENCE_MIN_WINDOW_DAYS = 180
ABSENCE_MIN_USABLE_OBSERVATIONS = 30
ABSENCE_MAX_GAP_DAYS = 45.0
ABSENCE_MAX_GAP_RATIO = 0.30
ABSENCE_LOW_NDVI_MAX = 0.25
ABSENCE_LOW_EVI_MAX = 0.20


@dataclass(frozen=True)
class AssessmentObservation:
    timestamp: datetime
    ndvi_smoothed: float
    ndvi_p95_raw: float
    ndvi_spread_raw: float
    evi_smoothed: float
    ndmi_smoothed: float
    ndwi_smoothed: float
    mndwi_smoothed: float


@dataclass(frozen=True)
class SeasonMetric:
    season_id: str
    start_date: date
    end_date: date
    peak_date: date
    quality_label: str
    confirmation_level: str
    is_open: bool
    provisional: bool
    duration_days: float
    peak_ndvi: float
    auc_ndvi: float
    peak_evi: float
    median_ndmi: float
    median_ndwi: float
    median_mndwi: float
    median_ndvi_spread: float
    peak_ndvi_p95: float
    evidence_summary: str
    gap_overlap_count: int
    gap_overlap_risk: str
    gap_overlap_stage: str
    lifecycle_status: str
    detection_status: str
    season_calendar_label: str = "unknown"


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _median(values: list[float]) -> float:
    ordered = sorted(value for value in values if math.isfinite(value))
    if not ordered:
        return float("nan")
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return float((ordered[middle - 1] + ordered[middle]) / 2.0)


def _max_finite(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return max(finite)


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
            if not row["ndvi_smoothed"].strip():
                continue
            observations.append(
                AssessmentObservation(
                    timestamp=_parse_timestamp(row["timestamp"]),
                    ndvi_smoothed=float(row["ndvi_smoothed"]),
                    ndvi_p95_raw=float(row["ndvi_p95_raw"]),
                    ndvi_spread_raw=float(row["ndvi_spread_raw"]),
                    evi_smoothed=float(row["evi_smoothed"]),
                    ndmi_smoothed=float(row["ndmi_smoothed"]),
                    ndwi_smoothed=float(row["ndwi_smoothed"]),
                    mndwi_smoothed=float(row["mndwi_smoothed"]),
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
                provisional=bool(season.get("provisional", season["is_open"])),
                duration_days=float(season["duration_days"]),
                peak_ndvi=float(season["peak_ndvi"]),
                auc_ndvi=round(_compute_auc(rows), 6),
                peak_evi=round(max(row.evi_smoothed for row in rows), 6),
                median_ndmi=round(_median([row.ndmi_smoothed for row in rows]), 6),
                median_ndwi=round(_median([row.ndwi_smoothed for row in rows]), 6),
                median_mndwi=round(_median([row.mndwi_smoothed for row in rows]), 6),
                median_ndvi_spread=round(_median([row.ndvi_spread_raw for row in rows]), 6),
                peak_ndvi_p95=round(_max_finite([row.ndvi_p95_raw for row in rows]), 6),
                evidence_summary=str(season["evidence_summary"]),
                gap_overlap_count=int(season.get("gap_overlap_count", 0)),
                gap_overlap_risk=str(season.get("gap_overlap_risk", "low")),
                gap_overlap_stage=str(season.get("gap_overlap_stage", "none")),
                lifecycle_status=str(season.get("lifecycle_status", "open_right" if season.get("is_open") else "complete")),
                detection_status=str(season.get("detection_status", "confirmed")),
                season_calendar_label=str(season.get("season_calendar_label", "unknown")),
            )
        )

    return metrics


def _activity_coverage_fraction(
    observations: list[AssessmentObservation],
    season_metrics: list[SeasonMetric],
) -> float:
    if not observations:
        return 0.0
    confirmed_windows = [season for season in season_metrics if season.detection_status == "confirmed"]
    active_count = sum(
        1
        for row in observations
        if any(season.start_date <= row.timestamp.date() <= season.end_date for season in confirmed_windows)
    )
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
    activity_coverage_fraction: float,
    latest_timestamp: datetime,
    absence_assessment: dict[str, Any],
) -> tuple[str | None, str]:
    if not season_metrics:
        if absence_assessment["status"] == "absence_supported":
            return "inactive", "No vegetation activity windows were detected and the absence gate supports a cautious inactive interpretation."
        return None, "No vegetation activity windows were detected, but the absence gate did not support an inactivity claim."

    recent_seasons = _recent_season_metrics(season_metrics, latest_timestamp=latest_timestamp)
    recent_good = sum(1 for season in recent_seasons if season.quality_label == "good")
    recent_any = len(recent_seasons)

    if recent_any >= 2 and recent_good >= 1 and activity_coverage_fraction >= 0.35:
        return (
            "active",
            f"{recent_any} recent vegetation activity windows were detected with activity_coverage_fraction={activity_coverage_fraction:.2f}.",
        )

    if recent_good >= 1 and activity_coverage_fraction >= 0.18:
        return (
            "active",
            f"A recent good vegetation activity window was detected with limited history (recent_windows={recent_any}, activity_coverage_fraction={activity_coverage_fraction:.2f}).",
        )

    if recent_any >= 1 and activity_coverage_fraction >= 0.18:
        return (
            "intermittent",
            f"Vegetation activity windows exist but continuity is weaker (recent_windows={recent_any}, activity_coverage_fraction={activity_coverage_fraction:.2f}).",
        )

    if absence_assessment["status"] != "absence_supported":
        return (
            None,
            f"Detected activity is sparse, but the absence gate did not support an inactive or idle interpretation (activity_coverage_fraction={activity_coverage_fraction:.2f}).",
        )

    return (
        "inactive",
        f"Detected activity is too sparse for a stable active classification (activity_coverage_fraction={activity_coverage_fraction:.2f}).",
    )


def _derive_trend(season_metrics: list[SeasonMetric]) -> tuple[str, str]:
    # `is_open` is True only for windows whose RIGHT edge is unobserved
    # (lifecycle open_right / open_both); these are excluded as trend references
    # because their end/peak may still be censored. An `open_left` window is NOT
    # is_open (it is a usable closed reference) but is still flagged provisional
    # via `lifecycle_status` / `start_boundary_certainty`. See seasons.py.
    reference = [season for season in season_metrics if not season.is_open]
    if len(reference) < 2:
        reference = season_metrics
    if len(reference) < 2:
        return "uncertain", "Trend needs at least two observed vegetation activity windows."

    first = reference[0]
    last = reference[-1]
    peak_delta = last.peak_ndvi - first.peak_ndvi
    auc_ratio = 0.0
    if first.auc_ndvi > 0:
        auc_ratio = (last.auc_ndvi - first.auc_ndvi) / first.auc_ndvi

    if peak_delta >= 0.03 or auc_ratio >= 0.10:
        return (
            "improving",
            f"Activity-window strength improved from peak_ndvi={first.peak_ndvi:.3f} to {last.peak_ndvi:.3f} with auc_ratio={auc_ratio:.2f}.",
        )
    if peak_delta <= -0.03 or auc_ratio <= -0.10:
        return (
            "declining",
            f"Activity-window strength declined from peak_ndvi={first.peak_ndvi:.3f} to {last.peak_ndvi:.3f} with auc_ratio={auc_ratio:.2f}.",
        )
    return (
        "stable",
        f"Activity-window strength stayed within conservative stability bounds (peak_delta={peak_delta:.3f}, auc_ratio={auc_ratio:.2f}).",
    )


def _latest_season_payload(season_metrics: list[SeasonMetric]) -> tuple[dict[str, Any], SeasonMetric]:
    # Prefer a closed reference cycle. `is_open` == right-edge unobserved only
    # (open_right / open_both); open_left counts as closed here. See seasons.py.
    closed = [season for season in season_metrics if not season.is_open]
    selected = closed[-1] if closed else season_metrics[-1]
    return (
        {
            "season_id": selected.season_id,
            "label": selected.quality_label,
            "provisional": selected.provisional,
            "confirmation_level": selected.confirmation_level,
            "evidence_summary": selected.evidence_summary,
        },
        selected,
    )


def _derive_confidence(
    quality_metrics: dict[str, Any],
    latest_season: SeasonMetric | None,
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
        reasons.append("Satellite evidence coverage is fair, so some activity-window interpretation remains cautious.")
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

    if latest_season is None:
        season_clarity_score -= 0.75
        signal_strength_score -= 0.75
        reasons.append("No vegetation activity window was detected in the observed interval.")
    elif latest_season.confirmation_level == "weak":
        season_clarity_score -= 0.75
        reasons.append("Latest activity window has weak multi-index confirmation.")
    elif latest_season.confirmation_level == "moderate":
        season_clarity_score -= 0.25
        reasons.append("Latest activity window has moderate multi-index confirmation.")
    else:
        reasons.append("Latest activity window has strong multi-index confirmation.")

    if latest_season is None:
        pass
    elif latest_season.quality_label == "weak":
        signal_strength_score -= 0.75
        reasons.append("Latest activity-window quality is weak.")
    elif latest_season.quality_label == "interrupted":
        signal_strength_score -= 0.5
        reasons.append("Latest activity window shows interruption-like observed signal behavior.")

    if latest_season is not None and latest_season.provisional:
        season_clarity_score -= 0.5
        reasons.append("Latest activity window has provisional boundaries because the cycle is incomplete or overlaps evidence gaps.")

    if latest_season is None:
        pass
    elif latest_season.gap_overlap_risk == "high":
        continuity_score -= 0.5
        reasons.append(
            f"The latest activity window overlaps one or more long observation gaps near {latest_season.gap_overlap_stage}."
        )
    elif latest_season.gap_overlap_risk == "moderate":
        continuity_score -= 0.25
        reasons.append(
            f"The latest activity window partially overlaps a long observation gap near {latest_season.gap_overlap_stage}."
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
        "activity_window_clarity": season_clarity_level,
        "signal_strength": signal_strength_level,
    }
    return payload


def _derive_satellite_evidence_coverage(quality_metrics: dict[str, Any]) -> dict[str, str]:
    gap_risk = str(quality_metrics["gap_risk"])
    usable_count = int(quality_metrics["usable_observation_count"])
    gap_ratio = float(quality_metrics.get("gap_ratio", 0.0))
    max_gap_days = float(quality_metrics.get("max_gap_days", 0.0))
    long_gap_count = int(quality_metrics.get("long_gap_count", 0))
    reason = str(quality_metrics.get("gap_risk_reason", "")).strip()

    if usable_count < 12:
        status = "insufficient"
        rationale = "Too few usable satellite observations for a complete automated assessment."
    elif gap_ratio > 0.60:
        status = "insufficient"
        rationale = "Satellite evidence gaps dominate the assessment window."
    elif max_gap_days > 90:
        status = "insufficient"
        rationale = "A very long satellite observation gap prevents a complete automated assessment."
    elif long_gap_count > 12:
        status = "insufficient"
        rationale = "Too many long satellite observation gaps prevent a complete automated assessment."
    elif usable_count < 30:
        status = "limited"
        rationale = "Usable satellite observations are sparse, so automated interpretation is limited."
    elif gap_risk == "high":
        status = "limited"
        rationale = reason or "Large observation gaps limit satellite evidence coverage."
    elif gap_ratio > 0.30:
        status = "limited"
        rationale = "Satellite evidence gaps limit automated interpretation."
    elif max_gap_days > 45:
        status = "limited"
        rationale = "A long satellite observation gap limits automated interpretation."
    elif long_gap_count > 6:
        status = "limited"
        rationale = "Frequent long satellite observation gaps limit automated interpretation."
    elif usable_count < 60:
        status = "fair"
        rationale = "Usable satellite observations are adequate but thinner than preferred."
    elif gap_risk == "moderate":
        status = "fair"
        rationale = reason or "Some observation gaps are present, but evidence remains usable."
    elif gap_ratio > 0.15:
        status = "fair"
        rationale = "Some satellite evidence gaps are present, but evidence remains usable."
    elif max_gap_days > 10:
        status = "fair"
        rationale = "A moderate satellite observation gap is present, but evidence remains usable."
    elif long_gap_count > 0:
        status = "fair"
        rationale = "One or more satellite observation gaps are present, but evidence remains usable."
    else:
        status = "good"
        rationale = reason or "Satellite observations are continuous enough for the assessment window."

    return {"status": status, "rationale": rationale}


def _derive_history_coverage(
    observations: list[AssessmentObservation],
    season_metrics: list[SeasonMetric],
) -> dict[str, Any]:
    observed_count = len(season_metrics)
    complete_count = sum(1 for season in season_metrics if not season.is_open)
    interval_days = 0
    if len(observations) >= 2:
        interval_days = max(0, (observations[-1].timestamp.date() - observations[0].timestamp.date()).days)

    if observed_count == 0:
        status = "insufficient_history"
        rationale = "No vegetation activity cycles were observed, so activity history could not be established."
    elif observed_count < 2 or complete_count < 1:
        status = "limited_history"
        rationale = "Only one vegetation activity cycle, or no complete cycle, was observed; do not infer long-term stability or trend."
    else:
        status = "sufficient_history"
        rationale = "Multiple vegetation activity cycles were observed in the assessment interval."

    return {
        "status": status,
        "rationale": rationale,
        "observed_activity_cycle_count": observed_count,
        "complete_activity_cycle_count": complete_count,
        "assessment_interval_days": interval_days,
    }


def _derive_absence_assessment(
    quality_metrics: dict[str, Any],
    observations: list[AssessmentObservation],
    season_metrics: list[SeasonMetric],
    satellite_evidence_coverage: dict[str, str],
) -> dict[str, str]:
    if season_metrics:
        return {
            "status": "activity_present",
            "rationale": "At least one vegetation activity cycle was detected; absence was not claimed.",
        }

    if not observations:
        return {
            "status": "not_assessed",
            "rationale": "No observations were available for an absence assessment.",
        }

    usable_count = int(quality_metrics["usable_observation_count"])
    gap_ratio = float(quality_metrics.get("gap_ratio", 0.0))
    max_gap_days = float(quality_metrics.get("max_gap_days", 0.0))
    interval_days = max(0, (observations[-1].timestamp.date() - observations[0].timestamp.date()).days)
    coverage_status = satellite_evidence_coverage["status"]

    if coverage_status == "insufficient" or usable_count < 12:
        return {
            "status": "insufficient_evidence",
            "rationale": "Satellite evidence is insufficient, so absence or inactivity cannot be assessed safely.",
        }

    if interval_days < ABSENCE_MIN_WINDOW_DAYS:
        return {
            "status": "not_assessed",
            "rationale": f"The assessment window is too short for a safe absence claim (interval_days={interval_days}).",
        }

    if usable_count < ABSENCE_MIN_USABLE_OBSERVATIONS or gap_ratio > ABSENCE_MAX_GAP_RATIO or max_gap_days > ABSENCE_MAX_GAP_DAYS:
        return {
            "status": "insufficient_evidence",
            "rationale": "Observation density or gaps are not strong enough to support an absence claim.",
        }

    max_ndvi = max(row.ndvi_smoothed for row in observations)
    max_evi = max(row.evi_smoothed for row in observations)
    if max_ndvi <= ABSENCE_LOW_NDVI_MAX and max_evi <= ABSENCE_LOW_EVI_MAX:
        return {
            "status": "absence_supported",
            "rationale": f"No activity cycle was detected, evidence coverage is adequate, and vegetation signal stayed low (max_ndvi={max_ndvi:.2f}, max_evi={max_evi:.2f}).",
        }

    return {
        "status": "absence_uncertain",
        "rationale": f"No activity cycle was detected, but vegetation signal was not consistently low enough for a safe absence claim (max_ndvi={max_ndvi:.2f}, max_evi={max_evi:.2f}).",
    }


def _derive_assessment_status(satellite_evidence_coverage: dict[str, str]) -> str:
    if satellite_evidence_coverage["status"] == "insufficient":
        return "manual_review_required"
    return "complete"


def _cap_confidence_by_coverage(
    confidence: dict[str, Any],
    satellite_evidence_coverage: dict[str, str],
) -> dict[str, Any]:
    capped = dict(confidence)
    reasons = list(capped.get("reasons", []))
    coverage_status = satellite_evidence_coverage["status"]
    cap = COVERAGE_CONFIDENCE_CAPS[coverage_status]
    if cap is None:
        capped["reasons"] = reasons
        return capped

    current_level = str(capped.get("level", "medium"))
    if CONFIDENCE_RANK[current_level] > CONFIDENCE_RANK[cap]:
        capped["level"] = cap
        reasons.append(
            f"Assessment confidence is capped at {cap} because satellite evidence coverage is {coverage_status}."
        )
    elif coverage_status == "insufficient" and current_level != "low":
        capped["level"] = "low"
        reasons.append("Assessment confidence is low because satellite evidence is insufficient.")
    elif coverage_status == "insufficient":
        reasons.append("Satellite evidence is insufficient, so automated assessment requires manual review.")

    components = capped.get("components")
    if isinstance(components, dict):
        components = dict(components)
        if coverage_status == "fair" and components.get("continuity") == "high":
            components["continuity"] = "medium"
        elif coverage_status in {"limited", "insufficient"}:
            components["continuity"] = "low"
        capped["components"] = components

    capped["reasons"] = reasons
    return capped


def _score_to_level(score: float) -> str:
    if score >= 2.5:
        return "high"
    if score >= 1.5:
        return "medium"
    return "low"


def _derive_risk_flags(
    quality_metrics: dict[str, Any],
    season_metrics: list[SeasonMetric],
    latest_season: SeasonMetric | None,
    *,
    land_status: str | None,
    absence_assessment: dict[str, str],
) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []

    if any(season.quality_label == "interrupted" for season in season_metrics):
        flags.append(
            build_risk_flag(
                "interruption_risk",
                "moderate",
                "At least one detected vegetation activity window shows interruption-like observed signal behavior.",
            )
        )

    if latest_season is not None and latest_season.quality_label == "weak":
        flags.append(
            build_risk_flag(
                "weak_activity_risk",
                "high",
                "The latest interpreted vegetation activity window is weak.",
            )
        )
    elif latest_season is not None and latest_season.provisional:
        flags.append(
            build_risk_flag(
                "weak_activity_risk",
                "moderate",
                "The latest activity window is provisional, so final strength is not yet established.",
            )
        )

    if land_status == "inactive" and absence_assessment["status"] == "absence_supported":
        flags.append(
            build_risk_flag(
                "possible_inactivity",
                "high",
                "No vegetation activity cycle was detected and the absence gate supports a cautious inactivity interpretation.",
            )
        )
    elif land_status == "intermittent":
        flags.append(
            build_risk_flag(
                "limited_activity_continuity",
                "moderate",
                "Activity exists, but continuity is not strong enough for a stable active label.",
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

    activity_coverage_fraction = _activity_coverage_fraction(observations, season_metrics)
    satellite_evidence_coverage = _derive_satellite_evidence_coverage(quality_metrics)
    absence_assessment = _derive_absence_assessment(
        quality_metrics,
        observations,
        season_metrics,
        satellite_evidence_coverage,
    )
    history_coverage = _derive_history_coverage(observations, season_metrics)
    land_status, land_status_basis = _derive_land_status(
        season_metrics,
        activity_coverage_fraction=activity_coverage_fraction,
        latest_timestamp=observations[-1].timestamp,
        absence_assessment=absence_assessment,
    )
    trend_2y, trend_basis = _derive_trend(season_metrics)
    if season_metrics:
        latest_season_payload, latest_season = _latest_season_payload(season_metrics)
    else:
        latest_season_payload = None
        latest_season = None
    assessment_status = _derive_assessment_status(satellite_evidence_coverage)
    confidence = _cap_confidence_by_coverage(
        _derive_confidence(quality_metrics, latest_season),
        satellite_evidence_coverage,
    )
    risk_flags = _derive_risk_flags(
        quality_metrics,
        season_metrics,
        latest_season,
        land_status=land_status,
        absence_assessment=absence_assessment,
    )
    if assessment_status == "manual_review_required":
        land_status = None
        land_status_basis = "Satellite evidence is insufficient for a final automated land-status assessment."
        trend_2y = None
        trend_basis = "Satellite evidence is insufficient for a final automated trend assessment."
        latest_season_payload = None
        risk_flags = []

    return {
        "aoi_id": str(quality_metrics["aoi_id"]),
        "assessment_status": assessment_status,
        "interval": {
            "start_date": str(run_metadata.get("start_date", observations[0].timestamp.date().isoformat())),
            "end_date": str(run_metadata.get("end_date", observations[-1].timestamp.date().isoformat())),
        },
        "land_status": land_status,
        "trend_2y": trend_2y,
        "history_coverage": history_coverage,
        "absence_assessment": absence_assessment,
        "season_count": int(season_payload["season_count"]),
        "latest_season_performance": latest_season_payload,
        "risk_flags": risk_flags,
        "satellite_evidence_coverage": satellite_evidence_coverage,
        "confidence": confidence,
        "evidence": {
            "land_status_basis": land_status_basis,
            "history_coverage_basis": history_coverage["rationale"],
            "absence_assessment_basis": absence_assessment["rationale"],
            "trend_basis": trend_basis,
            "latest_season_basis": latest_season.evidence_summary
            if latest_season is not None
            else "No vegetation activity window was detected in the observed interval.",
            "gap_note": str(quality_metrics.get("gap_risk_reason", "")),
        },
        "metrics_summary": {
            "usable_observation_count": int(quality_metrics["usable_observation_count"]),
            "gap_risk": str(quality_metrics["gap_risk"]),
            "long_gap_count": int(quality_metrics.get("long_gap_count", 0)),
            "long_gap_windows": quality_metrics.get("long_gap_windows", []),
            "active_observation_fraction": round(activity_coverage_fraction, 4),
            "activity_coverage_fraction": round(activity_coverage_fraction, 4),
            "interval_max_ndvi": round(max(row.ndvi_smoothed for row in observations), 6),
            "interval_max_ndvi_p95": round(_max_finite([row.ndvi_p95_raw for row in observations]), 6),
            "interval_median_ndvi_spread": round(_median([row.ndvi_spread_raw for row in observations]), 6),
            "interval_max_evi": round(max(row.evi_smoothed for row in observations), 6),
            "interval_median_ndmi": round(_median([row.ndmi_smoothed for row in observations]), 6),
            "interval_median_ndwi": round(_median([row.ndwi_smoothed for row in observations]), 6),
            "interval_median_mndwi": round(_median([row.mndwi_smoothed for row in observations]), 6),
            "season_strength": [
                {
                    "season_id": season.season_id,
                    "peak_ndvi": season.peak_ndvi,
                    "auc_ndvi": season.auc_ndvi,
                    "peak_evi": season.peak_evi,
                    "median_ndmi": season.median_ndmi,
                    "median_ndwi": season.median_ndwi,
                    "median_mndwi": season.median_mndwi,
                    "median_ndvi_spread": season.median_ndvi_spread,
                    "peak_ndvi_p95": season.peak_ndvi_p95,
                    "quality_label": season.quality_label,
                    "confirmation_level": season.confirmation_level,
                    "is_open": season.is_open,
                    "provisional": season.provisional,
                    "gap_overlap_count": season.gap_overlap_count,
                    "gap_overlap_risk": season.gap_overlap_risk,
                    "gap_overlap_stage": season.gap_overlap_stage,
                    "lifecycle_status": season.lifecycle_status,
                    "detection_status": season.detection_status,
                    "season_calendar_label": season.season_calendar_label,
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
