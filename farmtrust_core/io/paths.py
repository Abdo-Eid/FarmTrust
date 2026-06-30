"""Path helpers for pipeline artifacts."""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    """Return the root directory for generated FarmTrust artifacts."""
    return Path(os.environ.get("FARMTRUST_DATA_DIR", "data"))


def aoi_dir(aoi_id: str, *, root: Path | None = None) -> Path:
    return (root or data_root()) / aoi_id


def preprocess_dir(aoi_id: str, *, root: Path | None = None) -> Path:
    return (root or data_root()) / "preprocess" / aoi_id


def seasonal_dir(aoi_id: str, *, root: Path | None = None) -> Path:
    return (root or data_root()) / "seasonal" / aoi_id


def assessment_dir(aoi_id: str, *, root: Path | None = None) -> Path:
    return (root or data_root()) / "assessment" / aoi_id


def timeseries_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return aoi_dir(aoi_id, root=root) / "indices_timeseries.csv"


def run_metadata_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return aoi_dir(aoi_id, root=root) / "run_metadata.json"


def smoothed_timeseries_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return preprocess_dir(aoi_id, root=root) / "ndvi_smoothed.csv"


def season_analysis_curve_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return preprocess_dir(aoi_id, root=root) / "season_analysis_curve.csv"


def quality_metrics_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return preprocess_dir(aoi_id, root=root) / "quality_metrics.json"


def season_windows_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return seasonal_dir(aoi_id, root=root) / "season_windows.json"


def land_assessment_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return assessment_dir(aoi_id, root=root) / "land_assessment.json"


def report_evidence_packet_path(aoi_id: str, *, root: Path | None = None) -> Path:
    return assessment_dir(aoi_id, root=root) / "report_evidence_packet.json"
