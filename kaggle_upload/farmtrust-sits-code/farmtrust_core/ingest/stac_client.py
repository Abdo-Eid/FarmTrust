"""STAC client helpers for ingestion."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from pystac_client import Client


def _try_import_planetary_computer():
    """Soft-import planetary_computer; return module or None if not installed."""
    try:
        return importlib.import_module("planetary_computer")
    except Exception:
        return None


def compute_start_date(end_dt: datetime, months: int) -> datetime:
    """Subtract months from end_dt using exact calendar math (dateutil) or 30-day fallback."""
    try:
        from dateutil.relativedelta import relativedelta
        return end_dt - relativedelta(months=months)
    except Exception:
        return end_dt - timedelta(days=months * 30)


def open_client(api_url: str, endpoint_name: str) -> Client:
    """Open STAC client; for Planetary Computer, apply sign_inplace to auto-renew SAS URL tokens."""
    pc = _try_import_planetary_computer()
    if endpoint_name == "planetary_computer" and pc is not None:
        return Client.open(api_url, modifier=pc.sign_inplace)
    return Client.open(api_url)


def stac_search_items(
    endpoints: List[Dict[str, str]],
    collection: str,
    intersects_geojson: Dict[str, Any],
    datetime_range: str,
    limit: int,
    query: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Any], str]:
    """Search STAC endpoints in order, returning the first non-empty result.

    Returns (items, endpoint_name). Items are pystac Item objects.
    Returns ([], "") if all endpoints fail or return nothing.
    """
    for ep in endpoints:
        try:
            client = open_client(ep["api_url"], ep["name"])
            search = client.search(
                collections=[collection],
                intersects=intersects_geojson,
                datetime=datetime_range,
                limit=limit,
                query=query,
            )
            items = sorted(list(search.items()), key=lambda x: x.datetime)
            if items:
                return items, ep["name"]
        except Exception:
            continue

    return [], ""
