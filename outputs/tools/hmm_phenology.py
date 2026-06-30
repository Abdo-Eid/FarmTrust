"""Deterministic 4-state Gaussian HMM phenology decoder (research cross-check).

This is a *cross-check* for the deterministic peak/trough detector in
:mod:`farmtrust_core.seasonal.seasons`. It is NOT the production source of truth:
it never changes ``season_windows.json`` and nothing in scoring consumes it. Its
output is provenance ``isolated_research_cross_check`` (T-11).

The field is, on each day, in one of four hidden phenological phases::

    LOW (bare/dormant)  RISING (green-up)  HIGH (peak)  DECLINING (senescence)

We observe only [NDVI value, NDVI slope] and infer the phase per day. Contiguous
RISING -> HIGH -> DECLINING runs are the crop cycles.

Determinism: the model is trained by Baum-Welch (EM) from a FIXED initialization
(fixed state means, sticky transitions, uniform start, data-variance) for a fixed
number of iterations. There is no RNG anywhere in this module, so the same input
always yields byte-identical output. (The original exploration script seeded RNG
only in its ``__main__`` demo, never in the library.)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

# Flat/short-series guard: below this NDVI peak-to-trough range we declare the
# field dormant (all LOW, no cycles) rather than letting EM invent a HIGH state.
HMM_MIN_NDVI_RANGE = 0.144  # aligns with seasons.MIN_CYCLE_AMPLITUDE_NDVI
HMM_MIN_OBSERVATIONS = 6
HMM_ITERATIONS = 30
HMM_STICKY_TRANSITION = 0.04
VARIANCE_FLOOR = 1e-3
STD_FLOOR = 1e-6
PROVENANCE = "isolated_research_cross_check"

# Fixed initial state means in standardized [value, slope] space.
INIT_STATE_MEANS = np.array(
    [
        [-1.2, 0.0],  # LOW       : low value,  flat
        [0.0, 1.6],  # RISING    : mid value,  rising
        [1.3, 0.0],  # HIGH      : high value, flat
        [0.0, -1.6],  # DECLINING : mid value,  falling
    ]
)


@dataclass(frozen=True)
class HmmCycle:
    sos_date: date
    pos_date: date
    eos_date: date
    peak_ndvi: float
    lifecycle_status: str
    duration_days: int


@dataclass(frozen=True)
class HmmResult:
    dates: list[date]
    states: list[str]
    cycles: list[HmmCycle]
    has_high_state: bool
    n_iter: int
    converged: bool
    method: str = "gaussian_hmm_4state_value_slope"
    provenance: str = PROVENANCE


def _log_gaussian(x: np.ndarray, mean: np.ndarray, var: np.ndarray) -> np.ndarray:
    diff = x - mean
    return -0.5 * np.sum(diff * diff / var + np.log(2 * np.pi * var), axis=1)


def _logsumexp(values: np.ndarray, axis: int) -> np.ndarray:
    peak = np.max(values, axis=axis, keepdims=True)
    return peak + np.log(np.sum(np.exp(values - peak), axis=axis, keepdims=True))


def _fit_hmm(x: np.ndarray, init_means: np.ndarray, n_iter: int):
    t_len, _ = x.shape
    k = len(init_means)
    means = init_means.astype(float).copy()
    var = np.tile(x.var(0) + 1e-2, (k, 1))
    transition = np.full((k, k), HMM_STICKY_TRANSITION)
    np.fill_diagonal(transition, 1 - HMM_STICKY_TRANSITION * (k - 1))
    start = np.full(k, 1.0 / k)

    for _ in range(n_iter):
        log_b = np.stack([_log_gaussian(x, means[i], var[i]) for i in range(k)], axis=1)
        log_a = np.log(transition + 1e-12)
        log_start = np.log(start + 1e-12)

        forward = np.zeros((t_len, k))
        forward[0] = log_start + log_b[0]
        for t in range(1, t_len):
            forward[t] = log_b[t] + _logsumexp(forward[t - 1][:, None] + log_a, axis=0).ravel()
        backward = np.zeros((t_len, k))
        for t in range(t_len - 2, -1, -1):
            backward[t] = _logsumexp(
                log_a + log_b[t + 1][None, :] + backward[t + 1][None, :], axis=1
            ).ravel()

        gamma = np.exp((forward + backward) - _logsumexp(forward + backward, axis=1))
        xi = np.zeros((k, k))
        for t in range(t_len - 1):
            m = forward[t][:, None] + log_a + log_b[t + 1][None, :] + backward[t + 1][None, :]
            xi += np.exp(m - _logsumexp(m.reshape(1, -1), axis=1))

        start = gamma[0] / gamma[0].sum()
        transition = xi / (gamma[:-1].sum(0)[:, None] + 1e-12)
        transition /= transition.sum(1, keepdims=True)
        for i in range(k):
            weight = gamma[:, i]
            total = weight.sum() + 1e-12
            means[i] = (weight[:, None] * x).sum(0) / total
            var[i] = (weight[:, None] * (x - means[i]) ** 2).sum(0) / total + VARIANCE_FLOOR
    return means, var, transition, start


def _viterbi(x: np.ndarray, means: np.ndarray, var: np.ndarray, transition: np.ndarray, start: np.ndarray):
    t_len, k = len(x), len(means)
    log_b = np.stack([_log_gaussian(x, means[i], var[i]) for i in range(k)], axis=1)
    log_a = np.log(transition + 1e-12)
    log_start = np.log(start + 1e-12)
    delta = np.zeros((t_len, k))
    back = np.zeros((t_len, k), int)
    delta[0] = log_start + log_b[0]
    for t in range(1, t_len):
        scored = delta[t - 1][:, None] + log_a
        back[t] = scored.argmax(0)
        delta[t] = log_b[t] + scored.max(0)
    path = np.zeros(t_len, int)
    path[-1] = int(delta[-1].argmax())
    for t in range(t_len - 2, -1, -1):
        path[t] = back[t + 1][path[t + 1]]
    return path


def _label_states(means: np.ndarray) -> dict[int, str]:
    order = np.argsort(means[:, 0])
    low, high = int(order[0]), int(order[3])
    mids = order[1:3]
    rising = int(mids[int(np.argmax(means[mids, 1]))])
    declining = int(mids[int(np.argmin(means[mids, 1]))])
    return {low: "LOW", rising: "RISING", high: "HIGH", declining: "DECLINING"}


def _extract_cycles(states: list[str], ndvi: np.ndarray, dates: list[date]) -> list[HmmCycle]:
    n = len(states)
    cycles: list[HmmCycle] = []
    i = 0
    while i < n:
        if states[i] != "HIGH":
            i += 1
            continue
        high_start = i
        while i < n and states[i] == "HIGH":
            i += 1
        high_end = i - 1

        start = high_start
        while start > 0 and states[start - 1] in ("RISING", "HIGH"):
            start -= 1
        end = high_end
        while end < n - 1 and states[end + 1] in ("DECLINING", "HIGH"):
            end += 1

        pos = high_start + int(np.argmax(ndvi[high_start : high_end + 1]))
        open_left = start == 0 and states[0] in ("RISING", "HIGH")
        open_right = end == n - 1 and states[n - 1] in ("DECLINING", "HIGH")
        if open_left and open_right:
            lifecycle = "open_both"
        elif open_left:
            lifecycle = "open_left"
        elif open_right:
            lifecycle = "open_right"
        else:
            lifecycle = "complete"

        cycles.append(
            HmmCycle(
                sos_date=dates[start],
                pos_date=dates[pos],
                eos_date=dates[end],
                peak_ndvi=float(ndvi[pos]),
                lifecycle_status=lifecycle,
                duration_days=(dates[end] - dates[start]).days,
            )
        )
    return cycles


def decode_phenology(
    dates: list[date],
    ndvi: list[float],
    *,
    n_iter: int = HMM_ITERATIONS,
) -> HmmResult:
    """Decode per-day phenology phases and derive HMM cycles from a daily curve."""
    z = np.asarray(ndvi, dtype=float)
    n = len(z)

    if n < HMM_MIN_OBSERVATIONS or float(np.ptp(z)) < HMM_MIN_NDVI_RANGE:
        # Flat / dormant / too short: declare LOW everywhere, no cycles. This is
        # the guard that prevents EM from inventing a spurious HIGH state.
        return HmmResult(
            dates=list(dates),
            states=["LOW"] * n,
            cycles=[],
            has_high_state=False,
            n_iter=0,
            converged=False,
        )

    slope = np.gradient(z)
    features = np.column_stack([z, slope])
    mean = features.mean(0)
    std = features.std(0)
    std = np.where(std < STD_FLOOR, 1.0, std)
    standardized = (features - mean) / std

    means, var, transition, start = _fit_hmm(standardized, INIT_STATE_MEANS, n_iter)
    path = _viterbi(standardized, means, var, transition, start)
    names = _label_states(means)
    states = [names[int(s)] for s in path]
    cycles = _extract_cycles(states, z, list(dates))

    return HmmResult(
        dates=list(dates),
        states=states,
        cycles=cycles,
        has_high_state="HIGH" in states,
        n_iter=n_iter,
        converged=True,
    )
