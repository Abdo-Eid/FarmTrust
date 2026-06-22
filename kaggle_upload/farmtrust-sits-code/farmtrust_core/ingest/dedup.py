"""Pre-download deduplication: one best scene per (date, spacecraft)."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Tuple


def normalize_spacecraft(platform: str) -> str:
    """Normalize STAC platform string to short spacecraft ID."""
    mapping = {"Sentinel-2A": "S2A", "Sentinel-2B": "S2B", "Sentinel-2C": "S2C"}
    return mapping.get(platform, platform)


def pre_deduplicate_items(items: List[Any], logger: logging.Logger) -> List[Any]:
    """
    Keep one best scene per (calendar_date, spacecraft).

    Selection rule:
      1. Lowest eo:cloud_cover (missing/-1 treated as 100.0)
      2. Tiebreaker: lexicographically lowest item_id (deterministic)

    Preserves the original datetime sort order of survivors.
    """
    from collections import defaultdict

    groups: Dict[Tuple[str, str], List[Any]] = defaultdict(list)
    for item in items:
        date_str = item.datetime.date().isoformat() if item.datetime else "unknown"
        spacecraft = normalize_spacecraft(item.properties.get("platform", "unknown"))
        groups[(date_str, spacecraft)].append(item)

    kept_ids: set = set()
    for (date_str, spacecraft), group in groups.items():
        def sort_key(it: Any) -> Tuple[float, str]:
            cc = it.properties.get("eo:cloud_cover", None)
            if cc is None or cc < 0:
                cc = 100.0
            return (float(cc), it.id)

        group.sort(key=sort_key)
        winner = group[0]
        kept_ids.add(winner.id)
        dropped = [it.id for it in group[1:]]
        if dropped:
            logger.info(
                f"Pre-dedup: {date_str} {spacecraft} kept={winner.id} "
                f"dropped={dropped} (cloud_cover={sort_key(winner)[0]})"
            )

    survivors = [it for it in items if it.id in kept_ids]
    return survivors
