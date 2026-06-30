"""Published provenance metadata for the analysis-curve smoother.

The smoother itself lives in :mod:`farmtrust_core.preprocess.analysis_curve`
(a quality-weighted Whittaker-Eilers smoother on a regular daily grid). This
module exposes the metadata describing that smoother, plus thin re-exports so
existing ``from farmtrust_core.preprocess.smoothing import ...`` call sites keep
working.

The previous implementation (a per-point local polynomial fit on the integer
observation index, mislabeled Savitzky-Golay, plus an unused gap-aware
median/weighted-mean smoother) has been removed.
"""

from __future__ import annotations

from typing import Any

from .analysis_curve import (
    ANALYSIS_INCLUSION_VALID_FRACTION,
    ANALYSIS_WEIGHT_FLOOR,
    LAMBDA_MAX,
    LAMBDA_MIN,
    LAMBDA_SELECTION_METHOD,
    SMOOTHING_METHOD_NAME,
    TARGET_SMOOTHING_DAYS,
    WHITTAKER_DIFFERENCE_ORDER,
    AnalysisCurveResult,
    build_analysis_curves,
    fill_at_observations,
    sample_curve_at_observations,
)

__all__ = [
    "SMOOTHING_METHOD_NAME",
    "AnalysisCurveResult",
    "build_analysis_curves",
    "fill_at_observations",
    "sample_curve_at_observations",
    "smoothing_metadata",
]


def smoothing_metadata(result: AnalysisCurveResult) -> dict[str, Any]:
    """Provenance metadata describing the analysis curve that actually ran.

    Written verbatim into ``quality_metrics.json``. These keys are descriptive
    provenance only (no downstream code consumes them), so they can evolve with
    the smoother.
    """
    return {
        "smoothing_method": SMOOTHING_METHOD_NAME,
        "smoother_family": "weighted_whittaker_eilers",
        "whittaker_difference_order": WHITTAKER_DIFFERENCE_ORDER,
        "lambda_selection_method": LAMBDA_SELECTION_METHOD,
        "target_smoothing_days": TARGET_SMOOTHING_DAYS,
        "selected_lambda": round(float(result.selected_lambda), 6),
        "lambda_selection_reason": result.lambda_selection_reason,
        "lambda_min": LAMBDA_MIN,
        "lambda_max": LAMBDA_MAX,
        "lambda_shared_across_indices": True,
        "lambda_anchor_index": "ndvi",
        "analysis_inclusion_valid_fraction": ANALYSIS_INCLUSION_VALID_FRACTION,
        "analysis_weight_floor": ANALYSIS_WEIGHT_FLOOR,
        "weighting_policy": "valid_fraction_clipped",
        "analysis_grid": "regular_daily_from_first_to_last_observed_date",
        "creates_synthetic_timestamps": True,
        "smooths_only_usable_observations": False,
        "interpolation_policy": "linear_fill_between_inclusion_gated_anchors_then_whittaker",
        "fill_policy": "fill_all_observed_timestamps_from_analysis_anchors",
        "analysis_curve_source": (
            "model_derived_weighted_whittaker_daily_curve_sampled_at_observations"
        ),
        "analysis_curve_direct_evidence": False,
        "envelope_reweighting": False,
    }
