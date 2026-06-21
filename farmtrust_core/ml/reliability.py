"""Parcel and data reliability features for agricultural activity models."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


RELIABILITY_FEATURE_NAMES = [
    "area_ha",
    "estimated_s2_pixel_count",
    "valid_observation_count",
    "mean_valid_fraction",
    "gap_ratio",
    "max_gap_days",
    "geometry_compactness",
    "small_parcel_flag",
    "mixed_pixel_risk",
]


def load_reliability_features(data_root: str | Path, aoi_id: str) -> dict[str, float]:
    """Compute reliability features from existing run/preprocess artifacts."""
    root = Path(data_root)
    quality_path = root / "preprocess" / aoi_id / "quality_metrics.json"
    metadata_path = root / aoi_id / "run_metadata.json"
    smoothed_path = root / "preprocess" / aoi_id / "ndvi_smoothed.csv"

    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    area_ha = _area_ha(metadata)
    estimated_pixels = area_ha * 100.0 if area_ha > 0 else 0.0

    mean_valid_fraction = 0.0
    if smoothed_path.exists():
        df = pd.read_csv(smoothed_path)
        usable = df[df["is_usable"].astype(str).str.lower().isin(["true", "1"])]
        if not usable.empty:
            mean_valid_fraction = float(usable["valid_fraction"].mean())

    return {
        "area_ha": float(area_ha),
        "estimated_s2_pixel_count": float(estimated_pixels),
        "valid_observation_count": float(quality.get("usable_observation_count", 0.0)),
        "mean_valid_fraction": mean_valid_fraction,
        "gap_ratio": float(quality.get("gap_ratio", 0.0)),
        "max_gap_days": float(quality.get("max_gap_days", 0.0)),
        "geometry_compactness": 1.0,
        "small_parcel_flag": 1.0 if 0.0 < area_ha < 0.5 else 0.0,
        "mixed_pixel_risk": 1.0 if 0.0 < estimated_pixels < 50.0 else 0.0,
    }


def _area_ha(metadata: dict[str, Any]) -> float:
    if metadata.get("area_ha") is not None:
        return float(metadata["area_ha"])
    bbox = metadata.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        min_lon, min_lat, max_lon, max_lat = [float(value) for value in bbox]
        center_lat = (min_lat + max_lat) / 2.0
        meters_per_degree_lon = 111_320.0 * math.cos(math.radians(center_lat))
        meters_per_degree_lat = 111_320.0
        width_m = abs(max_lon - min_lon) * meters_per_degree_lon
        height_m = abs(max_lat - min_lat) * meters_per_degree_lat
        return max(width_m * height_m / 10_000.0, 0.0)
    return 0.0
