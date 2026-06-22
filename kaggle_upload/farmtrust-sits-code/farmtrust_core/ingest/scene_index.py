"""Per-AOI scene registry: load, save, and cache-skip logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from farmtrust_core.ingest.utils import safe_write_text, utc_now_iso


def load_scenes_index(path: Path) -> Dict[str, Any]:
    """
    Load or initialize the per-AOI scene registry.

    Returns a minimal skeleton dict on first run (file doesn't exist yet).
    Validates the schema so corrupt files fail fast instead of silently producing bad output.
    """
    if not path.exists():
        return {"schema": "g15f.scenes_index.v1", "created_at": utc_now_iso(), "updated_at": utc_now_iso(), "scenes": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "scenes" not in data:
        raise ValueError(f"Invalid scenes_index.json format: {path}")
    if not isinstance(data["scenes"], dict):
        raise ValueError("scenes_index.json 'scenes' must be an object keyed by item_id")
    return data


def save_scenes_index(path: Path, index: Dict[str, Any]) -> None:
    """
    Write scenes index with updated timestamp.

    Updates 'updated_at' before writing so every save is auditable.
    Uses safe_write_text (atomic rename) to avoid corrupt JSON on crash mid-write.
    """
    index["updated_at"] = utc_now_iso()
    safe_write_text(path, json.dumps(index, indent=2, sort_keys=True))


def chips_complete(chip_dir: Path) -> bool:
    """All 6 band chips plus manifest.json must exist; partial download is treated as missing."""
    expected = ["SCL.tif", "B02.tif", "B03.tif", "B04.tif", "B08.tif", "B11.tif", "manifest.json"]
    return all((chip_dir / f).exists() for f in expected)


def should_skip_scene(index: Dict[str, Any], item_id: str, chip_dir: Path, fingerprint: str) -> bool:
    """
    Skip if:
      - chip files exist AND
      - index contains scene with same fingerprint AND
      - status == "ok"
    """
    scene = index.get("scenes", {}).get(item_id)
    if not scene:
        return False
    if scene.get("fingerprint") != fingerprint:
        return False
    if scene.get("status") != "ok":
        return False
    return chips_complete(chip_dir)
