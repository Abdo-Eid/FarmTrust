"""Weighted Whittaker-Eilers analysis curve on a regular daily grid.

This is the model-derived "analysis curve" used for vegetation activity-window
detection. It replaces the old per-point index-domain polynomial smoother, which
fit on the integer observation index rather than real time and therefore
distorted irregularly-sampled, cloud-gapped Sentinel-2 series.

Design (see plan "Part A"):

* Build a regular **daily** grid spanning the first..last observed UTC date.
* Place each observation on its day with a quality **weight** derived from
  ``valid_fraction`` (0 on unobserved days). The analysis curve uses a *looser*
  inclusion gate than the strict 0.90 evidence/usable flag -- the strict gate
  still governs gap/confidence evidence elsewhere; this only shapes the curve.
* Solve the penalized least-squares system ``(W + lam * D^T D) z = W y`` with a
  2nd-order difference penalty ``D`` (banded, symmetric positive definite) using
  :func:`scipy.linalg.solveh_banded`.
* Choose ``lam`` from a **phenology smoothing timescale in days** -- a physical
  constant of crop phenology (the same ~few-week vegetation response everywhere),
  not a value fit to any one field. For a 2nd-order Whittaker on a daily grid the
  half-power period ``T`` relates to ``lam`` as ``lam = (T / 2*pi)**4``, so a
  ~45-day smoothing window gives ``lam ~= 2600`` -- right in the sweet spot the
  Menofia exploration found by hand (lam=3000), but justified by timescale rather
  than tuned to that parcel.

  Plain generalized cross-validation (GCV) was evaluated and rejected as the
  default: on daily-gridded NDVI it systematically undersmooths (its minimum sits
  at lam~=1-10, fitting noise and cloud dips with ~150 effective DOF instead of
  ~30). :func:`select_lambda_gcv` is kept as an available alternative for
  experiments, but the timescale rule is the default.

Everything here is deterministic: no RNG, no optimizer state, fixed grids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Mapping, Sequence

import numpy as np
from scipy.linalg import solveh_banded

SMOOTHING_METHOD_NAME = "weighted_whittaker_eilers_daily_grid"
WHITTAKER_DIFFERENCE_ORDER = 2

# Default smoothing timescale (real days). Crop phenology responds over a few
# weeks; this is an agronomic constant, not an AOI-specific tuning. lambda is
# derived from it via lambda = (T / 2*pi)**(2*order).
TARGET_SMOOTHING_DAYS = 45.0
LAMBDA_SELECTION_METHOD = "phenology_timescale_fixed_day_window"

LAMBDA_MIN = 1.0
LAMBDA_MAX = 1.0e5
DEFAULT_LAMBDA = 1000.0  # documented fallback for short/degenerate series

# Fixed, deterministic candidate grid for the optional GCV selector.
LAMBDA_GRID = tuple(float(x) for x in np.logspace(0.0, 5.0, 31))

# The analysis curve includes more observations than the strict 0.90 evidence
# gate, each down-weighted by valid_fraction. The strict gate is unchanged and
# still governs usable_observation_count / gap_ratio / gap_risk elsewhere.
ANALYSIS_INCLUSION_VALID_FRACTION = 0.30
ANALYSIS_WEIGHT_FLOOR = 0.1

# Guards.
GCV_MIN_OBSERVATIONS = 5  # need enough anchors for cross-validation to be meaningful
GCV_MAX_GRID_DAYS = 2600  # above this, the full-inverse trace gets expensive -> default lam

# The anchor index whose lambda is reused for the others.
ANCHOR_INDEX = "ndvi"


@dataclass(frozen=True)
class AnalysisCurveResult:
    start_date: date
    n_days: int
    selected_lambda: float
    lambda_selection_reason: str
    curves: dict[str, list[float]]  # full daily series per index
    is_observed_day: list[bool]
    analysis_weight: list[float]  # per grid day (0 on unobserved days)

    def day_index(self, moment: datetime) -> int:
        return (moment.astimezone(timezone.utc).date() - self.start_date).days


def _utc_date(moment: datetime) -> date:
    return moment.astimezone(timezone.utc).date()


def _second_difference_penalty_bands(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the 0th/1st/2nd diagonals of ``D^T D`` for a 2nd-order difference D.

    ``D`` is the (n-2, n) second-difference operator; ``P = D^T D`` is symmetric
    penta-diagonal and positive semi-definite (nullspace = linear functions).
    """
    if n < 3:
        # Degenerate; caller handles via guards. Return zero penalty.
        return np.zeros(n), np.zeros(max(n - 1, 0)), np.zeros(max(n - 2, 0))
    e = np.ones(n - 2)
    # Build D as a banded operator and form P = D^T D explicitly via its stencil.
    main = np.empty(n)
    main[0] = 1.0
    main[1] = 5.0 if n > 3 else 2.0
    main[2:-2] = 6.0
    main[-1] = 1.0
    main[-2] = 5.0 if n > 3 else main[-2]
    if n == 3:
        main[:] = [1.0, 4.0, 1.0]
    off1 = np.empty(n - 1)
    off1[0] = -2.0
    off1[1:-1] = -4.0
    off1[-1] = -2.0
    if n == 3:
        off1[:] = [-2.0, -2.0]
    off2 = np.ones(n - 2) * float(e[0]) if n - 2 > 0 else np.zeros(0)
    return main, off1, off2


def _banded_ab(weights: np.ndarray, lam: float, bands: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    """Assemble the symmetric-banded (upper) form of ``diag(w) + lam*P``."""
    main, off1, off2 = bands
    n = len(weights)
    ab = np.zeros((3, n))
    ab[2] = weights + lam * main
    if n >= 2:
        ab[1, 1:] = lam * off1
    if n >= 3:
        ab[0, 2:] = lam * off2
    return ab


def whittaker_smooth(
    values: Sequence[float],
    weights: Sequence[float],
    lam: float,
) -> np.ndarray:
    """Solve the weighted Whittaker system ``(W + lam*D^T D) z = W y``."""
    y = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    n = len(y)
    if n == 0:
        return np.zeros(0)
    if n < 3:
        # No 2nd-difference penalty possible; return the (weighted) data itself.
        return y.copy()
    bands = _second_difference_penalty_bands(n)
    ab = _banded_ab(w, float(lam), bands)
    return solveh_banded(ab, w * y, lower=False)


def lambda_for_timescale(
    target_days: float,
    *,
    order: int = WHITTAKER_DIFFERENCE_ORDER,
) -> float:
    """Map a smoothing timescale (days) to a Whittaker lambda on a daily grid.

    For an order-``d`` difference penalty the smoother's half-power period ``T``
    satisfies ``lam * (2*pi/T)**(2*d) = 1`` in the low-frequency limit, hence
    ``lam = (T / (2*pi))**(2*d)``.
    """
    if target_days <= 0:
        raise ValueError("target_days must be positive")
    return float((target_days / (2.0 * np.pi)) ** (2 * order))


def select_lambda(target_days: float = TARGET_SMOOTHING_DAYS) -> tuple[float, str]:
    """Default lambda selection: derived from the phenology smoothing timescale."""
    lam = lambda_for_timescale(target_days)
    clamped = float(min(max(lam, LAMBDA_MIN), LAMBDA_MAX))
    return clamped, "phenology_timescale"


def _gcv_score(y: np.ndarray, w: np.ndarray, lam: float, bands) -> float:
    """Generalized cross-validation score (lower is better) for one lambda."""
    n = len(y)
    ab = _banded_ab(w, lam, bands)
    inv = solveh_banded(ab, np.eye(n), lower=False)  # (W + lam P)^{-1}
    z = inv @ (w * y)
    trace_h = float(np.sum(w * np.diag(inv)))  # tr(H), H = inv * W
    rss = float(np.sum(w * (y - z) ** 2))
    denom = (n - trace_h) ** 2
    if denom <= 1e-9:
        return float("inf")
    return n * rss / denom


def select_lambda_gcv(
    values: Sequence[float],
    weights: Sequence[float],
    *,
    grid: Sequence[float] = LAMBDA_GRID,
) -> tuple[float, str]:
    """Pick lambda by bounded GCV over a fixed grid. Deterministic.

    Returns ``(lambda, reason)``. Falls back to :data:`DEFAULT_LAMBDA` for short,
    degenerate, or very long series where GCV is not appropriate/affordable.
    """
    y = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    n = len(y)
    positive = int(np.count_nonzero(w > 0))

    if positive < GCV_MIN_OBSERVATIONS:
        return DEFAULT_LAMBDA, "default_degenerate"
    if n > GCV_MAX_GRID_DAYS:
        return DEFAULT_LAMBDA, "default_large_grid"

    bands = _second_difference_penalty_bands(n)
    best_lam = DEFAULT_LAMBDA
    best_score = float("inf")
    for lam in grid:
        score = _gcv_score(y, w, float(lam), bands)
        if score < best_score:  # first (smallest-lambda) argmin on ties
            best_score = score
            best_lam = float(lam)
    if not np.isfinite(best_score):
        return DEFAULT_LAMBDA, "default_no_finite_gcv"
    clamped = float(min(max(best_lam, LAMBDA_MIN), LAMBDA_MAX))
    reason = "gcv" if clamped == best_lam else "gcv_clamped"
    return clamped, reason


def compute_analysis_weights(
    valid_fractions: Sequence[float],
    *,
    inclusion_threshold: float = ANALYSIS_INCLUSION_VALID_FRACTION,
    floor: float = ANALYSIS_WEIGHT_FLOOR,
) -> list[float]:
    """Per-observation curve weight: 0 below the inclusion gate, else clipped vf."""
    weights: list[float] = []
    for value in valid_fractions:
        vf = float(value)
        if not np.isfinite(vf) or vf < inclusion_threshold:
            weights.append(0.0)
        else:
            weights.append(float(min(max(vf, floor), 1.0)))
    return weights


def _grid_arrays(
    timestamps: Sequence[datetime],
    index_values: Mapping[str, Sequence[float]],
    obs_weights: Sequence[float],
) -> tuple[date, int, dict[str, np.ndarray], np.ndarray, np.ndarray]:
    """Project observations onto a daily grid (weighted-mean same-day collisions)."""
    dates = [_utc_date(ts) for ts in timestamps]
    start = min(dates)
    end = max(dates)
    n_days = (end - start).days + 1

    day_index = np.array([(d - start).days for d in dates], dtype=int)
    weight_sum = np.zeros(n_days)
    weight_count = np.zeros(n_days)
    value_grids: dict[str, np.ndarray] = {}
    wvalue_sum: dict[str, np.ndarray] = {}

    for name, values in index_values.items():
        wvalue_sum[name] = np.zeros(n_days)
        value_grids[name] = np.zeros(n_days)

    for i, gi in enumerate(day_index):
        w = float(obs_weights[i])
        weight_sum[gi] += w
        weight_count[gi] += 1.0
        for name, values in index_values.items():
            wvalue_sum[name][gi] += w * float(values[i])

    observed = weight_count > 0
    grid_weight = np.zeros(n_days)
    # Effective day weight = mean of contributing obs weights (avoids over-counting
    # repeated same-day acquisitions); value = weight-weighted mean on that day.
    grid_weight[observed] = weight_sum[observed] / weight_count[observed]
    for name in index_values:
        gv = value_grids[name]
        pos = observed & (weight_sum > 0)
        gv[pos] = wvalue_sum[name][pos] / weight_sum[pos]
        # Observed-but-zero-weight days keep value 0 and weight 0 (treated as gaps).
        value_grids[name] = gv

    return start, n_days, value_grids, grid_weight, observed


def build_analysis_curves(
    *,
    timestamps: Sequence[datetime],
    index_values: Mapping[str, Sequence[float]],
    valid_fractions: Sequence[float],
    lam: float | None = None,
    target_smoothing_days: float = TARGET_SMOOTHING_DAYS,
) -> AnalysisCurveResult:
    """Build the daily Whittaker analysis curve for every provided index.

    ``index_values`` maps an index name (e.g. ``"ndvi"``) to its raw values at the
    observation timestamps. Lambda is derived once from the phenology smoothing
    timescale and reused across indices, unless an explicit ``lam`` is supplied
    (for reproducible re-derivation by the detector / comparison harness).
    """
    if not timestamps:
        raise ValueError("Cannot build an analysis curve without observations")
    if ANCHOR_INDEX not in index_values:
        raise ValueError(f"index_values must include the anchor index '{ANCHOR_INDEX}'")

    obs_weights = compute_analysis_weights(valid_fractions)

    # NaN-safety: a fully-clouded acquisition can carry a non-finite value (it
    # usually also has valid_fraction 0). Drop such observations from the fit for
    # every index (shared weights), and sanitize values so 0*nan never appears.
    finite_mask = np.ones(len(timestamps), dtype=bool)
    sanitized: dict[str, list[float]] = {}
    for name, values in index_values.items():
        arr = np.asarray(values, dtype=float)
        finite_mask &= np.isfinite(arr)
        sanitized[name] = np.nan_to_num(arr, nan=0.0).tolist()
    obs_weights = [w if finite_mask[i] else 0.0 for i, w in enumerate(obs_weights)]

    if not any(w > 0 for w in obs_weights):
        raise ValueError("Cannot build an analysis curve without finite usable observations")

    start, n_days, value_grids, grid_weight, observed = _grid_arrays(
        timestamps, sanitized, obs_weights
    )

    if lam is None:
        selected_lambda, reason = select_lambda(target_smoothing_days)
    else:
        selected_lambda, reason = float(lam), "explicit"

    curves: dict[str, list[float]] = {}
    for name, y in value_grids.items():
        z = whittaker_smooth(y, grid_weight, selected_lambda)
        curves[name] = [float(v) for v in z]

    return AnalysisCurveResult(
        start_date=start,
        n_days=n_days,
        selected_lambda=float(selected_lambda),
        lambda_selection_reason=reason,
        curves=curves,
        is_observed_day=[bool(v) for v in observed],
        analysis_weight=[float(v) for v in grid_weight],
    )


def sample_curve_at_observations(
    result: AnalysisCurveResult,
    timestamps: Sequence[datetime],
    index_name: str,
) -> list[float]:
    """Sample a daily curve at each observation timestamp (obs days are grid points)."""
    curve = result.curves[index_name]
    samples: list[float] = []
    for ts in timestamps:
        idx = result.day_index(ts)
        idx = min(max(idx, 0), result.n_days - 1)
        samples.append(float(curve[idx]))
    return samples


def fill_at_observations(
    timestamps: Sequence[datetime],
    values: Sequence[float],
    valid_fractions: Sequence[float],
    *,
    inclusion_threshold: float = ANALYSIS_INCLUSION_VALID_FRACTION,
) -> list[float]:
    """Linear interpolation of analysis anchors at observed timestamps (real days).

    Produces the pre-smoothing ``*_filled`` columns. Anchors are observations whose
    ``valid_fraction`` clears the inclusion gate and whose value is finite.
    """
    if not (len(timestamps) == len(values) == len(valid_fractions)):
        raise ValueError("timestamps, values, and valid_fractions must have the same length")
    if not values:
        return []

    origin = _utc_date(timestamps[0])
    x = np.array([(_utc_date(ts) - origin).days for ts in timestamps], dtype=float)
    anchor_idx = [
        i
        for i, (v, vf) in enumerate(zip(values, valid_fractions))
        if np.isfinite(float(v)) and float(vf) >= inclusion_threshold
    ]
    if not anchor_idx:
        raise ValueError("Cannot fill analysis values without usable finite observations")
    if len(anchor_idx) == 1:
        return [float(values[anchor_idx[0]]) for _ in values]

    anchor_x = x[anchor_idx]
    anchor_y = np.array([float(values[i]) for i in anchor_idx], dtype=float)
    filled = np.interp(x, anchor_x, anchor_y)
    return [float(v) for v in filled]
