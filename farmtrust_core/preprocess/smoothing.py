"""Gap filling and smoothing methods for time-series signals."""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Sequence

import numpy as np


MAX_SMOOTHING_GAP_DAYS = 12.0
LOCAL_WINDOW_DAYS = 12.0
MIN_LOCAL_NEIGHBORS = 2
SMOOTHING_METHOD_NAME = "linear_fill_savitzky_golay"
SMOOTHING_WEIGHTING_POLICY = "none"
SMOOTHING_INTERPOLATION_POLICY = "full_curve_linear_between_usable_observations"
SAVGOL_WINDOW_OBSERVATIONS = 11
SAVGOL_POLYORDER = 3


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
        "smooths_only_usable_observations": False,
        "fill_policy": "fill_all_observed_timestamps_from_usable_anchors",
        "savgol_window_observations": SAVGOL_WINDOW_OBSERVATIONS,
        "savgol_polyorder": SAVGOL_POLYORDER,
    }


def _is_finite(value: float) -> bool:
    return bool(np.isfinite(float(value)))


def _to_day_offsets(timestamps: Sequence[datetime]) -> list[float]:
    origin = timestamps[0]
    return [(timestamp - origin).total_seconds() / 86400.0 for timestamp in timestamps]


def fill_analysis_values(
    *,
    timestamps: Sequence[datetime],
    values: Sequence[float],
    is_usable: Sequence[bool],
) -> list[float]:
    """Fill every observed timestamp from usable finite anchors, without creating dates."""
    if not (len(timestamps) == len(values) == len(is_usable)):
        raise ValueError("timestamps, values, and is_usable must have the same length")
    if not values:
        return []

    anchor_indices = [
        index
        for index, (value, usable) in enumerate(zip(values, is_usable))
        if usable and _is_finite(value)
    ]
    if not anchor_indices:
        raise ValueError("Cannot fill analysis curve without usable finite observations")
    if len(anchor_indices) == 1:
        return [float(values[anchor_indices[0]]) for _value in values]

    x = np.asarray(_to_day_offsets(timestamps), dtype=float)
    anchor_x = np.asarray([x[index] for index in anchor_indices], dtype=float)
    anchor_y = np.asarray([float(values[index]) for index in anchor_indices], dtype=float)
    filled = np.interp(x, anchor_x, anchor_y)
    return [float(value) for value in filled]


def _odd_window_length(length: int, requested: int) -> int:
    window = min(length, requested)
    if window % 2 == 0:
        window -= 1
    return max(window, 1)


def smooth_filled_values(
    values: Sequence[float],
    *,
    window_observations: int = SAVGOL_WINDOW_OBSERVATIONS,
    polyorder: int = SAVGOL_POLYORDER,
) -> list[float]:
    """Apply a small Savitzky-Golay smoother on the filled observed-timestamp curve."""
    if not values:
        return []
    if window_observations <= 0:
        raise ValueError("window_observations must be positive")
    if polyorder < 0:
        raise ValueError("polyorder must be non-negative")

    raw = np.asarray([float(value) for value in values], dtype=float)
    window = _odd_window_length(len(raw), window_observations)
    if window <= polyorder or len(raw) <= polyorder:
        return [float(value) for value in raw]

    half_window = window // 2
    smoothed: list[float] = []
    for index in range(len(raw)):
        start = max(0, index - half_window)
        end = min(len(raw), index + half_window + 1)
        if end - start <= polyorder:
            smoothed.append(float(raw[index]))
            continue
        local_x = np.arange(start, end, dtype=float) - float(index)
        local_y = raw[start:end]
        coeffs = np.polynomial.polynomial.polyfit(local_x, local_y, deg=polyorder)
        smoothed.append(float(coeffs[0]))
    return smoothed


def build_analysis_values(
    *,
    timestamps: Sequence[datetime],
    values: Sequence[float],
    is_usable: Sequence[bool],
) -> tuple[list[float], list[float]]:
    filled = fill_analysis_values(
        timestamps=timestamps,
        values=values,
        is_usable=is_usable,
    )
    return filled, smooth_filled_values(filled)


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
