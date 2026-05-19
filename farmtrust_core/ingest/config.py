"""Config and parsing helpers for ingestion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional


def parse_bbox(value: str) -> List[float]:
    """Parse bbox from a comma-separated string into [min_lon, min_lat, max_lon, max_lat].

    Input is expected in EPSG:4326 order: min_lon,min_lat,max_lon,max_lat.
    Raises argparse.ArgumentTypeError on invalid format or non-numeric values.
    """
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be four comma-separated numbers")
    try:
        return [float(p) for p in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox values must be numbers") from exc


def normalize_bbox(value: object) -> List[float]:
    """Normalize bbox input from list or comma-separated string.

    Accepts either a list of four values or a string compatible with parse_bbox.
    Returns a list of floats; raises ValueError on unsupported inputs.
    """
    if isinstance(value, list):
        if len(value) != 4:
            raise ValueError("bbox list must have four numbers")
        return [float(v) for v in value]
    if isinstance(value, str):
        return parse_bbox(value)
    raise ValueError("bbox must be a list or a comma-separated string")


def parse_geometry(value: str) -> dict[str, Any]:
    """Parse a GeoJSON geometry from a JSON string or JSON file path."""
    candidate = Path(value)
    if candidate.exists():
        data = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        data = json.loads(value)
    return normalize_geometry(data)


def normalize_geometry(value: object) -> dict[str, Any]:
    """Validate and normalize a GeoJSON Polygon geometry."""
    if not isinstance(value, dict):
        raise ValueError("geometry must be a GeoJSON object")

    geometry = value.get("geometry") if value.get("type") == "Feature" else value
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a GeoJSON Polygon or Feature")
    if geometry.get("type") != "Polygon":
        raise ValueError("geometry must be a GeoJSON Polygon")

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("Polygon geometry must include coordinates")
    exterior = coordinates[0]
    if not isinstance(exterior, list) or len(exterior) < 4:
        raise ValueError("Polygon exterior ring must contain at least four points")
    for point in exterior:
        if not isinstance(point, list) or len(point) < 2:
            raise ValueError("Polygon points must be [lon, lat] pairs")
        float(point[0])
        float(point[1])

    return {
        "type": "Polygon",
        "coordinates": coordinates,
    }


def geometry_to_bbox(geometry: dict[str, Any]) -> List[float]:
    """Compute EPSG:4326 bbox from a normalized GeoJSON Polygon."""
    normalized = normalize_geometry(geometry)
    points = normalized["coordinates"][0]
    lons = [float(point[0]) for point in points]
    lats = [float(point[1]) for point in points]
    return [min(lons), min(lats), max(lons), max(lats)]


def default_dates() -> tuple[str, str]:
    """Return default (start_date, end_date) as last 30 days in UTC.

    Dates are ISO-8601 strings (YYYY-MM-DD) derived from current UTC time.
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    return start_date.isoformat(), end_date.isoformat()


def load_config(path: Optional[str]) -> dict:
    """Load JSON config from disk (returns empty dict when path is None).

    Ensures the file exists and the root object is a JSON object.
    """
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config must be a JSON object")
    return data
