"""Index computations for ingestion outputs."""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

# Note: all inputs are single-band 2D arrays (one channel per argument),
# not stacked multi-band tensors.


def compute_stats(arr: np.ndarray, mask: np.ndarray, name: str) -> Tuple[float, float]:
    """Return mean and p95 for masked valid pixels.

    The mask is applied first, then NaNs are excluded. If no valid pixels remain,
    the function logs a warning and returns (nan, nan).
    """
    valid = arr[mask & ~np.isnan(arr)]
    if valid.size == 0:
        logging.getLogger(__name__).warning(f"No valid pixels for {name}")
        return float("nan"), float("nan")
    mean = float(np.nanmean(valid))
    p95 = float(np.nanpercentile(valid, 95))
    return mean, p95


def compute_ndvi(red: np.ndarray, nir: np.ndarray, mask: np.ndarray) -> Tuple[float, float]:
    """Compute NDVI stats from red and NIR arrays.

    NDVI = (NIR - Red) / (NIR + Red). The returned values are the mean and p95
    of masked valid pixels.
    """
    ndvi = (nir - red) / (nir + red + 1e-8)
    return compute_stats(ndvi, mask, "ndvi")


def compute_evi(blue: np.ndarray, red: np.ndarray, nir: np.ndarray, mask: np.ndarray) -> Tuple[float, float]:
    """Compute EVI stats from blue, red, and NIR arrays.

    EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1). The returned values
    are the mean and p95 of masked valid pixels.
    """
    evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + 1e-8)
    return compute_stats(evi, mask, "evi")


def compute_ndmi(nir: np.ndarray, swir1: np.ndarray, mask: np.ndarray) -> Tuple[float, float]:
    """Compute NDMI stats from NIR and SWIR1 arrays.

    NDMI = (NIR - SWIR1) / (NIR + SWIR1). The returned values are the mean and
    p95 of masked valid pixels.
    """
    ndmi = (nir - swir1) / (nir + swir1 + 1e-8)
    return compute_stats(ndmi, mask, "ndmi")


def compute_ndwi(green: np.ndarray, nir: np.ndarray, mask: np.ndarray) -> Tuple[float, float]:
    """Compute NDWI stats from green and NIR arrays.

    NDWI = (Green - NIR) / (Green + NIR). The returned values are the mean and
    p95 of masked valid pixels.
    """
    ndwi = (green - nir) / (green + nir + 1e-8)
    return compute_stats(ndwi, mask, "ndwi")


def compute_mndwi(green: np.ndarray, swir1: np.ndarray, mask: np.ndarray) -> Tuple[float, float]:
    """Compute MNDWI stats from green and SWIR1 arrays.

    MNDWI = (Green - SWIR1) / (Green + SWIR1). The returned values are the mean
    and p95 of masked valid pixels.
    """
    mndwi = (green - swir1) / (green + swir1 + 1e-8)
    return compute_stats(mndwi, mask, "mndwi")
