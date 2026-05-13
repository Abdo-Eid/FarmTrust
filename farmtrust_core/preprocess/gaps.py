"""Gap metrics and handling helpers."""

from __future__ import annotations

from datetime import datetime
import statistics
from typing import Iterable


EXPECTED_CADENCE_DAYS = 5.0
MODERATE_GAP_DAYS = 10.0
HIGH_GAP_DAYS = 15.0


def _day_deltas(timestamps: Iterable[datetime]) -> list[float]:
    ordered = sorted(timestamps)
    if len(ordered) < 2:
        return []

    deltas: list[float] = []
    for left, right in zip(ordered[:-1], ordered[1:]):
        delta_days = (right - left).total_seconds() / 86400.0
        deltas.append(delta_days)
    return deltas


def compute_gap_metrics(
    timestamps: Iterable[datetime],
    *,
    expected_cadence_days: float = EXPECTED_CADENCE_DAYS,
) -> dict[str, float]:
    """Compute simple gap metrics from usable timestamps."""
    ordered = sorted(timestamps)
    if not ordered:
        return {
            "gap_ratio": 1.0,
            "max_gap_days": 0.0,
            "median_gap_days": 0.0,
        }

    if len(ordered) == 1:
        return {
            "gap_ratio": 0.0,
            "max_gap_days": 0.0,
            "median_gap_days": 0.0,
        }

    deltas = _day_deltas(ordered)
    total_span_days = max((ordered[-1] - ordered[0]).total_seconds() / 86400.0, 0.0)
    excess_gap_days = sum(max(0.0, delta - expected_cadence_days) for delta in deltas)
    gap_ratio = (excess_gap_days / total_span_days) if total_span_days > 0 else 0.0

    return {
        "gap_ratio": float(min(max(gap_ratio, 0.0), 1.0)),
        "max_gap_days": float(max(deltas)),
        "median_gap_days": float(statistics.median(deltas)),
    }


def compute_gap_windows(
    timestamps: Iterable[datetime],
    *,
    expected_cadence_days: float = EXPECTED_CADENCE_DAYS,
    long_gap_days: float = MODERATE_GAP_DAYS,
) -> dict[str, object]:
    """Return explicit gap windows for downstream review and storytelling."""
    ordered = sorted(timestamps)
    if len(ordered) < 2:
        return {
            "gap_window_count": 0,
            "long_gap_count": 0,
            "long_gap_windows": [],
        }

    long_gap_windows: list[dict[str, object]] = []
    for left, right in zip(ordered[:-1], ordered[1:]):
        gap_days = (right - left).total_seconds() / 86400.0
        if gap_days <= long_gap_days:
            continue

        long_gap_windows.append(
            {
                "start_timestamp": left.isoformat(),
                "end_timestamp": right.isoformat(),
                "gap_days": float(gap_days),
                "excess_gap_days": float(max(0.0, gap_days - expected_cadence_days)),
            }
        )

    return {
        "gap_window_count": len(long_gap_windows),
        "long_gap_count": len(long_gap_windows),
        "long_gap_windows": long_gap_windows,
    }


def build_confidence_inputs(
    *,
    usable_observation_count: int,
    gap_ratio: float,
    max_gap_days: float,
) -> dict[str, float]:
    """Expose the baseline confidence inputs expected by downstream roles."""
    return {
        "usable_observation_count": int(usable_observation_count),
        "gap_ratio": float(gap_ratio),
        "max_gap_days": float(max_gap_days),
    }


def classify_gap_risk(
    *,
    gap_ratio: float,
    max_gap_days: float,
) -> dict[str, object]:
    """Classify gap risk for downstream confidence and review use."""
    if max_gap_days > HIGH_GAP_DAYS or gap_ratio > 0.30:
        return {
            "gap_risk": "high",
            "confidence_penalty": "high",
            "gap_risk_reason": (
                "Long or frequent gaps may hide season onset, interruption, or peak timing."
            ),
        }

    if max_gap_days > MODERATE_GAP_DAYS or gap_ratio > 0.15:
        return {
            "gap_risk": "moderate",
            "confidence_penalty": "moderate",
            "gap_risk_reason": (
                "Some continuity is missing, so seasonal timing should be treated with caution."
            ),
        }

    return {
        "gap_risk": "low",
        "confidence_penalty": "low",
        "gap_risk_reason": (
            "Observation continuity is strong enough that gap-related distortion risk is limited."
        ),
    }
