"""Utility helpers for ingestion."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def safe_write_text(path: Path, text: str) -> None:
    """Write text atomically by replacing a temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def compute_fingerprint(payload: Dict[str, Any]) -> str:
    """Stable fingerprint for caching decisions.

    Include anything that changes outputs (bbox, dates, thresholds, mask rules,
    script version, etc.).
    """
    b = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()
