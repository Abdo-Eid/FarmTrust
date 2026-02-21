"""Config and parsing helpers for ingestion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional


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
