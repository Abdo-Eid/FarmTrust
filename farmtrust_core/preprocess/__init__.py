"""Time-series preprocessing utilities."""

from .analysis_curve import (
    AnalysisCurveResult,
    SMOOTHING_METHOD_NAME,
    TARGET_SMOOTHING_DAYS,
    build_analysis_curves,
)
from .gaps import (
    build_confidence_inputs,
    classify_gap_risk,
    compute_gap_metrics,
    compute_gap_windows,
)
from .pipeline import (
    REQUIRED_COLUMNS,
    build_preprocess_artifacts,
    load_ingestion_observations,
    write_preprocess_outputs,
)
from .smoothing import smoothing_metadata

__all__ = [
    "REQUIRED_COLUMNS",
    "SMOOTHING_METHOD_NAME",
    "TARGET_SMOOTHING_DAYS",
    "AnalysisCurveResult",
    "build_analysis_curves",
    "build_confidence_inputs",
    "classify_gap_risk",
    "build_preprocess_artifacts",
    "compute_gap_metrics",
    "compute_gap_windows",
    "load_ingestion_observations",
    "smoothing_metadata",
    "write_preprocess_outputs",
]
