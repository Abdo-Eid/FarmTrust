"""Egypt agricultural-cycle calendar helpers for ML sequence building."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CYCLE_TEMPLATES = (
    {"name": "winter", "start_month": 11, "start_day": 1, "end_month": 4, "end_day": 30, "end_year_offset": 1},
    {"name": "summer", "start_month": 5, "start_day": 1, "end_month": 8, "end_day": 31, "end_year_offset": 0},
    {"name": "nile", "start_month": 9, "start_day": 1, "end_month": 10, "end_day": 31, "end_year_offset": 0},
)


def _as_utc_datetime(value: Any) -> datetime:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_templates(calendar_path: Path) -> tuple[dict[str, Any], ...]:
    if not calendar_path.exists():
        return DEFAULT_CYCLE_TEMPLATES

    payload = yaml.safe_load(calendar_path.read_text(encoding="utf-8")) or {}
    raw_cycles = payload.get("cycles", payload if isinstance(payload, list) else [])
    templates: list[dict[str, Any]] = []
    for raw in raw_cycles:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or raw.get("cycle") or "").strip()
        if not name:
            continue
        templates.append(
            {
                "name": name,
                "start_month": int(raw["start_month"]),
                "start_day": int(raw["start_day"]),
                "end_month": int(raw["end_month"]),
                "end_day": int(raw["end_day"]),
                "end_year_offset": int(raw.get("end_year_offset", 0)),
            }
        )
    return tuple(templates) if templates else DEFAULT_CYCLE_TEMPLATES


def load_egypt_cycles(calendar_path: str | Path, start: Any, end: Any) -> list[dict[str, Any]]:
    """Return expected Egypt agricultural-cycle windows covering the date range."""
    start_dt = _as_utc_datetime(start)
    end_dt = _as_utc_datetime(end)
    templates = _load_templates(Path(calendar_path))

    cycles: list[dict[str, Any]] = []
    for year in range(start_dt.year - 1, end_dt.year + 2):
        for template in templates:
            cycle_start = datetime(
                year,
                int(template["start_month"]),
                int(template["start_day"]),
                tzinfo=timezone.utc,
            )
            end_year = year + int(template.get("end_year_offset", 0))
            cycle_end = datetime(
                end_year,
                int(template["end_month"]),
                int(template["end_day"]),
                23,
                59,
                59,
                tzinfo=timezone.utc,
            )
            if cycle_end < start_dt or cycle_start > end_dt:
                continue
            cycle_name = str(template["name"]).lower().replace(" ", "_")
            cycles.append(
                {
                    "cycle_id": f"egypt_{cycle_name}_{year}",
                    "start_date": cycle_start,
                    "end_date": cycle_end,
                    "expected_window": {
                        "start_date": cycle_start.date().isoformat(),
                        "end_date": cycle_end.date().isoformat(),
                    },
                }
            )

    cycles.sort(key=lambda item: item["start_date"])
    return cycles
