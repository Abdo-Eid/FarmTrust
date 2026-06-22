"""Gap-aware smoothing methods for time-series signals."""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Sequence


MAX_SMOOTHING_GAP_DAYS = 12.0
LOCAL_WINDOW_DAYS = 12.0
MIN_LOCAL_NEIGHBORS = 2
SMOOTHING_METHOD_NAME = "gap_aware_local_median_weighted_mean"
SMOOTHING_WEIGHTING_POLICY = "valid_fraction_time_distance"
SMOOTHING_INTERPOLATION_POLICY = "none"


def smoothing_metadata() -> dict[str, object]:
    return {
        "smoothing_method": SMOOTHING_METHOD_NAME,
        "max_smoothing_gap_days": MAX_SMOOTHING_GAP_DAYS,
        "local_window_days": LOCAL_WINDOW_DAYS,
        "minimum_local_neighbors": MIN_LOCAL_NEIGHBORS,
        "minimum_local_neighbors_excludes_center": True,
        "weighting_policy": SMOOTHING_WEIGHTING_POLICY,
        "interpolation_policy": SMOOTHING_INTERPOLATION_POLICY,
        "creates_synthetic_timestamps": False,
        "smooths_only_usable_observations": True,
    }


def _day_delta(left: datetime, right: datetime) -> float:
    return abs((right - left).total_seconds()) / 86400.0


def _continuous_segments(
    timestamps: Sequence[datetime],
    *,
    max_gap_days: float,
) -> list[tuple[int, int]]:
    if not timestamps:
        return []

    segments: list[tuple[int, int]] = []
    start = 0
    for index in range(1, len(timestamps)):
        gap_days = (timestamps[index] - timestamps[index - 1]).total_seconds() / 86400.0
        if gap_days > max_gap_days:
            segments.append((start, index))
            start = index
    segments.append((start, len(timestamps)))
    return segments


def _window_indices(
    timestamps: Sequence[datetime],
    *,
    center_index: int,
    start: int,
    end: int,
    local_window_days: float,
) -> list[int]:
    center_timestamp = timestamps[center_index]
    return [
        index
        for index in range(start, end)
        if _day_delta(timestamps[index], center_timestamp) <= local_window_days
    ]


def _has_enough_neighbors(window_indices: list[int], center_index: int, min_neighbors: int) -> bool:
    neighbor_count = sum(1 for index in window_indices if index != center_index)
    return neighbor_count >= min_neighbors


def _weighted_mean(
    *,
    center_index: int,
    indices: list[int],
    timestamps: Sequence[datetime],
    values: Sequence[float],
    valid_fractions: Sequence[float],
    local_window_days: float,
) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    center_timestamp = timestamps[center_index]

    for index in indices:
        delta_days = _day_delta(timestamps[index], center_timestamp)
        weight = max(float(valid_fractions[index]), 0.0) / (1.0 + delta_days / local_window_days)
        weighted_sum += values[index] * weight
        total_weight += weight

    if total_weight <= 0:
        return float(sum(values[index] for index in indices) / len(indices))
    return float(weighted_sum / total_weight)


def smooth_usable_values(
    *,
    timestamps: Sequence[datetime],
    values: Sequence[float],
    valid_fractions: Sequence[float],
    max_gap_days: float = MAX_SMOOTHING_GAP_DAYS,
    local_window_days: float = LOCAL_WINDOW_DAYS,
    min_local_neighbors: int = MIN_LOCAL_NEIGHBORS,
) -> list[float]:
    """Smooth real usable observations without crossing timestamp gaps."""
    if not (len(timestamps) == len(values) == len(valid_fractions)):
        raise ValueError("timestamps, values, and valid_fractions must have the same length")
    if not values:
        return []
    if local_window_days <= 0:
        raise ValueError("local_window_days must be positive")

    smoothed = [float(value) for value in values]
    segments = _continuous_segments(timestamps, max_gap_days=max_gap_days)

    for start, end in segments:
        if end - start <= 2:
            continue

        median_pass = [float(value) for value in values]
        for index in range(start, end):
            indices = _window_indices(
                timestamps,
                center_index=index,
                start=start,
                end=end,
                local_window_days=local_window_days,
            )
            if not _has_enough_neighbors(indices, index, min_local_neighbors):
                continue
            median_pass[index] = float(statistics.median(values[window_index] for window_index in indices))

        for index in range(start, end):
            indices = _window_indices(
                timestamps,
                center_index=index,
                start=start,
                end=end,
                local_window_days=local_window_days,
            )
            if not _has_enough_neighbors(indices, index, min_local_neighbors):
                continue
            smoothed[index] = _weighted_mean(
                center_index=index,
                indices=indices,
                timestamps=timestamps,
                values=median_pass,
                valid_fractions=valid_fractions,
                local_window_days=local_window_days,
            )

    return smoothed
