"""Deterministic synthetic Sentinel-2-like phenology fixtures for tests.

These generators replace the old hand-built linear ramps (e.g. ``[0.12, 0.13,
0.15, ...]``) with curves that actually resemble field-mean Sentinel-2 NDVI:

* ~5-day nominal cadence with day jitter and injected cloud gaps,
* asymmetric green-up / senescence cycle shapes (not linear ramps),
* bare-soil baselines ~0.12-0.18 and crop peaks ~0.7-0.9,
* small Gaussian noise plus occasional negative "cloud dip" excursions on
  observations whose ``valid_fraction`` is low.

RNG is used **only here** (in tests), never in production code, and every
generator is fully seeded so fixtures are byte-reproducible.

The same fixtures feed both the smoother tests (``build_analysis_curves`` takes
``timestamps`` / ``index_values`` / ``valid_fractions``) and the detector / HMM
tests (which want ``SeasonalObservation``-shaped rows).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

EPOCH = datetime(2024, 1, 1, tzinfo=timezone.utc)

# Canonical index keys the generator emits.
INDEX_KEYS = ("ndvi", "evi", "ndmi", "ndwi", "mndwi")


@dataclass(frozen=True)
class Cycle:
    """One vegetation cycle as an asymmetric Gaussian bump on day-of-series axis."""

    peak_day: float
    amplitude: float
    rise_width: float
    fall_width: float


@dataclass(frozen=True)
class SyntheticSeries:
    """A generated series plus ground truth for invariant assertions."""

    timestamps: list[datetime]
    valid_fractions: list[float]
    raw: dict[str, list[float]]  # observed values (noise + cloud dips)
    clean: dict[str, list[float]]  # noise-free true curve sampled at observations
    true_peak_days: list[float]  # day offsets of injected cycle peaks
    base: float

    def date_for_day(self, day: float) -> datetime:
        return self.timestamps[0] + timedelta(days=float(day))


def _true_ndvi(days: np.ndarray, base: float, cycles: list[Cycle]) -> np.ndarray:
    """Bare-soil base plus asymmetric-Gaussian crop bumps, clipped to NDVI range."""
    value = np.full_like(days, float(base), dtype=float)
    for cycle in cycles:
        left = days < cycle.peak_day
        width = np.where(left, cycle.rise_width, cycle.fall_width)
        value = value + cycle.amplitude * np.exp(-0.5 * ((days - cycle.peak_day) / width) ** 2)
    return np.clip(value, 0.0, 0.97)


def _derive_indices(ndvi: np.ndarray, rng: np.random.Generator, *, noise_sd: float) -> dict[str, np.ndarray]:
    """Plausible companion indices tracking NDVI, each with independent small noise."""
    n = len(ndvi)

    def jitter(scale: float) -> np.ndarray:
        return rng.normal(0.0, noise_sd * scale, n)

    evi = np.clip(0.82 * ndvi + jitter(1.0), 0.0, 0.95)
    ndmi = np.clip(0.35 * ndvi - 0.04 + jitter(0.8), -0.4, 0.6)
    ndwi = np.clip(-0.32 * ndvi + 0.10 + jitter(0.8), -0.6, 0.4)
    mndwi = np.clip(-0.30 - 0.10 * ndvi + jitter(0.6), -0.7, -0.05)  # never wet -> no water signal
    return {"ndvi": ndvi, "evi": evi, "ndmi": ndmi, "ndwi": ndwi, "mndwi": mndwi}


def _sample_days(
    *,
    total_days: int,
    cadence_days: float,
    jitter_days: float,
    gaps: list[tuple[float, float]],
    rng: np.random.Generator,
) -> np.ndarray:
    """Irregular acquisition days: nominal cadence + jitter, minus cloud-gap windows."""
    days: list[float] = []
    day = 0.0
    while day <= total_days:
        offset = rng.uniform(-jitter_days, jitter_days) if jitter_days else 0.0
        candidate = min(max(day + offset, 0.0), float(total_days))
        if not any(start <= candidate <= end for start, end in gaps):
            days.append(round(candidate))
        day += cadence_days
    # De-duplicate same rounded day (same-day collisions are handled downstream).
    unique = sorted(set(days))
    return np.asarray(unique, dtype=float)


def make_phenology_series(
    *,
    cycles: list[Cycle],
    base: float = 0.14,
    total_days: int = 400,
    start: datetime = EPOCH,
    cadence_days: float = 5.0,
    jitter_days: float = 1.5,
    gaps: list[tuple[float, float]] | None = None,
    noise_sd: float = 0.015,
    cloud_dip_prob: float = 0.12,
    cloud_dip_magnitude: float = 0.18,
    seed: int = 0,
) -> SyntheticSeries:
    """Generate one deterministic Sentinel-2-like multi-index series."""
    rng = np.random.default_rng(seed)
    gaps = gaps or []

    obs_days = _sample_days(
        total_days=total_days,
        cadence_days=cadence_days,
        jitter_days=jitter_days,
        gaps=gaps,
        rng=rng,
    )
    timestamps = [start + timedelta(days=float(d)) for d in obs_days]

    clean_ndvi = _true_ndvi(obs_days, base, cycles)
    clean = _derive_indices(clean_ndvi, np.random.default_rng(seed + 1), noise_sd=0.0)

    # Observed values: clean curve + measurement noise.
    noisy_ndvi = clean_ndvi + rng.normal(0.0, noise_sd, len(obs_days))

    # Cloud dips: a subset of acquisitions are partly contaminated -> low valid
    # fraction AND a downward NDVI excursion (clouds depress greenness).
    valid_fractions = rng.uniform(0.9, 1.0, len(obs_days))
    dip_mask = rng.random(len(obs_days)) < cloud_dip_prob
    valid_fractions[dip_mask] = rng.uniform(0.2, 0.6, int(dip_mask.sum()))
    noisy_ndvi[dip_mask] -= rng.uniform(0.5, 1.0, int(dip_mask.sum())) * cloud_dip_magnitude
    noisy_ndvi = np.clip(noisy_ndvi, 0.0, 0.97)

    raw = _derive_indices(noisy_ndvi, np.random.default_rng(seed + 2), noise_sd=noise_sd)

    return SyntheticSeries(
        timestamps=timestamps,
        valid_fractions=[float(v) for v in valid_fractions],
        raw={k: [float(x) for x in v] for k, v in raw.items()},
        clean={k: [float(x) for x in v] for k, v in clean.items()},
        true_peak_days=[c.peak_day for c in cycles],
        base=base,
    )


# --------------------------------------------------------------------------
# Named scenarios. Each returns a SyntheticSeries; seeds are fixed per scenario.
# --------------------------------------------------------------------------


def single_complete_cycle(seed: int = 11) -> SyntheticSeries:
    """One fully-observed crop cycle peaking mid-series."""
    return make_phenology_series(
        cycles=[Cycle(peak_day=120.0, amplitude=0.62, rise_width=28.0, fall_width=36.0)],
        total_days=240,
        seed=seed,
    )


def two_cycles_with_gap(seed: int = 12) -> SyntheticSeries:
    """Two cycles separated by a real temporal gap straddling the bare-soil trough.

    The gap (days 150-185) drops observations between the cycles, so the two
    peaks are close in observation index but far apart in real days -- the case
    the old index-distance detector wrongly merged.
    """
    return make_phenology_series(
        cycles=[
            Cycle(peak_day=80.0, amplitude=0.60, rise_width=24.0, fall_width=30.0),
            Cycle(peak_day=250.0, amplitude=0.64, rise_width=26.0, fall_width=32.0),
        ],
        total_days=330,
        gaps=[(150.0, 185.0)],
        seed=seed,
    )


def open_left_cycle(seed: int = 13) -> SyntheticSeries:
    """Series begins with the canopy already near peak, then senesces (open-left)."""
    return make_phenology_series(
        cycles=[Cycle(peak_day=-10.0, amplitude=0.66, rise_width=30.0, fall_width=55.0)],
        total_days=180,
        seed=seed,
    )


def open_right_cycle(seed: int = 14) -> SyntheticSeries:
    """Series ends while greenness is still rising toward an unobserved peak (open-right)."""
    return make_phenology_series(
        cycles=[Cycle(peak_day=210.0, amplitude=0.66, rise_width=55.0, fall_width=30.0)],
        total_days=180,
        seed=seed,
    )


def berseem_multicut_sawtooth(seed: int = 15) -> SyntheticSeries:
    """One long clover cycle with several shallow cuts (sub-peaks).

    The cuts dip only partway down from the plateau and never return to bare
    soil, so a correct detector must report exactly ONE cycle, not several.
    """
    rng = np.random.default_rng(seed)
    total_days = 220
    obs_days = _sample_days(
        total_days=total_days, cadence_days=5.0, jitter_days=1.0, gaps=[], rng=rng
    )
    # Slow large bump (the crop) + shallow ripple (the cuts).
    bump = _true_ndvi(obs_days, 0.14, [Cycle(110.0, 0.60, 45.0, 50.0)])
    ripple = 0.07 * np.sin(2 * np.pi * obs_days / 28.0)
    plateau = bump > 0.45
    clean_ndvi = np.clip(bump + np.where(plateau, ripple, 0.0), 0.0, 0.97)

    timestamps = [EPOCH + timedelta(days=float(d)) for d in obs_days]
    valid_fractions = rng.uniform(0.9, 1.0, len(obs_days))
    noisy = np.clip(clean_ndvi + rng.normal(0.0, 0.012, len(obs_days)), 0.0, 0.97)
    clean = _derive_indices(clean_ndvi, np.random.default_rng(seed + 1), noise_sd=0.0)
    raw = _derive_indices(noisy, np.random.default_rng(seed + 2), noise_sd=0.012)
    return SyntheticSeries(
        timestamps=timestamps,
        valid_fractions=[float(v) for v in valid_fractions],
        raw={k: [float(x) for x in v] for k, v in raw.items()},
        clean={k: [float(x) for x in v] for k, v in clean.items()},
        true_peak_days=[110.0],
        base=0.14,
    )


def flat_fallow(seed: int = 16) -> SyntheticSeries:
    """Bare/fallow field: low flat NDVI with noise, no cycle at all."""
    return make_phenology_series(
        cycles=[],
        base=0.15,
        total_days=240,
        noise_sd=0.02,
        seed=seed,
    )


def single_winter_cycle(seed: int = 17) -> SyntheticSeries:
    """Short ~6-month series with one winter cycle (mirrors the sparse land AOI)."""
    return make_phenology_series(
        cycles=[Cycle(peak_day=95.0, amplitude=0.58, rise_width=26.0, fall_width=30.0)],
        total_days=180,
        start=datetime(2025, 12, 1, tzinfo=timezone.utc),
        cadence_days=5.0,
        jitter_days=1.0,
        seed=seed,
    )


def double_crop_two_year(seed: int = 18) -> SyntheticSeries:
    """~2 years, ~4 cycles with bare-soil troughs between them (mirrors aoi_demo_01)."""
    return make_phenology_series(
        cycles=[
            Cycle(peak_day=120.0, amplitude=0.66, rise_width=26.0, fall_width=30.0),
            Cycle(peak_day=300.0, amplitude=0.58, rise_width=30.0, fall_width=34.0),
            Cycle(peak_day=480.0, amplitude=0.68, rise_width=26.0, fall_width=30.0),
            Cycle(peak_day=660.0, amplitude=0.60, rise_width=32.0, fall_width=40.0),
        ],
        total_days=760,
        gaps=[(200.0, 224.0), (560.0, 585.0)],
        seed=seed,
    )
