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
from pathlib import Path
from statistics import median
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

SIGNAL_MODEL_METHOD = "hybrid_threshold_activity_windows"
LOW_ENVELOPE_PERCENTILE = 20.0
HIGH_ENVELOPE_PERCENTILE = 80.0
LOCAL_ENVELOPE_WINDOW_DAYS = 90.0
MIN_LOCAL_ENVELOPE_OBSERVATIONS = 5
BOUNDARY_PROMINENCE_FRACTION = 0.20
FIXED_ACTIVITY_THRESHOLD_NDVI = 0.35
DYNAMIC_ACTIVITY_MARGIN_NDVI = 0.10
BORDERLINE_FIXED_ACTIVITY_THRESHOLD_NDVI = 0.20
BORDERLINE_DYNAMIC_ACTIVITY_MARGIN_NDVI = 0.05
MAX_INACTIVE_BREAK_DAYS = 15.0
CONFIRMED_PROMINENCE_NOISE_RATIO = 3.8
BORDERLINE_PROMINENCE_NOISE_RATIO = 2.5
STRONG_PROMINENCE_NOISE_RATIO = 4.0
INTERRUPTED_DROP_FRACTION = 0.45
MIN_ACTIVITY_WINDOW_DURATION_DAYS = 20.0
MIN_ACTIVITY_WINDOW_OBSERVATIONS = 4


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
class ActivitySignalModel:
    low_envelope: list[float]
    noise_floor_ndvi: float
    cadence_days: float


@dataclass(frozen=True)
class ActivityCandidate:
    start_index: int
    peak_index: int
    end_index: int
    detection_status: str
    lifecycle_status: str
    baseline_ndvi: float
    prominence_ndvi: float
    boundary_threshold_ndvi: float
    prominence_to_noise_ratio: float


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
    lifecycle_status: str
    detection_status: str
    prominence_ndvi: float
    noise_floor_ndvi: float
    prominence_to_noise_ratio: float


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


def _duration_days(observations: list[SeasonalObservation]) -> float:
    start = observations[0].timestamp
    end = observations[-1].timestamp
    return max(0.0, (end - start).total_seconds() / 86400.0)


def _median_absolute_deviation(values: list[float]) -> float:
    if not values:
        return 0.0
    center = float(median(values))
    return float(median(abs(value - center) for value in values))


def _typical_cadence_days(observations: list[SeasonalObservation]) -> float:
    gaps = [
        (right.timestamp - left.timestamp).total_seconds() / 86400.0
        for left, right in zip(observations[:-1], observations[1:])
        if right.timestamp > left.timestamp
    ]
    if not gaps:
        return 0.0
    return float(median(gaps))


def _estimate_noise_floor(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    step_changes = [abs(right - left) for left, right in zip(values[:-1], values[1:])]
    step_noise = _median_absolute_deviation(step_changes) * 1.4826
    low_step = _percentile(step_changes, LOW_ENVELOPE_PERCENTILE) if step_changes else 0.0
    series_noise = _median_absolute_deviation(values) * 1.4826
    envelope_range = max(values) - min(values)
    sample_scaled_range = envelope_range / max(float(len(values) - 1), 1.0)
    return max(step_noise, low_step, series_noise / 6.0, sample_scaled_range)


def _compute_low_envelope(observations: list[SeasonalObservation]) -> list[float]:
    if not observations:
        return []

    all_values = [row.ndvi_smoothed for row in observations]
    global_low = _percentile(all_values, LOW_ENVELOPE_PERCENTILE)
    envelope: list[float] = []
    for observation in observations:
        local_values = [
            candidate.ndvi_smoothed
            for candidate in observations
            if abs((candidate.timestamp - observation.timestamp).total_seconds()) / 86400.0
            <= LOCAL_ENVELOPE_WINDOW_DAYS
        ]
        if len(local_values) >= MIN_LOCAL_ENVELOPE_OBSERVATIONS:
            envelope.append(_percentile(local_values, LOW_ENVELOPE_PERCENTILE))
        else:
            envelope.append(global_low)
    return envelope


def build_activity_signal_model(observations: list[SeasonalObservation]) -> ActivitySignalModel:
    values = [row.ndvi_smoothed for row in observations]
    return ActivitySignalModel(
        low_envelope=_compute_low_envelope(observations),
        noise_floor_ndvi=_estimate_noise_floor(values),
        cadence_days=_typical_cadence_days(observations),
    )


def _max_single_step_drop(values: list[float]) -> float:
    drops = [left - right for left, right in zip(values[:-1], values[1:]) if right < left]
    if not drops:
        return 0.0
    return max(drops)


def _local_peak_indices(observations: list[SeasonalObservation]) -> list[int]:
    if len(observations) < 2:
        return []

    values = [row.ndvi_smoothed for row in observations]
    indices: list[int] = []
    for index, value in enumerate(values):
        left = values[index - 1] if index > 0 else None
        right = values[index + 1] if index < len(values) - 1 else None
        if left is None and right is not None and value > right:
            indices.append(index)
        elif right is None and left is not None and value > left:
            indices.append(index)
        elif left is not None and right is not None and value >= left and value > right:
            indices.append(index)

    if not indices:
        max_index = max(range(len(values)), key=lambda candidate: values[candidate])
        min_index = min(range(len(values)), key=lambda candidate: values[candidate])
        if max_index != min_index:
            indices.append(max_index)
    return indices


def _local_valley_indices(observations: list[SeasonalObservation]) -> list[int]:
    if len(observations) < 2:
        return []

    values = [row.ndvi_smoothed for row in observations]
    indices: list[int] = []
    for index, value in enumerate(values):
        left = values[index - 1] if index > 0 else None
        right = values[index + 1] if index < len(values) - 1 else None
        if left is None and right is not None and value < right:
            indices.append(index)
        elif right is None and left is not None and value < left:
            indices.append(index)
        elif left is not None and right is not None and value <= left and value < right:
            indices.append(index)
    return indices


def _first_index_at_or_above(
    observations: list[SeasonalObservation],
    *,
    start_index: int,
    end_index: int,
    threshold: float,
) -> int:
    for index in range(start_index, end_index + 1):
        if observations[index].ndvi_smoothed >= threshold:
            return index
    return start_index


def _last_index_at_or_above(
    observations: list[SeasonalObservation],
    *,
    start_index: int,
    end_index: int,
    threshold: float,
) -> int:
    for index in range(end_index, start_index - 1, -1):
        if observations[index].ndvi_smoothed >= threshold:
            return index
    return end_index


def _candidate_from_peak(
    observations: list[SeasonalObservation],
    model: ActivitySignalModel,
    peak_index: int,
) -> ActivityCandidate | None:
    values = [row.ndvi_smoothed for row in observations]
    peak_value = values[peak_index]
    valleys = _local_valley_indices(observations)
    left_valleys = [index for index in valleys if index < peak_index]
    right_valleys = [index for index in valleys if index > peak_index]
    left_low_index = left_valleys[-1] if left_valleys else min(range(0, peak_index + 1), key=lambda index: values[index])
    right_low_index = right_valleys[0] if right_valleys else min(range(peak_index, len(values)), key=lambda index: values[index])
    left_prominence = peak_value - values[left_low_index]
    right_prominence = peak_value - values[right_low_index]
    has_left_rise = peak_index > 0 and left_prominence > 0
    has_right_fall = peak_index < len(observations) - 1 and right_prominence > 0

    if has_left_rise and has_right_fall:
        lifecycle_status = "complete"
        surrounding_low = max(values[left_low_index], values[right_low_index])
        boundary_base = min(values[left_low_index], values[right_low_index])
        prominence = peak_value - surrounding_low
    elif has_left_rise:
        lifecycle_status = "open_right"
        surrounding_low = values[left_low_index]
        boundary_base = surrounding_low
        prominence = left_prominence
    elif has_right_fall:
        lifecycle_status = "open_left"
        surrounding_low = values[right_low_index]
        boundary_base = surrounding_low
        prominence = right_prominence
    else:
        return None

    if prominence <= 0:
        return None

    if model.noise_floor_ndvi > 0:
        prominence_to_noise_ratio = prominence / model.noise_floor_ndvi
    else:
        prominence_to_noise_ratio = float("inf")

    if prominence_to_noise_ratio >= CONFIRMED_PROMINENCE_NOISE_RATIO:
        detection_status = "confirmed"
    elif prominence_to_noise_ratio >= BORDERLINE_PROMINENCE_NOISE_RATIO:
        detection_status = "borderline"
    else:
        return None

    boundary_threshold = boundary_base + BOUNDARY_PROMINENCE_FRACTION * prominence
    if lifecycle_status == "open_left":
        start_index = 0
    else:
        start_index = _first_index_at_or_above(
            observations,
            start_index=left_low_index,
            end_index=peak_index,
            threshold=boundary_threshold,
        )

    if lifecycle_status == "open_right":
        end_index = len(observations) - 1
    else:
        end_index = _last_index_at_or_above(
            observations,
            start_index=peak_index,
            end_index=right_low_index,
            threshold=boundary_threshold,
        )

    if end_index < start_index:
        return None

    if lifecycle_status == "complete":
        if start_index == 0 and end_index == len(observations) - 1:
            lifecycle_status = "open_both"
        elif start_index == 0:
            lifecycle_status = "open_left"
        elif end_index == len(observations) - 1:
            lifecycle_status = "open_right"


    candidate_observations = observations[start_index : end_index + 1]
    if len(candidate_observations) < MIN_ACTIVITY_WINDOW_OBSERVATIONS:
        return None
    if _duration_days(candidate_observations) < MIN_ACTIVITY_WINDOW_DURATION_DAYS:
        return None

    return ActivityCandidate(
        start_index=start_index,
        peak_index=peak_index,
        end_index=end_index,
        detection_status=detection_status,
        lifecycle_status=lifecycle_status,
        baseline_ndvi=model.low_envelope[peak_index],
        prominence_ndvi=prominence,
        boundary_threshold_ndvi=boundary_threshold,
        prominence_to_noise_ratio=prominence_to_noise_ratio,
    )


def _find_activity_candidates(
    observations: list[SeasonalObservation],
    model: ActivitySignalModel,
) -> list[ActivityCandidate]:
    if not observations:
        return []

    values = [row.ndvi_smoothed for row in observations]
    global_baseline = _percentile(values, LOW_ENVELOPE_PERCENTILE)
    confirmed_threshold = max(
        FIXED_ACTIVITY_THRESHOLD_NDVI,
        global_baseline + DYNAMIC_ACTIVITY_MARGIN_NDVI,
    )
    borderline_threshold = max(
        BORDERLINE_FIXED_ACTIVITY_THRESHOLD_NDVI,
        global_baseline + BORDERLINE_DYNAMIC_ACTIVITY_MARGIN_NDVI,
    )

    def _build_segments(threshold: float) -> list[tuple[int, int]]:
        active_indices = [index for index, value in enumerate(values) if value >= threshold]
        if not active_indices:
            return []

        segments: list[tuple[int, int]] = []
        start = active_indices[0]
        previous = active_indices[0]
        for index in active_indices[1:]:
            inactive_break_days = (
                observations[index].timestamp - observations[previous].timestamp
            ).total_seconds() / 86400.0
            if inactive_break_days > MAX_INACTIVE_BREAK_DAYS:
                segments.append((start, previous))
                start = index
            previous = index
        segments.append((start, previous))
        return segments

    candidate_ranges = []
    for start, end in _build_segments(borderline_threshold):
        peak_value = max(values[start : end + 1])
        if peak_value >= confirmed_threshold:
            candidate_ranges.append((start, end, "confirmed", confirmed_threshold))
        else:
            candidate_ranges.append((start, end, "borderline", borderline_threshold))

    candidates: list[ActivityCandidate] = []
    for start_index, end_index, detection_status, threshold in candidate_ranges:
        segment = observations[start_index : end_index + 1]
        if len(segment) < MIN_ACTIVITY_WINDOW_OBSERVATIONS:
            continue
        if _duration_days(segment) < MIN_ACTIVITY_WINDOW_DURATION_DAYS:
            continue

        peak_index = max(range(start_index, end_index + 1), key=lambda index: values[index])
        baseline = min(model.low_envelope[peak_index], global_baseline)
        amplitude = values[peak_index] - baseline
        if amplitude <= 0:
            continue

        if start_index == 0 and end_index == len(observations) - 1:
            lifecycle_status = "open_both"
        elif start_index == 0:
            lifecycle_status = "open_left"
        elif end_index == len(observations) - 1:
            lifecycle_status = "open_right"
        else:
            lifecycle_status = "complete"

        if model.noise_floor_ndvi > 0:
            ratio = amplitude / model.noise_floor_ndvi
        else:
            ratio = float("inf")

        candidates.append(
            ActivityCandidate(
                start_index=start_index,
                peak_index=peak_index,
                end_index=end_index,
                detection_status=detection_status,
                lifecycle_status=lifecycle_status,
                baseline_ndvi=baseline,
                prominence_ndvi=amplitude,
                boundary_threshold_ndvi=threshold,
                prominence_to_noise_ratio=ratio,
            )
        )

    candidates.sort(key=lambda candidate: candidate.start_index)
    return candidates


def _label_quality(
    segment: list[SeasonalObservation],
    *,
    prominence_ndvi: float,
    prominence_to_noise_ratio: float,
    lifecycle_status: str,
) -> tuple[str, str, str]:
    values = [row.ndvi_smoothed for row in segment]
    peak_row = max(segment, key=lambda row: row.ndvi_smoothed)
    duration_days = _duration_days(segment)
    max_drop = _max_single_step_drop(values)

    if max_drop >= prominence_ndvi * INTERRUPTED_DROP_FRACTION:
        return (
            "interrupted",
            (
                "Interrupted vegetation activity window: "
                f"peak_ndvi={peak_row.ndvi_smoothed:.3f}, prominence_ndvi={prominence_ndvi:.3f}, "
                f"max_drop={max_drop:.3f}, lifecycle_status={lifecycle_status}."
            ),
            "moderate",
        )

    if prominence_ndvi >= 0.15 and lifecycle_status == "complete":
        return (
            "good",
            (
                "Good vegetation activity window: "
                f"peak_ndvi={peak_row.ndvi_smoothed:.3f}, prominence_ndvi={prominence_ndvi:.3f}, "
                f"prominence_to_noise_ratio={prominence_to_noise_ratio:.2f}."
            ),
            "strong",
        )

    return (
        "weak",
        (
            "Weak or provisional vegetation activity window: "
            f"peak_ndvi={peak_row.ndvi_smoothed:.3f}, prominence_ndvi={prominence_ndvi:.3f}, "
            f"prominence_to_noise_ratio={prominence_to_noise_ratio:.2f}, "
            f"duration_days={duration_days:.1f}, lifecycle_status={lifecycle_status}."
        ),
        "weak",
    )


def _series_supports_peak(values: list[float], peak_offset: int, *, inverted: bool = False) -> bool:
    if len(values) < 3:
        return False
    peak_value = values[peak_offset]
    low_envelope = _percentile(values, LOW_ENVELOPE_PERCENTILE)
    high_envelope = _percentile(values, HIGH_ENVELOPE_PERCENTILE)
    if high_envelope == low_envelope:
        return False
    normalized = (peak_value - low_envelope) / (high_envelope - low_envelope)
    if inverted:
        return normalized <= 1.0 - BOUNDARY_PROMINENCE_FRACTION
    return normalized >= BOUNDARY_PROMINENCE_FRACTION


def _compute_multi_index_confirmation(
    segment: list[SeasonalObservation],
    *,
    peak_row: SeasonalObservation | None = None,
) -> tuple[str, str]:
    if peak_row is None:
        peak_row = max(segment, key=lambda row: row.ndvi_smoothed)
    peak_offset = segment.index(peak_row)
    evi_values = [row.evi_smoothed for row in segment]
    ndmi_values = [row.ndmi_smoothed for row in segment]
    ndwi_values = [row.ndwi_smoothed for row in segment]

    checks = [
        _series_supports_peak(evi_values, peak_offset),
        _series_supports_peak(ndmi_values, peak_offset),
        _series_supports_peak(ndwi_values, peak_offset, inverted=True),
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
        f"(relative EVI/NDMI support={support_count >= 2}, NDWI non-water support={checks[2]})."
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
    if quality_label == "interrupted" and confirmation_level == "strong" and base_level == "moderate":
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


def _window_from_candidate(
    observations: list[SeasonalObservation],
    candidate: ActivityCandidate,
    *,
    model: ActivitySignalModel,
    long_gap_windows: list[dict[str, Any]],
    sequence_number: int,
) -> SeasonWindow:
    season_observations = observations[candidate.start_index : candidate.end_index + 1]
    peak_row = observations[candidate.peak_index]
    is_open = candidate.lifecycle_status in {"open_right", "open_both"}
    duration_days = _duration_days(season_observations)
    quality_label, evidence_summary, base_level = _label_quality(
        season_observations,
        prominence_ndvi=candidate.prominence_ndvi,
        prominence_to_noise_ratio=candidate.prominence_to_noise_ratio,
        lifecycle_status=candidate.lifecycle_status,
    )
    confirmation_level, confirmation_evidence = _compute_multi_index_confirmation(
        season_observations,
        peak_row=peak_row,
    )
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

    if candidate.lifecycle_status in {"open_left", "open_both"}:
        start_boundary_certainty = "open"
    if candidate.lifecycle_status in {"open_right", "open_both"}:
        end_boundary_certainty = "open"

    provisional = candidate.lifecycle_status != "complete" or gap_provisional
    if candidate.lifecycle_status != "complete":
        evidence_summary = (
            f"{evidence_summary} Window lifecycle is {candidate.lifecycle_status}; "
            "unobserved boundaries are provisional."
        )
    evidence_summary = f"{evidence_summary} {gap_overlap_evidence}"

    return SeasonWindow(
        season_id=f"season_{sequence_number:02d}",
        crossing_date=_iso_date(observations[candidate.start_index].timestamp),
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
        baseline_ndvi=round(candidate.baseline_ndvi, 6),
        amplitude_ndvi=round(candidate.prominence_ndvi, 6),
        boundary_threshold_ndvi=round(candidate.boundary_threshold_ndvi, 6),
        usable_observation_count=len(season_observations),
        start_boundary_certainty=start_boundary_certainty,
        peak_certainty=peak_certainty,
        end_boundary_certainty=end_boundary_certainty,
        internal_gap_count=internal_gap_count,
        lifecycle_status=candidate.lifecycle_status,
        detection_status=candidate.detection_status,
        prominence_ndvi=round(candidate.prominence_ndvi, 6),
        noise_floor_ndvi=round(model.noise_floor_ndvi, 6),
        prominence_to_noise_ratio=round(candidate.prominence_to_noise_ratio, 6),
    )


def _season_to_payload(season: SeasonWindow, season_confidence_note: str) -> dict[str, Any]:
    return {
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
        "lifecycle_status": season.lifecycle_status,
        "detection_status": season.detection_status,
        "prominence_ndvi": season.prominence_ndvi,
        "noise_floor_ndvi": season.noise_floor_ndvi,
        "prominence_to_noise_ratio": season.prominence_to_noise_ratio,
        "season_confidence_note": season_confidence_note,
    }


def detect_activity_windows(
    observations: list[SeasonalObservation],
    *,
    long_gap_windows: Optional[list[dict[str, Any]]] = None,
) -> tuple[list[SeasonWindow], list[SeasonWindow]]:
    long_gap_windows = long_gap_windows or []
    model = build_activity_signal_model(observations)
    candidates = _find_activity_candidates(observations, model)
    confirmed_candidates = [candidate for candidate in candidates if candidate.detection_status == "confirmed"]
    borderline_candidates = [candidate for candidate in candidates if candidate.detection_status == "borderline"]

    confirmed = [
        _window_from_candidate(
            observations,
            candidate,
            model=model,
            long_gap_windows=long_gap_windows,
            sequence_number=index,
        )
        for index, candidate in enumerate(confirmed_candidates, start=1)
    ]
    borderline = [
        _window_from_candidate(
            observations,
            candidate,
            model=model,
            long_gap_windows=long_gap_windows,
            sequence_number=index,
        )
        for index, candidate in enumerate(borderline_candidates, start=1)
    ]
    return confirmed, borderline


def detect_season_windows(
    observations: list[SeasonalObservation],
    *,
    long_gap_windows: Optional[list[dict[str, Any]]] = None,
) -> list[SeasonWindow]:
    confirmed, _borderline = detect_activity_windows(
        observations,
        long_gap_windows=long_gap_windows,
    )
    return confirmed


def build_season_payload(
    smoothed_csv_path: Path,
    quality_metrics_path: Path,
) -> dict[str, Any]:
    quality_metrics = _load_quality_metrics(quality_metrics_path)
    observations = load_preprocess_observations(smoothed_csv_path)
    long_gap_windows = _parse_gap_windows(quality_metrics)
    seasons, borderline_windows = detect_activity_windows(
        observations,
        long_gap_windows=long_gap_windows,
    )
    season_confidence_note = _build_season_confidence_note(quality_metrics)

    complete_window_count = sum(1 for season in seasons if season.lifecycle_status == "complete")
    open_window_count = len(seasons) - complete_window_count

    return {
        "aoi_id": quality_metrics["aoi_id"],
        "season_count": len(seasons),
        "complete_window_count": complete_window_count,
        "open_window_count": open_window_count,
        "borderline_window_count": len(borderline_windows),
        "gap_risk": quality_metrics["gap_risk"],
        "activity_detection_model": {
            "method": SIGNAL_MODEL_METHOD,
            "low_envelope_percentile": LOW_ENVELOPE_PERCENTILE,
            "local_envelope_window_days": LOCAL_ENVELOPE_WINDOW_DAYS,
            "fixed_activity_threshold_ndvi": FIXED_ACTIVITY_THRESHOLD_NDVI,
            "dynamic_activity_margin_ndvi": DYNAMIC_ACTIVITY_MARGIN_NDVI,
            "borderline_fixed_activity_threshold_ndvi": BORDERLINE_FIXED_ACTIVITY_THRESHOLD_NDVI,
            "borderline_dynamic_activity_margin_ndvi": BORDERLINE_DYNAMIC_ACTIVITY_MARGIN_NDVI,
            "max_inactive_break_days": MAX_INACTIVE_BREAK_DAYS,
        },
        "terminology": {
            "season": "detected vegetation activity window, not an agronomic crop season",
        },
        "seasons": [_season_to_payload(season, season_confidence_note) for season in seasons],
        "borderline_windows": [
            _season_to_payload(season, season_confidence_note) for season in borderline_windows
        ],
    }


def write_season_payload(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "season_windows.json"
    safe_write_text(output_path, json.dumps(payload, indent=2, sort_keys=True))
    return output_path
