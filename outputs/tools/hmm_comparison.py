"""Compare the deterministic detector windows against the HMM cross-check.

This produces a *diagnostic* only. It is not consumed by scoring or the API.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from .hmm_phenology import HmmCycle

DEFAULT_POS_MATCH_TOLERANCE_DAYS = 30


def _to_date(value: str) -> date:
    return date.fromisoformat(value)


def compare_detector_and_hmm(
    detector_seasons: Sequence[dict[str, Any]],
    hmm_cycles: Sequence[HmmCycle],
    *,
    tolerance_days: int = DEFAULT_POS_MATCH_TOLERANCE_DAYS,
) -> dict[str, Any]:
    """Greedy 1:1 match of detector windows and HMM cycles by peak date."""
    prod = [
        {
            "season_id": str(season["season_id"]),
            "sos": _to_date(str(season["start_date"])),
            "pos": _to_date(str(season["peak_date"])),
            "eos": _to_date(str(season["end_date"])),
            "lifecycle": str(season.get("lifecycle_status", "complete")),
        }
        for season in detector_seasons
    ]
    hmm = [
        {"sos": c.sos_date, "pos": c.pos_date, "eos": c.eos_date, "lifecycle": c.lifecycle_status}
        for c in hmm_cycles
    ]

    used: set[int] = set()
    matches: list[dict[str, Any]] = []
    for p in prod:
        best_j: int | None = None
        best_delta: int | None = None
        for j, h in enumerate(hmm):
            if j in used:
                continue
            delta = abs((p["pos"] - h["pos"]).days)
            if best_delta is None or delta < best_delta:
                best_delta, best_j = delta, j
        if best_j is not None and best_delta is not None and best_delta <= tolerance_days:
            used.add(best_j)
            h = hmm[best_j]
            matches.append(
                {
                    "season_id": p["season_id"],
                    "sos_delta_days": (h["sos"] - p["sos"]).days,
                    "pos_delta_days": (h["pos"] - p["pos"]).days,
                    "eos_delta_days": (h["eos"] - p["eos"]).days,
                    "lifecycle_match": p["lifecycle"] == h["lifecycle"],
                }
            )

    matched_ids = {m["season_id"] for m in matches}
    unmatched_prod = [p["season_id"] for p in prod if p["season_id"] not in matched_ids]
    unmatched_hmm = [j for j in range(len(hmm)) if j not in used]

    abs_pos = [abs(m["pos_delta_days"]) for m in matches]
    abs_sos = [abs(m["sos_delta_days"]) for m in matches]
    abs_eos = [abs(m["eos_delta_days"]) for m in matches]

    def _mean(values: list[int]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None

    return {
        "prod_cycle_count": len(prod),
        "hmm_cycle_count": len(hmm),
        "cycle_count_delta": len(hmm) - len(prod),
        "matched_count": len(matches),
        "matches": matches,
        "unmatched_prod_ids": unmatched_prod,
        "unmatched_hmm_indices": unmatched_hmm,
        "mean_abs_sos_delta_days": _mean(abs_sos),
        "mean_abs_pos_delta_days": _mean(abs_pos),
        "mean_abs_eos_delta_days": _mean(abs_eos),
        "max_abs_pos_delta_days": max(abs_pos) if abs_pos else None,
        "lifecycle_agreement_fraction": (
            round(sum(1 for m in matches if m["lifecycle_match"]) / len(matches), 3)
            if matches
            else None
        ),
        "agreement_within_tolerance": (
            len(prod) > 0 and len(matches) == len(prod) == len(hmm)
        ),
        "tolerance_days": tolerance_days,
    }
