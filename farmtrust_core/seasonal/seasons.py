"""Vegetation activity-window detection on a daily reconstructed curve.

The durable output file still uses season-oriented field names for API
compatibility. In this module, a "season" record means a detected vegetation
activity window from satellite observations, not an agronomic crop season.

Detection runs on a dense **daily** analysis curve (the weighted Whittaker curve
from :mod:`farmtrust_core.preprocess.analysis_curve`). Peaks/troughs are found in
real-day units; per-cycle start/end use asymmetric relative-amplitude thresholds
(TIMESAT-style) on the rising/falling limbs, with a slope-confirmation gate and
sub-peak merging so a multi-cut crop (e.g. berseem) stays a single cycle.
Confidence/gap evidence is still computed on real usable observation timestamps;
the synthetic daily curve is model-derived and never treated as direct evidence.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Optional, Sequence

import numpy as np
from scipy.signal import find_peaks

from farmtrust_core.ingest.utils import safe_write_text
from farmtrust_core.preprocess.analysis_curve import build_analysis_curves, select_lambda


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

SIGNAL_MODEL_METHOD = "deterministic_peak_trough_relative_amplitude_phenology"

# Percentile envelopes (used for the global bare-soil baseline and the
# multi-index confirmation check).
LOW_ENVELOPE_PERCENTILE = 20.0
HIGH_ENVELOPE_PERCENTILE = 80.0

# Peak / trough detection on the daily NDVI curve. Distances are in REAL DAYS
# (the grid is daily), which is the fix for two cycles separated by a temporal
# gap being merged.
PEAK_MIN_HEIGHT_NDVI = 0.20  # aligned with the borderline activity floor
PEAK_MIN_PROMINENCE_NDVI = 0.144  # aligned with MIN_CYCLE_AMPLITUDE_NDVI
PEAK_MIN_DISTANCE_DAYS = 55
TROUGH_MIN_PROMINENCE_NDVI = 0.08
TROUGH_MIN_DISTANCE_DAYS = 40

# Asymmetric relative-amplitude start/end thresholds (fractions of per-limb
# amplitude). Senescence/harvest is detected at a higher fraction than green-up.
ALPHA_START = 0.20
ALPHA_END = 0.35
# Require the curve to be moving the right way for this many daily steps at a
# start/end crossing -> rejects rain-flush / noise false starts.
SLOPE_CONFIRM_STEPS = 3
# A trough only splits two peaks into separate cycles if it descends at least
# this fraction of the way from the lower peak toward bare soil; otherwise the
# sub-peaks are merged (e.g. berseem cuts).
CYCLE_SPLIT_AMPLITUDE_FRACTION = 0.50

# Amplitude / classification gates.
MIN_CYCLE_AMPLITUDE_NDVI = 0.144
GOOD_QUALITY_MIN_AMPLITUDE_NDVI = 0.15
INTERRUPTED_DROP_FRACTION = 0.45
MIN_ACTIVITY_WINDOW_DURATION_DAYS = 20.0
MIN_ACTIVITY_WINDOW_OBSERVATIONS = 4
MAX_ACTIVITY_WINDOW_DURATION_DAYS = 320.0  # soft sanity flag only (never splits)

FIXED_ACTIVITY_THRESHOLD_NDVI = 0.35
DYNAMIC_ACTIVITY_MARGIN_NDVI = 0.10
BORDERLINE_FIXED_ACTIVITY_THRESHOLD_NDVI = 0.20
BORDERLINE_DYNAMIC_ACTIVITY_MARGIN_NDVI = 0.05
CONFIRMED_AMPLITUDE_NOISE_RATIO = 3.8
BORDERLINE_AMPLITUDE_NOISE_RATIO = 2.5

# Robust noise floor of the daily curve.
ABSOLUTE_NOISE_FLOOR_NDVI = 0.02
NOISE_FLOOR_MAD_SCALE = 1.4826

# Multi-index confirmation: normalized-position support threshold.
MULTI_INDEX_SUPPORT_FRACTION = 0.20


@dataclass(frozen=True)
class SeasonalObservation:
    timestamp: datetime
    ndvi_smoothed: float
    evi_smoothed: float
    ndmi_smoothed: float
    ndwi_smoothed: float
    valid_fraction: float
    source_row_count: int
    is_usable: bool = True


@dataclass(frozen=True)
class DailyAnalysisCurve:
    start_date: date
    dates: list[date]
    ndvi: list[float]
    evi: list[float]
    ndmi: list[float]
    ndwi: list[float]
    selected_lambda: float


@dataclass(frozen=True)
class CycleCandidate:
    start_index: int
    peak_index: int
    end_index: int
    detection_status: str
    lifecycle_status: str
    baseline_left: float
    baseline_right: float
    baseline_ndvi: float
    amplitude_ndvi: float
    peak_ndvi: float
    boundary_threshold_ndvi: float
    amplitude_to_noise_ratio: float
    greenup_rate: float
    senescence_rate: float
    integrated_ndvi: float
    internal_drop: float
    cycle_split_merged: bool


@dataclass(frozen=True)
class SeasonWindow:
    season_id: str
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
    season_calendar_label: str
    greenup_rate: float
    senescence_rate: float
    integrated_ndvi: float
    cycle_split_merged: bool
    daily_curve_lambda: float
    start_boundary_source: str
    peak_source: str
    end_boundary_source: str
    start_nearest_real_observation_date: str | None
    peak_nearest_real_observation_date: str | None
    end_nearest_real_observation_date: str | None
    start_nearest_real_observation_days: float | None
    peak_nearest_real_observation_days: float | None
    end_nearest_real_observation_days: float | None


# ---------------------------------------------------------------------------
# Parsing / loading
# ---------------------------------------------------------------------------


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

        missing_columns = [
            column for column in REQUIRED_PREPROCESS_COLUMNS if column not in reader.fieldnames
        ]
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
                    is_usable=str(row["is_usable"]).strip().lower() == "true",
                )
            )

    if not observations:
        raise ValueError(f"No usable smoothed observations found in {csv_path}")

    observations.sort(key=lambda row: row.timestamp)
    return observations


def load_daily_analysis_curve(csv_path: Path) -> DailyAnalysisCurve:
    """Load the persisted dense daily analysis curve artifact."""
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Analysis curve CSV is empty: {csv_path}")
    dates = [date.fromisoformat(row["date"]) for row in rows]
    return DailyAnalysisCurve(
        start_date=dates[0],
        dates=dates,
        ndvi=[float(row["ndvi_curve"]) for row in rows],
        evi=[float(row["evi_curve"]) for row in rows],
        ndmi=[float(row["ndmi_curve"]) for row in rows],
        ndwi=[float(row["ndwi_curve"]) for row in rows],
        # The CSV does not store lambda; the pipeline always uses the deterministic
        # phenology-timescale default, so recover that rather than emitting NaN.
        selected_lambda=select_lambda()[0],
    )


def daily_curve_from_observations(observations: list[SeasonalObservation]) -> DailyAnalysisCurve:
    """Reconstruct a daily curve from already-smoothed observations.

    Used when callers pass observations directly (tests, and as a fallback when no
    persisted curve is supplied). The smoothed observation values are trusted, so
    every observation anchors the daily reconstruction with full weight.
    """
    timestamps = [obs.timestamp for obs in observations]
    result = build_analysis_curves(
        timestamps=timestamps,
        index_values={
            "ndvi": [obs.ndvi_smoothed for obs in observations],
            "evi": [obs.evi_smoothed for obs in observations],
            "ndmi": [obs.ndmi_smoothed for obs in observations],
            "ndwi": [obs.ndwi_smoothed for obs in observations],
        },
        valid_fractions=[1.0 for _ in observations],
    )
    dates = [result.start_date + timedelta(days=i) for i in range(result.n_days)]
    return DailyAnalysisCurve(
        start_date=result.start_date,
        dates=dates,
        ndvi=result.curves["ndvi"],
        evi=result.curves["evi"],
        ndmi=result.curves["ndmi"],
        ndwi=result.curves["ndwi"],
        selected_lambda=result.selected_lambda,
    )


# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------


def _percentile(values: Sequence[float], percentile: float) -> float:
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


def _noise_floor(values: np.ndarray) -> float:
    if len(values) < 2:
        return ABSOLUTE_NOISE_FLOOR_NDVI
    diffs = np.abs(np.diff(values))
    mad = float(median([abs(d - float(median(diffs))) for d in diffs])) if len(diffs) else 0.0
    return max(ABSOLUTE_NOISE_FLOOR_NDVI, mad * NOISE_FLOOR_MAD_SCALE)


def _slope_confirmed_rising(values: np.ndarray, index: int, steps: int) -> bool:
    low = max(1, index - steps + 1)
    if index < 1:
        return True
    return all(values[j] >= values[j - 1] for j in range(low, index + 1))


def _slope_confirmed_falling(values: np.ndarray, index: int, steps: int) -> bool:
    high = min(len(values) - 1, index + steps)
    if index > len(values) - 2:
        return True
    return all(values[j + 1] <= values[j] for j in range(index, high))


# ---------------------------------------------------------------------------
# Peak / trough detection and cycle building (on the daily curve)
# ---------------------------------------------------------------------------


def _detect_peaks(values: np.ndarray) -> list[int]:
    peaks, _ = find_peaks(
        values,
        height=PEAK_MIN_HEIGHT_NDVI,
        prominence=PEAK_MIN_PROMINENCE_NDVI,
        distance=PEAK_MIN_DISTANCE_DAYS,
    )
    peaks = [int(p) for p in peaks]
    n = len(values)
    # Boundary peaks: scipy.find_peaks cannot return the first/last index, but a
    # partially-observed (open) cycle peaks exactly there.
    if n >= 3 and values[0] >= PEAK_MIN_HEIGHT_NDVI and values[0] >= values[1] >= values[2]:
        peaks.append(0)
    if n >= 3 and values[-1] >= PEAK_MIN_HEIGHT_NDVI and values[-1] >= values[-2] >= values[-3]:
        peaks.append(n - 1)
    return sorted(set(peaks))


def _group_peaks(
    values: np.ndarray,
    peaks: list[int],
    global_baseline: float,
) -> list[tuple[int, list[int], int, float]]:
    """Merge sub-peaks separated by shallow troughs into single cycles.

    Returns (left_bound, peak_indices, right_bound, deepest_internal_drop).
    """
    if not peaks:
        return []

    groups: list[tuple[int, list[int], int, float]] = []
    left = int(np.argmin(values[: peaks[0] + 1]))
    current = [peaks[0]]
    internal_drops: list[float] = []

    for a, b in zip(peaks, peaks[1:]):
        valley = a + int(np.argmin(values[a : b + 1]))
        drop = float(min(values[a], values[b]) - values[valley])
        amp_ref = float(min(values[a], values[b]) - global_baseline)
        if amp_ref > 0 and drop >= CYCLE_SPLIT_AMPLITUDE_FRACTION * amp_ref:
            groups.append((left, current, valley, max(internal_drops) if internal_drops else 0.0))
            left = valley
            current = [b]
            internal_drops = []
        else:
            internal_drops.append(drop)
            current.append(b)

    last_peak = current[-1]
    right = last_peak + int(np.argmin(values[last_peak:]))
    groups.append((left, current, right, max(internal_drops) if internal_drops else 0.0))
    return groups


def _find_start_index(values: np.ndarray, left: int, peak: int, threshold: float) -> int:
    crossings = [i for i in range(left, peak + 1) if values[i] >= threshold]
    if not crossings:
        return left
    for i in crossings:
        if _slope_confirmed_rising(values, i, SLOPE_CONFIRM_STEPS):
            return i
    return crossings[0]


def _find_end_index(values: np.ndarray, peak: int, right: int, threshold: float) -> int:
    crossings = [i for i in range(peak, right + 1) if values[i] >= threshold]
    if not crossings:
        return right
    for i in reversed(crossings):
        if _slope_confirmed_falling(values, i, SLOPE_CONFIRM_STEPS):
            return i
    return crossings[-1]


def _detection_status(peak_ndvi: float, amplitude: float, baseline: float, noise: float) -> tuple[str | None, float]:
    ratio = amplitude / noise if noise > 0 else float("inf")
    confirmed_threshold = max(
        FIXED_ACTIVITY_THRESHOLD_NDVI, baseline + DYNAMIC_ACTIVITY_MARGIN_NDVI
    )
    borderline_threshold = max(
        BORDERLINE_FIXED_ACTIVITY_THRESHOLD_NDVI, baseline + BORDERLINE_DYNAMIC_ACTIVITY_MARGIN_NDVI
    )
    if ratio >= CONFIRMED_AMPLITUDE_NOISE_RATIO and peak_ndvi >= confirmed_threshold:
        return "confirmed", ratio
    if ratio >= BORDERLINE_AMPLITUDE_NOISE_RATIO and peak_ndvi >= borderline_threshold:
        return "borderline", ratio
    return None, ratio


def _build_candidate(
    values: np.ndarray,
    group: tuple[int, list[int], int, float],
    *,
    noise: float,
) -> CycleCandidate | None:
    left, group_peaks, right, internal_drop = group
    peak = max(group_peaks, key=lambda i: values[i])
    n = len(values)

    baseline_left = float(values[left])
    baseline_right = float(values[right])
    peak_ndvi = float(values[peak])
    baseline = min(baseline_left, baseline_right)
    amplitude = peak_ndvi - baseline
    if amplitude < MIN_CYCLE_AMPLITUDE_NDVI:
        return None

    sos_threshold = baseline_left + ALPHA_START * (peak_ndvi - baseline_left)
    eos_threshold = baseline_right + ALPHA_END * (peak_ndvi - baseline_right)

    start_index = _find_start_index(values, left, peak, sos_threshold)
    end_index = _find_end_index(values, peak, right, eos_threshold)
    if end_index < start_index:
        return None

    open_left = left == 0 and values[0] >= sos_threshold
    open_right = right == n - 1 and values[-1] >= eos_threshold
    if open_left and open_right:
        lifecycle_status = "open_both"
    elif open_left:
        lifecycle_status = "open_left"
    elif open_right:
        lifecycle_status = "open_right"
    else:
        lifecycle_status = "complete"

    detection_status, ratio = _detection_status(peak_ndvi, amplitude, baseline, noise)
    if detection_status is None:
        return None

    greenup_rate = (
        (peak_ndvi - float(values[start_index])) / max(peak - start_index, 1)
        if peak > start_index
        else 0.0
    )
    senescence_rate = (
        (float(values[end_index]) - peak_ndvi) / max(end_index - peak, 1)
        if end_index > peak
        else 0.0
    )
    integrated_ndvi = float(
        np.trapezoid(np.clip(values[start_index : end_index + 1] - baseline, 0.0, None))
    )

    return CycleCandidate(
        start_index=start_index,
        peak_index=peak,
        end_index=end_index,
        detection_status=detection_status,
        lifecycle_status=lifecycle_status,
        baseline_left=baseline_left,
        baseline_right=baseline_right,
        baseline_ndvi=baseline,
        amplitude_ndvi=amplitude,
        peak_ndvi=peak_ndvi,
        boundary_threshold_ndvi=sos_threshold,
        amplitude_to_noise_ratio=ratio,
        greenup_rate=greenup_rate,
        senescence_rate=senescence_rate,
        integrated_ndvi=integrated_ndvi,
        internal_drop=internal_drop,
        cycle_split_merged=len(group_peaks) > 1,
    )


def _find_cycle_candidates(curve: DailyAnalysisCurve) -> list[CycleCandidate]:
    values = np.asarray(curve.ndvi, dtype=float)
    if len(values) < 3:
        return []
    noise = _noise_floor(values)
    global_baseline = _percentile([float(v) for v in values], LOW_ENVELOPE_PERCENTILE)
    peaks = _detect_peaks(values)
    groups = _group_peaks(values, peaks, global_baseline)
    candidates: list[CycleCandidate] = []
    for group in groups:
        candidate = _build_candidate(values, group, noise=noise)
        if candidate is not None:
            candidates.append(candidate)
    return sorted(candidates, key=lambda c: c.start_index)


# ---------------------------------------------------------------------------
# Evidence layers (computed on REAL usable observations)
# ---------------------------------------------------------------------------


def _max_single_step_drop(values: list[float]) -> float:
    drops = [left - right for left, right in zip(values[:-1], values[1:]) if right < left]
    return max(drops) if drops else 0.0


def _label_quality(
    *,
    amplitude_ndvi: float,
    amplitude_to_noise_ratio: float,
    lifecycle_status: str,
    peak_ndvi: float,
    internal_drop: float,
) -> tuple[str, str, str]:
    if internal_drop >= amplitude_ndvi * INTERRUPTED_DROP_FRACTION and internal_drop > 0:
        return (
            "interrupted",
            (
                "Interrupted vegetation activity window: "
                f"peak_ndvi={peak_ndvi:.3f}, amplitude_ndvi={amplitude_ndvi:.3f}, "
                f"internal_drop={internal_drop:.3f}, lifecycle_status={lifecycle_status}."
            ),
            "moderate",
        )

    if amplitude_ndvi >= GOOD_QUALITY_MIN_AMPLITUDE_NDVI and lifecycle_status == "complete":
        return (
            "good",
            (
                "Good vegetation activity window: "
                f"peak_ndvi={peak_ndvi:.3f}, amplitude_ndvi={amplitude_ndvi:.3f}, "
                f"amplitude_to_noise_ratio={amplitude_to_noise_ratio:.2f}."
            ),
            "strong",
        )

    return (
        "weak",
        (
            "Weak or provisional vegetation activity window: "
            f"peak_ndvi={peak_ndvi:.3f}, amplitude_ndvi={amplitude_ndvi:.3f}, "
            f"amplitude_to_noise_ratio={amplitude_to_noise_ratio:.2f}, "
            f"lifecycle_status={lifecycle_status}."
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
        return normalized <= 1.0 - MULTI_INDEX_SUPPORT_FRACTION
    return normalized >= MULTI_INDEX_SUPPORT_FRACTION


def _compute_multi_index_confirmation(segment: list[SeasonalObservation]) -> tuple[str, str]:
    if not segment:
        return "weak", "Multi-index confirmation=weak (no observations in window)."
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


def _observations_in_window(
    observations: list[SeasonalObservation],
    start_date: date,
    end_date: date,
) -> list[SeasonalObservation]:
    return [
        obs
        for obs in observations
        if start_date <= obs.timestamp.astimezone(timezone.utc).date() <= end_date
    ]


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
        dominant_stage = "middle"
        for candidate in ("onset", "peak", "tail", "middle"):
            if candidate in touched_stages:
                dominant_stage = candidate
                break
    else:
        dominant_stage = "unclassified"

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


def _nearest_real_observation_support(
    observations: list[SeasonalObservation],
    target_date: date,
) -> tuple[str | None, float | None]:
    usable = [observation for observation in observations if observation.is_usable]
    if not usable:
        return None, None
    target = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    nearest = min(
        usable,
        key=lambda observation: abs((observation.timestamp - target).total_seconds()),
    )
    support_days = abs((nearest.timestamp - target).total_seconds()) / 86400.0
    return _iso_date(nearest.timestamp), round(float(support_days), 2)


def _season_calendar_label(peak_date: date) -> str:
    month = peak_date.month
    if month in (5, 6, 7, 8, 9):
        return "summer"
    if month in (11, 12, 1, 2, 3):
        return "winter"
    return "transition"


# ---------------------------------------------------------------------------
# Window construction + payload
# ---------------------------------------------------------------------------


def _window_from_candidate(
    observations: list[SeasonalObservation],
    curve: DailyAnalysisCurve,
    candidate: CycleCandidate,
    *,
    long_gap_windows: list[dict[str, Any]],
    noise_floor: float,
    sequence_number: int,
) -> SeasonWindow:
    start_date = curve.dates[candidate.start_index]
    peak_date = curve.dates[candidate.peak_index]
    end_date = curve.dates[candidate.end_index]
    duration_days = float((end_date - start_date).days)
    season_observations = _observations_in_window(observations, start_date, end_date)

    is_open = candidate.lifecycle_status in {"open_right", "open_both"}

    quality_label, evidence_summary, base_level = _label_quality(
        amplitude_ndvi=candidate.amplitude_ndvi,
        amplitude_to_noise_ratio=candidate.amplitude_to_noise_ratio,
        lifecycle_status=candidate.lifecycle_status,
        peak_ndvi=candidate.peak_ndvi,
        internal_drop=candidate.internal_drop,
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
    ) = _compute_gap_overlap(season_observations, long_gap_windows)

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
    if duration_days > MAX_ACTIVITY_WINDOW_DURATION_DAYS:
        evidence_summary = (
            f"{evidence_summary} Unusually long cycle ({duration_days:.0f} days); "
            "may span multiple managements."
        )

    start_support_date, start_support_days = _nearest_real_observation_support(observations, start_date)
    peak_support_date, peak_support_days = _nearest_real_observation_support(observations, peak_date)
    end_support_date, end_support_days = _nearest_real_observation_support(observations, end_date)

    evidence_summary = (
        f"{evidence_summary} Boundaries were estimated from the model-derived season-analysis curve "
        "and checked against nearest real usable observations. "
        f"{gap_overlap_evidence}"
    )

    return SeasonWindow(
        season_id=f"season_{sequence_number:02d}",
        start_date=start_date.isoformat(),
        peak_date=peak_date.isoformat(),
        end_date=end_date.isoformat(),
        is_open=is_open,
        peak_ndvi=round(candidate.peak_ndvi, 6),
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
        amplitude_ndvi=round(candidate.amplitude_ndvi, 6),
        boundary_threshold_ndvi=round(candidate.boundary_threshold_ndvi, 6),
        usable_observation_count=sum(1 for obs in season_observations if obs.is_usable),
        start_boundary_certainty=start_boundary_certainty,
        peak_certainty=peak_certainty,
        end_boundary_certainty=end_boundary_certainty,
        internal_gap_count=internal_gap_count,
        lifecycle_status=candidate.lifecycle_status,
        detection_status=candidate.detection_status,
        prominence_ndvi=round(candidate.amplitude_ndvi, 6),
        noise_floor_ndvi=round(noise_floor, 6),
        prominence_to_noise_ratio=round(candidate.amplitude_to_noise_ratio, 6),
        season_calendar_label=_season_calendar_label(peak_date),
        greenup_rate=round(candidate.greenup_rate, 6),
        senescence_rate=round(candidate.senescence_rate, 6),
        integrated_ndvi=round(candidate.integrated_ndvi, 6),
        cycle_split_merged=candidate.cycle_split_merged,
        daily_curve_lambda=round(float(curve.selected_lambda), 6),
        start_boundary_source="model_derived_analysis_curve",
        peak_source="model_derived_analysis_curve",
        end_boundary_source="model_derived_analysis_curve",
        start_nearest_real_observation_date=start_support_date,
        peak_nearest_real_observation_date=peak_support_date,
        end_nearest_real_observation_date=end_support_date,
        start_nearest_real_observation_days=start_support_days,
        peak_nearest_real_observation_days=peak_support_days,
        end_nearest_real_observation_days=end_support_days,
    )


def _season_to_payload(season: SeasonWindow, season_confidence_note: str) -> dict[str, Any]:
    return {
        "season_id": season.season_id,
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
        "season_calendar_label": season.season_calendar_label,
        "greenup_rate": season.greenup_rate,
        "senescence_rate": season.senescence_rate,
        "integrated_ndvi": season.integrated_ndvi,
        "cycle_split_merged": season.cycle_split_merged,
        "daily_curve_lambda": season.daily_curve_lambda,
        "start_boundary_source": season.start_boundary_source,
        "peak_source": season.peak_source,
        "end_boundary_source": season.end_boundary_source,
        "start_nearest_real_observation_date": season.start_nearest_real_observation_date,
        "peak_nearest_real_observation_date": season.peak_nearest_real_observation_date,
        "end_nearest_real_observation_date": season.end_nearest_real_observation_date,
        "start_nearest_real_observation_days": season.start_nearest_real_observation_days,
        "peak_nearest_real_observation_days": season.peak_nearest_real_observation_days,
        "end_nearest_real_observation_days": season.end_nearest_real_observation_days,
        "season_confidence_note": season_confidence_note,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_activity_windows(
    observations: list[SeasonalObservation],
    *,
    long_gap_windows: Optional[list[dict[str, Any]]] = None,
    daily_curve: Optional[DailyAnalysisCurve] = None,
) -> tuple[list[SeasonWindow], list[SeasonWindow]]:
    long_gap_windows = long_gap_windows or []
    if daily_curve is None:
        daily_curve = daily_curve_from_observations(observations)

    noise_floor = _noise_floor(np.asarray(daily_curve.ndvi, dtype=float))
    candidates = [
        candidate
        for candidate in _find_cycle_candidates(daily_curve)
        if _window_passes_size_gates(observations, daily_curve, candidate)
    ]

    windows: list[SeasonWindow] = []
    for sequence_number, candidate in enumerate(candidates, start=1):
        windows.append(
            _window_from_candidate(
                observations,
                daily_curve,
                candidate,
                long_gap_windows=long_gap_windows,
                noise_floor=noise_floor,
                sequence_number=sequence_number,
            )
        )

    confirmed = [window for window in windows if window.detection_status == "confirmed"]
    borderline = [window for window in windows if window.detection_status == "borderline"]
    return confirmed, borderline


def _window_passes_size_gates(
    observations: list[SeasonalObservation],
    curve: DailyAnalysisCurve,
    candidate: CycleCandidate,
) -> bool:
    start_date = curve.dates[candidate.start_index]
    end_date = curve.dates[candidate.end_index]
    if (end_date - start_date).days < MIN_ACTIVITY_WINDOW_DURATION_DAYS:
        return False
    season_observations = _observations_in_window(observations, start_date, end_date)
    if len(season_observations) < MIN_ACTIVITY_WINDOW_OBSERVATIONS:
        return False
    return True


def detect_season_windows(
    observations: list[SeasonalObservation],
    *,
    long_gap_windows: Optional[list[dict[str, Any]]] = None,
    daily_curve: Optional[DailyAnalysisCurve] = None,
) -> list[SeasonWindow]:
    confirmed, _borderline = detect_activity_windows(
        observations,
        long_gap_windows=long_gap_windows,
        daily_curve=daily_curve,
    )
    return confirmed


def build_season_payload(
    smoothed_csv_path: Path,
    quality_metrics_path: Path,
    *,
    daily_curve_path: Optional[Path] = None,
) -> dict[str, Any]:
    quality_metrics = _load_quality_metrics(quality_metrics_path)
    observations = load_preprocess_observations(smoothed_csv_path)
    long_gap_windows = _parse_gap_windows(quality_metrics)

    daily_curve: Optional[DailyAnalysisCurve] = None
    if daily_curve_path is not None and Path(daily_curve_path).exists():
        daily_curve = load_daily_analysis_curve(Path(daily_curve_path))

    seasons, borderline_windows = detect_activity_windows(
        observations,
        long_gap_windows=long_gap_windows,
        daily_curve=daily_curve,
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
            "input_signal": "model_derived_analysis_curve_at_observed_timestamps",
            "boundary_method": "peak_trough_per_cycle_amplitude_fraction",
            "alpha_start": ALPHA_START,
            "alpha_end": ALPHA_END,
            "slope_confirm_steps": SLOPE_CONFIRM_STEPS,
            "cycle_split_amplitude_fraction": CYCLE_SPLIT_AMPLITUDE_FRACTION,
            "gap_confidence_source": "real_usable_observation_timestamps",
            "low_envelope_percentile": LOW_ENVELOPE_PERCENTILE,
            "fixed_activity_threshold_ndvi": FIXED_ACTIVITY_THRESHOLD_NDVI,
            "dynamic_activity_margin_ndvi": DYNAMIC_ACTIVITY_MARGIN_NDVI,
            "borderline_fixed_activity_threshold_ndvi": BORDERLINE_FIXED_ACTIVITY_THRESHOLD_NDVI,
            "borderline_dynamic_activity_margin_ndvi": BORDERLINE_DYNAMIC_ACTIVITY_MARGIN_NDVI,
            "min_cycle_amplitude_ndvi": MIN_CYCLE_AMPLITUDE_NDVI,
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
