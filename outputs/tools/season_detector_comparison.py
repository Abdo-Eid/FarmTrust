"""Cross-check the deterministic activity-window detector against the HMM.

Diagnostic only. Reads the daily analysis curve + season_windows.json, runs the
deterministic HMM phenology decoder, and writes a comparison artifact under
``data/comparison/<aoi>/``. This NEVER changes production detection output and is
not consumed by scoring (provenance: isolated_research_cross_check).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.ingest.utils import safe_write_text
from farmtrust_core.seasonal.seasons import load_daily_analysis_curve
from outputs.tools.hmm_comparison import compare_detector_and_hmm
from outputs.tools.hmm_phenology import HmmResult, decode_phenology

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def build_comparison(curve_path: Path, season_windows_path: Path, *, aoi_id: str) -> tuple[dict, str]:
    curve = load_daily_analysis_curve(curve_path)
    result = decode_phenology(curve.dates, curve.ndvi)
    seasons = json.loads(season_windows_path.read_text(encoding="utf-8")).get("seasons", [])
    comparison = compare_detector_and_hmm(seasons, result.cycles)

    payload = {
        "aoi_id": aoi_id,
        "claim_type": "isolated_research_cross_check",
        "provenance_level": 2,
        "method": result.method,
        "restriction": "diagnostic_only; not_consumed_by_scoring; no_crop_identity_claims",
        "daily_curve_source": curve_path.name,
        "hmm_has_high_state": result.has_high_state,
        "comparison": comparison,
        "hmm_cycles": [
            {
                "sos_date": c.sos_date.isoformat(),
                "pos_date": c.pos_date.isoformat(),
                "eos_date": c.eos_date.isoformat(),
                "peak_ndvi": round(c.peak_ndvi, 6),
                "lifecycle_status": c.lifecycle_status,
                "duration_days": c.duration_days,
            }
            for c in result.cycles
        ],
        "detector_seasons": [
            {
                "season_id": s["season_id"],
                "start_date": s["start_date"],
                "peak_date": s["peak_date"],
                "end_date": s["end_date"],
                "lifecycle_status": s.get("lifecycle_status", "complete"),
            }
            for s in seasons
        ],
    }
    return payload, _render_markdown(payload, result)


def _render_markdown(payload: dict, result: HmmResult) -> str:
    cmp = payload["comparison"]
    lines = [
        f"# HMM cross-check vs deterministic detector — {payload['aoi_id']}",
        "",
        "> Research cross-check (`isolated_research_cross_check`, provenance level 2).",
        "> Diagnostic only — not consumed by scoring; does not change production output.",
        "",
        f"- Detector cycles: **{cmp['prod_cycle_count']}**",
        f"- HMM cycles: **{cmp['hmm_cycle_count']}** (delta {cmp['cycle_count_delta']:+d})",
        f"- Matched within ±{cmp['tolerance_days']}d of peak: **{cmp['matched_count']}**",
        f"- Mean |SOS| / |POS| / |EOS| delta (days): "
        f"{cmp['mean_abs_sos_delta_days']} / {cmp['mean_abs_pos_delta_days']} / {cmp['mean_abs_eos_delta_days']}",
        f"- Lifecycle agreement: {cmp['lifecycle_agreement_fraction']}",
        f"- Overall agreement within tolerance: **{cmp['agreement_within_tolerance']}**",
        "",
        "| detector season | SOS Δ | POS Δ | EOS Δ | lifecycle match |",
        "|---|---|---|---|---|",
    ]
    for m in cmp["matches"]:
        lines.append(
            f"| {m['season_id']} | {m['sos_delta_days']:+d} | {m['pos_delta_days']:+d} "
            f"| {m['eos_delta_days']:+d} | {m['lifecycle_match']} |"
        )
    if cmp["unmatched_prod_ids"]:
        lines.append("")
        lines.append(f"Unmatched detector seasons: {', '.join(cmp['unmatched_prod_ids'])}")
    if cmp["unmatched_hmm_indices"]:
        lines.append(f"Unmatched HMM cycles: {cmp['unmatched_hmm_indices']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="HMM cross-check vs deterministic detector.")
    parser.add_argument("--aoi-id", required=True)
    parser.add_argument("--preprocess-dir", default=None, help="default: data/preprocess/<aoi-id>")
    parser.add_argument("--seasonal-dir", default=None, help="default: data/seasonal/<aoi-id>")
    parser.add_argument("--output-dir", default=None, help="default: outputs/diagnostics/<aoi-id>")
    args = parser.parse_args()

    preprocess_dir = Path(args.preprocess_dir) if args.preprocess_dir else Path("data") / "preprocess" / args.aoi_id
    seasonal_dir = Path(args.seasonal_dir) if args.seasonal_dir else Path("data") / "seasonal" / args.aoi_id
    output_dir = Path(args.output_dir) if args.output_dir else Path("outputs") / "diagnostics" / args.aoi_id

    curve_path = preprocess_dir / "season_analysis_curve.csv"
    season_windows_path = seasonal_dir / "season_windows.json"
    if not curve_path.exists():
        raise FileNotFoundError(f"Missing analysis curve: {curve_path}")
    if not season_windows_path.exists():
        raise FileNotFoundError(f"Missing season windows: {season_windows_path}")

    payload, markdown = build_comparison(curve_path, season_windows_path, aoi_id=args.aoi_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_write_text(output_dir / "hmm_cross_check.json", json.dumps(payload, indent=2, sort_keys=True))
    safe_write_text(output_dir / "hmm_cross_check.md", markdown)
    logging.info("Wrote HMM cross-check to: %s", output_dir / "hmm_cross_check.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
