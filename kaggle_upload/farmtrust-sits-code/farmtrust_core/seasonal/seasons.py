"""Vegetation activity-window detection utilities.

The durable output file still uses season-oriented field names for API
compatibility. In this module, a "season" record means a detected vegetation
activity window from satellite observations, not an agronomic crop season.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from pathlib import Path
from typing import Any, Optional

from farmtrust_core.ingest.utils import safe_write_text


REQUIRED_PREPROCESS_COLUMNS = (
    "timestamp",
    "ndvi_smoothed",
    "evi_smoothed",
    "ndmi_smoothed",
    "ndwi_smoothed",
    "is_usable",
    "valid_fraction",
    "source_row_count",
)
REQUIRED_QUALITY_KEYS = (
    "aoi_id",
    "usable_observation_count",
    "gap_ratio",
    "max_gap_days",
    "gap_risk",
)

BASELINE_METHOD = "local_p20_smoothed_ndvi"
BASELINE_WINDOW_DAYS = 90.0
BASELINE_PERCENTILE = 20.0
MIN_LOCAL_BASELINE_OBSERVATIONS = 5
PEAK_METHOD = "max_smoothed_ndvi_in_candidate_window"
ACTIVITY_BOUNDARY_AMPLITUDE_FRACTION = 0.35
LOW_VEGETATION_FLOOR = 0.18
ACTIVITY_THRESHOLD = LOW_VEGETATION_FLOOR
MIN_ACTIVITY_AMPLITUDE = 0.08
GOOD_ACTIVITY_AMPLITUDE = 0.12
MIN_ACTIVITY_WINDOW_DURATION_DAYS = 20.0
MIN_ACTIVITY_WINDOW_OBSERVATIONS = 4
GOOD_PEAK_THRESHOLD = 0.30
INTERRUPTED_DROP_THRESHOLD = 0.05
EVI_CONFIRMATION_MIN = 0.20
NDMI_CONFIRMATION_MIN = 0.05
NDWI_CONFIRMATION_MAX = 0.20


@dataclass(frozen=True)
class SeasonalObservation:
    timestamp: datetime
    ndvi_smoothed: float
    evi_smoothed: float
    ndmi_smoothed: float
    ndwi_smoothed: float
    valid_fraction: float
    source_row_count: int


@dataclass(frozen=True)
class SeasonWindow:
    season_id: str
    crossing_date: str
    start_date: str
    peak_date: str
    end_date: str
    is_open: bool
    peak_ndvi: float
    duration_days: float
    quality_label: str
    evidence_summary: str
    confirmation_level: str
    gap_overlap_count: int
    gap_overlap_risk: str
    gap_overlap_stage: str
    window_type: str
    provisional: bool
    baseline_ndvi: float
    amplitude_ndvi: float
    boundary_threshold_ndvi: float
    usable_observation_count: int
    start_boundary_certainty: str
    peak_certainty: str
    end_boundary_certainty: str
    internal_gap_count: int


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_date(value: datetime) -> str:
    return value.astimezone(timezone.utc).date().isoformat()


def _load_quality_metrics(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing_keys = [key for key in REQUIRED_QUALITY_KEYS if key not in data]
    if missing_keys:
        raise ValueError(f"Quality metrics missing required keys {missing_keys}: {path}")
    return data


def _build_season_confidence_note(quality_metrics: dict[str, Any]) -> str:
    gap_risk = str(quality_metrics["gap_risk"])
    reason = str(quality_metrics.get("gap_risk_reason", "")).strip()
    if reason:
        return f"Gap risk is {gap_risk}. {reason}"
    return f"Gap risk is {gap_risk}."


def _parse_gap_windows(quality_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    windows = quality_metrics.get("long_gap_windows", [])
    if not isinstance(windows, list):
        return []
    return [window for window in windows if isinstance(window, dict)]


def load_preprocess_observations(csv_path: Path) -> list[SeasonalObservation]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {csv_path}")

        missing_columns = [column for column in REQUIRED_PREPROCESS_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"Preprocess CSV is missing required columns {missing_columns}: {csv_path}"
            )

        observations: list[SeasonalObservation] = []
        for row in reader:
            if row["is_usable"].strip().lower() != "true":
                continue
            if not row["ndvi_smoothed"].strip():
                continue
            if not row["evi_smoothed"].strip():
                continue
            if not row["ndmi_smoothed"].strip():
                continue
            if not row["ndwi_smoothed"].strip():
                continue

            observations.append(
                SeasonalObservation(
                    timestamp=_parse_timestamp(row["timestamp"]),
                    ndvi_smoothed=float(row["ndvi_smoothed"]),
                    evi_smoothed=float(row["evi_smoothed"]),
                    ndmi_smoothed=float(row["ndmi_smoothed"]),
                    ndwi_smoothed=float(row["ndwi_smoothed"]),
                    valid_fraction=float(row["valid_fraction"]),
                    source_row_count=int(row["source_row_count"]),
                )
            )

    if not observations:
        raise ValueError(f"No usable smoothed observations found in {csv_path}")

    observations.sort(key=lambda row: row.timestamp)
    return observations


def compute_activity_threshold(
    observations: list[SeasonalObservation],
    *,
    activity_threshold: float = ACTIVITY_THRESHOLD,
) -> float:
    if not observations:
        raise ValueError("Cannot compute activity threshold without observations")
    return activity_threshold


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile without values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])

    rank = (percentile / 100.0) * (len(ordered) - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = rank - lower_index
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    return float(lower_value + (upper_value - lower_value) * fraction)


def compute_local_baselines(observations: list[SeasonalObservation]) -> list[float]:
    if not observations:
        return []

    global_baseline = _percentile(
        [row.ndvi_smoothed for row in observations],
        BASELINE_PERCENTILE,
    )
    baselines: list[float] = []
    for observation in observations:
        local_values = [
            candidate.ndvi_smoothed
            for candidate in observations
            if abs((candidate.timestamp - observation.timestamp).total_seconds()) / 86400.0
            <= BASELINE_WINDOW_DAYS
        ]
        if len(local_values) >= MIN_LOCAL_BASELINE_OBSERVATIONS:
            baselines.append(_percentile(local_values, BASELINE_PERCENTILE))
        else:
            baselines.append(global_baseline)
    return baselines


def _segment_active_periods(
    observations: list[SeasonalObservation],
    *,
    activity_threshold: float,
) -> list[tuple[int, list[SeasonalObservation]]]:
    segments: list[tuple[int, list[SeasonalObservation]]] = []
    current: list[SeasonalObservation] = []
    current_start_index: int | None = None

    for index, observation in enumerate(observations):
        if observation.ndvi_smoothed >= activity_threshold:
            if not current:
                current_start_index = index
            current.append(observation)
        elif current:
            assert current_start_index is not None
            segments.append((current_start_index, current))
            current = []
            current_start_index = None

    if current:
        assert current_start_index is not None
        segments.append((current_start_index, current))

    return segments


def _duration_days(observations: list[SeasonalObservation]) -> float:
    start = observations[0].timestamp
    end = observations[-1].timestamp
    return max(0.0, (end - start).total_seconds() / 86400.0)


def _max_single_step_drop(values: list[float]) -> float:
    drops = [left - right for left, right in zip(values[:-1], values[1:]) if right < left]
    if not drops:
        return 0.0
    return max(drops)


def _label_quality(
    segment: list[SeasonalObservation],
    *,
    baseline_ndvi: float,
    amplitude_ndvi: float,
    is_open: bool = False,
) -> tuple[str, str, str]:
    values = [row.ndvi_smoothed for row in segment]
    peak_row = max(segment, key=lambda row: row.ndvi_smoothed)
    peak_ndvi = peak_row.ndvi_smoothed
    duration_days = _duration_days(segment)
    max_drop = _max_single_step_drop(values)

    if duration_days < MIN_ACTIVITY_WINDOW_DURATION_DAYS or amplitude_ndvi < GOOD_ACTIVITY_AMPLITUDE:
        label = (
            "weak",
            (
                "Weak vegetation activity window: "
                f"peak_ndvi={peak_ndvi:.3f}, baseline_ndvi={baseline_ndvi:.3f}, "
                f"amplitude_ndvi={amplitude_ndvi:.3f}, duration_days={duration_days:.1f}."
            ),
        )
        quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
        return quality_label, evidence_summary, "weak"

    if max_drop >= INTERRUPTED_DROP_THRESHOLD:
        label = (
            "interrupted",
            f"Interrupted vegetation activity window: peak_ndvi={peak_ndvi:.3f}, max_drop={max_drop:.3f}.",
        )
        quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
        return quality_label, evidence_summary, "moderate"

    if peak_ndvi >= GOOD_PEAK_THRESHOLD and amplitude_ndvi >= GOOD_ACTIVITY_AMPLITUDE:
        label = (
            "good",
            (
                "Good vegetation activity window: "
                f"peak_ndvi={peak_ndvi:.3f}, baseline_ndvi={baseline_ndvi:.3f}, "
                f"amplitude_ndvi={amplitude_ndvi:.3f}."
            ),
        )
        quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
        return quality_label, evidence_summary, "strong"

    label = (
        "weak",
        (
            "Weak vegetation activity window: "
            f"peak_ndvi={peak_ndvi:.3f}, baseline_ndvi={baseline_ndvi:.3f}, "
            f"amplitude_ndvi={amplitude_ndvi:.3f}."
        ),
    )
    quality_label, evidence_summary = _append_open_note(label, is_open=is_open)
    return quality_label, evidence_summary, "weak"


def _append_open_note(
    label: tuple[str, str],
    *,
    is_open: bool,
) -> tuple[str, str]:
    if not is_open:
        return label

    quality_label, evidence_summary = label
    return quality_label, f"{evidence_summary[:-1]} Still active at end of available observations; boundary is provisional."


def _compute_multi_index_confirmation(segment: list[SeasonalObservation]) -> tuple[str, str]:
    evi_peak = max(row.evi_smoothed for row in segment)
    ndmi_median = float(median(row.ndmi_smoothed for row in segment))
    ndwi_median = float(median(row.ndwi_smoothed for row in segment))

    checks = [
        evi_peak >= EVI_CONFIRMATION_MIN,
        ndmi_median >= NDMI_CONFIRMATION_MIN,
        ndwi_median <= NDWI_CONFIRMATION_MAX,
    ]
    support_count = sum(1 for flag in checks if flag)
    if support_count == 3:
        level = "strong"
    elif support_count == 2:
        level = "moderate"
    else:
        level = "weak"

    evidence = (
        f"Multi-index confirmation={level} "
        f"(evi_peak={evi_peak:.3f}, ndmi_median={ndmi_median:.3f}, ndwi_median={ndwi_median:.3f})."
    )
    return level, evidence


def _apply_confirmation_adjustment(
    *,
    quality_label: str,
    base_evidence: str,
    base_level: str,
    confirmation_level: str,
    confirmation_evidence: str,
) -> tuple[str, str]:
    adjusted_label = quality_label
    if confirmation_level == "weak":
        adjusted_label = "weak"
    elif quality_label == "interrupted" and confirmation_level == "strong" and base_level == "moderate":
        adjusted_label = "good"

    return adjusted_label, f"{base_evidence} {confirmation_evidence}"


def _compute_gap_overlap(
    season_observations: list[SeasonalObservation],
    long_gap_windows: list[dict[str, Any]],
) -> tuple[int, str, str, str, str, str, str, int, bool]:
    if not season_observations or not long_gap_windows:
        return 0, "low", "none", "No long gaps overlap this activity window.", "clear", "clear", "clear", 0, False

    season_start = season_observations[0].timestamp
    season_end = season_observations[-1].timestamp
    season_span_days = max((season_end - season_start).total_seconds() / 86400.0, 1.0)
    onset_end = season_start + (season_end - season_start) / 3
    tail_start = season_end - (season_end - season_start) / 3
    peak_row = max(season_observations, key=lambda row: row.ndvi_smoothed)
    peak_half_window_days = max(6.0, season_span_days / 6.0)
    peak_start = peak_row.timestamp - timedelta(days=peak_half_window_days)
    peak_end = peak_row.timestamp + timedelta(days=peak_half_window_days)
    overlapping: list[dict[str, Any]] = []
    touched_stages: set[str] = set()
    internal_gap_count = 0

    for window in long_gap_windows:
        start_value = window.get("start_timestamp")
        end_value = window.get("end_timestamp")
        if not isinstance(start_value, str) or not isinstance(end_value, str):
            continue

        gap_start = _parse_timestamp(start_value)
        gap_end = _parse_timestamp(end_value)
        if gap_start <= season_end and gap_end >= season_start:
            overlapping.append(window)
            if gap_start < onset_end and gap_end >= season_start:
                touched_stages.add("onset")
            if gap_start <= peak_end and gap_end >= peak_start:
                touched_stages.add("peak")
            if gap_start <= season_end and gap_end > tail_start:
                touched_stages.add("tail")
            touches_middle = (
                gap_start > onset_end
                and gap_end < tail_start
                and not (gap_start <= peak_end and gap_end >= peak_start)
            )
            if touches_middle:
                touched_stages.add("middle")
                internal_gap_count += 1

    overlap_count = len(overlapping)
    if overlap_count == 0:
        return 0, "low", "none", "No long gaps overlap this activity window.", "clear", "clear", "clear", 0, False

    max_overlap_gap_days = max(float(window.get("gap_days", 0.0)) for window in overlapping)
    if len(touched_stages) > 1:
        dominant_stage = "multiple"
    elif touched_stages:
        for candidate in ("onset", "peak", "tail", "middle"):
            if candidate in touched_stages:
                dominant_stage = candidate
                break
        else:
            dominant_stage = "middle"
    else:
        dominant_stage = "middle"

    if "onset" in touched_stages or "peak" in touched_stages:
        overlap_risk = "high"
    elif overlap_count >= 2 or max_overlap_gap_days > 15.0:
        overlap_risk = "high"
    else:
        overlap_risk = "moderate"

    start_boundary_certainty = "limited" if "onset" in touched_stages else "clear"
    peak_certainty = "limited" if "peak" in touched_stages else "clear"
    end_boundary_certainty = "limited" if "tail" in touched_stages else "clear"
    provisional = start_boundary_certainty == "limited" or end_boundary_certainty == "limited"

    return (
        overlap_count,
        overlap_risk,
        dominant_stage,
        (
            f"{overlap_count} long gap window(s) overlap this activity window "
            f"(stage={dominant_stage}, max_gap_days={max_overlap_gap_days:.1f}, span_days={season_span_days:.1f})."
        ),
        start_boundary_certainty,
        peak_certainty,
        end_boundary_certainty,
        internal_gap_count,
        provisional,
    )


def _is_left_edge_partial_tail(
    observations: list[SeasonalObservation],
    crossing_index: int,
    season_observations: list[SeasonalObservation],
) -> bool:
    if crossing_index != 0:
        return False
    if not season_observations:
        return False

    peak_row = max(season_observations, key=lambda row: row.ndvi_smoothed)
    first_row = season_observations[0]
    return peak_row.timestamp == first_row.timestamp


def detect_season_windows(
    observations: list[SeasonalObservation],
    *,
    activity_threshold: float = ACTIVITY_THRESHOLD,
    long_gap_windows: Optional[list[dict[str, Any]]] = None,
) -> list[SeasonWindow]:
    seasons: list[SeasonWindow] = []
    long_gap_windows = long_gap_windows or []
    activity_threshold = compute_activity_threshold(
        observations,
        activity_threshold=activity_threshold,
    )
    baselines = compute_local_baselines(observations)
    segments = _segment_active_periods(observations, activity_threshold=activity_threshold)

    used_ranges: list[tuple[int, int]] = []

    for crossing_index, segment in segments:
        segment_start_index = crossing_index
        segment_end_index = crossing_index + len(segment) - 1
        candidate_peak_indices = [
            index
            for index in range(segment_start_index, segment_end_index + 1)
            if observations[index].ndvi_smoothed - baselines[index] >= MIN_ACTIVITY_AMPLITUDE
        ]
        candidate_peak_indices.sort(key=lambda index: observations[index].ndvi_smoothed, reverse=True)

        for peak_index in candidate_peak_indices:
            if any(start <= peak_index <= end for start, end in used_ranges):
                continue

            peak_row = observations[peak_index]
            baseline_ndvi = baselines[peak_index]
            amplitude_ndvi = peak_row.ndvi_smoothed - baseline_ndvi
            boundary_threshold = max(
                LOW_VEGETATION_FLOOR,
                baseline_ndvi + ACTIVITY_BOUNDARY_AMPLITUDE_FRACTION * amplitude_ndvi,
            )
            start_index = peak_index
            while (
                start_index > segment_start_index
                and observations[start_index - 1].ndvi_smoothed >= boundary_threshold
            ):
                start_index -= 1

            end_index = peak_index
            while (
                end_index < segment_end_index
                and observations[end_index + 1].ndvi_smoothed >= boundary_threshold
            ):
                end_index += 1

            if any(not (end_index < start or start_index > end) for start, end in used_ranges):
                continue

            season_observations = observations[start_index : end_index + 1]
            is_open = end_index == len(observations) - 1

            if _is_left_edge_partial_tail(observations, start_index, season_observations):
                continue

            duration_days = _duration_days(season_observations)
            if len(season_observations) < MIN_ACTIVITY_WINDOW_OBSERVATIONS:
                continue
            if duration_days < MIN_ACTIVITY_WINDOW_DURATION_DAYS:
                continue

            break
        else:
            continue

        used_ranges.append((start_index, end_index))
        peak_row = max(season_observations, key=lambda row: row.ndvi_smoothed)
        quality_label, evidence_summary, base_level = _label_quality(
            season_observations,
            baseline_ndvi=baseline_ndvi,
            amplitude_ndvi=amplitude_ndvi,
            is_open=is_open,
        )
        confirmation_level, confirmation_evidence = _compute_multi_index_confirmation(season_observations)
        quality_label, evidence_summary = _apply_confirmation_adjustment(
            quality_label=quality_label,
            base_evidence=evidence_summary,
            base_level=base_level,
            confirmation_level=confirmation_level,
            confirmation_evidence=confirmation_evidence,
        )
        (
            gap_overlap_count,
            gap_overlap_risk,
            gap_overlap_stage,
            gap_overlap_evidence,
            start_boundary_certainty,
            peak_certainty,
            end_boundary_certainty,
            internal_gap_count,
            gap_provisional,
        ) = _compute_gap_overlap(
            season_observations,
            long_gap_windows,
        )
        if is_open:
            end_boundary_certainty = "open"
        provisional = is_open or gap_provisional
        evidence_summary = f"{evidence_summary} {gap_overlap_evidence}"

        seasons.append(
            SeasonWindow(
                season_id=f"season_{len(seasons) + 1:02d}",
                crossing_date=_iso_date(observations[start_index].timestamp),
                start_date=_iso_date(season_observations[0].timestamp),
                peak_date=_iso_date(peak_row.timestamp),
                end_date=_iso_date(season_observations[-1].timestamp),
                is_open=is_open,
                peak_ndvi=round(peak_row.ndvi_smoothed, 6),
                duration_days=round(duration_days, 2),
                quality_label=quality_label,
                evidence_summary=evidence_summary,
                confirmation_level=confirmation_level,
                gap_overlap_count=gap_overlap_count,
                gap_overlap_risk=gap_overlap_risk,
                gap_overlap_stage=gap_overlap_stage,
                window_type="vegetation_activity",
                provisional=provisional,
                baseline_ndvi=round(baseline_ndvi, 6),
                amplitude_ndvi=round(amplitude_ndvi, 6),
                boundary_threshold_ndvi=round(boundary_threshold, 6),
                usable_observation_count=len(season_observations),
                start_boundary_certainty=start_boundary_certainty,
                peak_certainty=peak_certainty,
                end_boundary_certainty=end_boundary_certainty,
                internal_gap_count=internal_gap_count,
            )
        )

    return seasons


def build_season_payload(
    smoothed_csv_path: Path,
    quality_metrics_path: Path,
) -> dict[str, Any]:
    quality_metrics = _load_quality_metrics(quality_metrics_path)
    observations = load_preprocess_observations(smoothed_csv_path)
    long_gap_windows = _parse_gap_windows(quality_metrics)
    seasons = detect_season_windows(observations, long_gap_windows=long_gap_windows)
    season_confidence_note = _build_season_confidence_note(quality_metrics)

    return {
        "aoi_id": quality_metrics["aoi_id"],
        "season_count": len(seasons),
        "gap_risk": quality_metrics["gap_risk"],
        "terminology": {
            "season": "detected vegetation activity window, not an agronomic crop season",
        },
        "seasons": [
            {
                "season_id": season.season_id,
                "crossing_date": season.crossing_date,
                "start_date": season.start_date,
                "peak_date": season.peak_date,
                "end_date": season.end_date,
                "is_open": season.is_open,
                "peak_ndvi": season.peak_ndvi,
                "duration_days": season.duration_days,
                "quality_label": season.quality_label,
                "evidence_summary": season.evidence_summary,
                "confirmation_level": season.confirmation_level,
                "gap_overlap_count": season.gap_overlap_count,
                "gap_overlap_risk": season.gap_overlap_risk,
                "gap_overlap_stage": season.gap_overlap_stage,
                "window_type": season.window_type,
                "provisional": season.provisional,
                "baseline_ndvi": season.baseline_ndvi,
                "amplitude_ndvi": season.amplitude_ndvi,
                "boundary_threshold_ndvi": season.boundary_threshold_ndvi,
                "usable_observation_count": season.usable_observation_count,
                "start_boundary_certainty": season.start_boundary_certainty,
                "peak_certainty": season.peak_certainty,
                "end_boundary_certainty": season.end_boundary_certainty,
                "internal_gap_count": season.internal_gap_count,
                "season_confidence_note": season_confidence_note,
            }
            for season in seasons
        ],
    }


def write_season_payload(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "season_windows.json"
    safe_write_text(output_path, json.dumps(payload, indent=2, sort_keys=True))
    return output_path
