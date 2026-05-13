"""Smoothing methods for time-series signals."""

from __future__ import annotations

import statistics
from typing import Sequence


SMOOTHING_METHOD_NAME = "rolling_median_3_then_mean_3"


def _window_bounds(index: int, length: int, window_size: int) -> tuple[int, int]:
    radius = window_size // 2
    start = max(0, index - radius)
    end = min(length, index + radius + 1)
    return start, end


def _centered_rolling_median(values: Sequence[float], window_size: int) -> list[float]:
    result: list[float] = []
    for index in range(len(values)):
        start, end = _window_bounds(index, len(values), window_size)
        result.append(float(statistics.median(values[start:end])))
    return result


def _centered_rolling_mean(values: Sequence[float], window_size: int) -> list[float]:
    result: list[float] = []
    for index in range(len(values)):
        start, end = _window_bounds(index, len(values), window_size)
        window = values[start:end]
        result.append(float(sum(window) / len(window)))
    return result


def smooth_usable_values(values: Sequence[float]) -> list[float]:
    """Apply the baseline smoothing method to a usable metric series."""
    if not values:
        return []

    median_pass = _centered_rolling_median(values, window_size=3)
    return _centered_rolling_mean(median_pass, window_size=3)
