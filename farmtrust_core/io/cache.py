"""Local cache helpers for fast iteration."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from farmtrust_core.ingest.utils import compute_fingerprint, utc_now_iso


def cache_enabled() -> bool:
    return os.environ.get("STAC_CACHE_DISABLE", "0").strip() not in ("1", "true", "TRUE", "yes", "YES")


def cache_ttl_hours() -> int:
    v = os.environ.get("STAC_CACHE_TTL_HOURS", "72").strip()
    try:
        return max(0, int(v))
    except Exception:
        return 72


def cache_path(cache_dir: Path, key: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"


def read_cache(cache_dir: Path, query_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not cache_enabled():
        return None

    key = compute_fingerprint(query_obj)
    path = cache_path(cache_dir, key)
    if not path.exists():
        return None

    obj = json.loads(path.read_text(encoding="utf-8"))
    ttl = timedelta(hours=cache_ttl_hours())
    saved_at = datetime.fromisoformat(obj.get("saved_at"))
    if ttl.total_seconds() > 0 and datetime.now(timezone.utc) - saved_at > ttl:
        return None
    return obj


def write_cache(cache_dir: Path, query_obj: Dict[str, Any], payload: Dict[str, Any]) -> None:
    if not cache_enabled():
        return
    key = compute_fingerprint(query_obj)
    path = cache_path(cache_dir, key)
    out = {"saved_at": utc_now_iso(), **payload}
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
