"""Deterministic brief tests (T-04).

The brief is the always-on narration and the LLM fallback. It must be fully
typed, claim-disciplined, deterministic, and faithful to the packet's wording.
"""

from __future__ import annotations

import re

from farmtrust_core.report.brief import build_deterministic_brief
from farmtrust_core.report.evidence_packet import CLAIM_TYPES

FORBIDDEN_CROP_TOKENS = (
    "wheat", "maize", "corn", "berseem", "clover", "rice",
    "fasolia", "cotton", "sorghum", "beans",
)


def _packet() -> dict:
    return {
        "aoi_id": "aoi-x",
        "assessment_status": "complete",
        "interval": {"start_date": "2024-01-01", "end_date": "2026-01-01", "duration_days": 730},
        "headline": {
            "state_label": "Active — multiple cycles observed",
            "overall_confidence": "medium",
            "cropping_intensity": "2 complete cycle(s) observed (provisional)",
            "summary": "Active — multiple cycles observed. 2 vegetation activity cycle(s) detected over the "
            "2.0-year window at medium overall confidence. Evidence is satellite greenness only — not crop "
            "identity, yield, or financial outcome.",
        },
        "claims": [
            {"id": "observation_coverage", "layer": "observed", "claim": "Coverage is good.",
             "confidence": "moderate", "claim_type": "measured_observation"},
            {"id": "activity_cycles_observed", "layer": "observed",
             "claim": "Greenness completed 2 vegetation activity cycle(s).",
             "confidence": "strong", "claim_type": "deterministic_pipeline_result"},
            {"id": "worked_field_interpreted", "layer": "interpreted",
             "claim": "The greenness rhythm is consistent with a worked, actively cropped field.",
             "confidence": "moderate", "claim_type": "interpretation"},
            {"id": "conf_yield", "layer": "confidence", "claim": "Confidence in yield, output, or income.",
             "confidence": "none", "claim_type": "boundary_exclusion"},
            {"id": "watch_short_record", "layer": "watch", "claim": "The satellite track record is short.",
             "confidence": "moderate", "claim_type": "measured_observation"},
        ],
        "track_record": {
            "seasons_observed": 2, "seasons_for_certifiable_trend": 5, "fraction": 0.4,
            "status_so_far": "stable", "provisional": True,
            "note": "2 of ~5 seasons toward a certifiable use-stability claim.",
        },
        "risk_register": [
            {"item": "Short satellite record", "kind": "evidence_limitation", "severity": "low",
             "reason": "Track record is too short for a long-term claim."},
        ],
        "boundaries": [
            "Harvested yield, tonnage, or output volume",
            "Crop identity (not proven from satellite)",
            "Pest, disease, or in-field damage",
        ],
        "indicators": {"values": {"ndvi_peak": 0.88}, "interpretation_notes": {}},
    }


def test_brief_is_fully_typed_and_sourced() -> None:
    lines = build_deterministic_brief(_packet())
    assert lines
    for line in lines:
        assert line["text"]
        assert line["claim_type"] in CLAIM_TYPES
        assert line["source"]
        assert "section" in line


def test_brief_starts_with_verdict_and_ends_with_boundaries() -> None:
    lines = build_deterministic_brief(_packet())
    assert lines[0]["section"] == "verdict"
    assert lines[-1]["section"] == "boundaries"
    assert lines[-1]["claim_type"] == "boundary_exclusion"


def test_brief_reuses_claim_types_and_confidence() -> None:
    lines = build_deterministic_brief(_packet())
    by_source = {line["source"]: line for line in lines}
    assert by_source["observation_coverage"]["claim_type"] == "measured_observation"
    assert by_source["worked_field_interpreted"]["claim_type"] == "interpretation"
    assert by_source["activity_cycles_observed"]["confidence"] == "strong"


def test_brief_has_no_crop_tokens() -> None:
    text = " ".join(line["text"] for line in build_deterministic_brief(_packet())).lower()
    for token in FORBIDDEN_CROP_TOKENS:
        assert re.search(rf"\b{token}\b", text) is None, f"crop token '{token}' leaked into brief"


def test_brief_is_deterministic() -> None:
    first = build_deterministic_brief(_packet())
    second = build_deterministic_brief(_packet())
    assert first == second


def test_brief_covers_every_layer_and_risk() -> None:
    lines = build_deterministic_brief(_packet())
    sections = {line["section"] for line in lines}
    assert {"verdict", "observed", "interpreted", "confidence", "watch", "track_record", "risk", "boundaries"} <= sections
