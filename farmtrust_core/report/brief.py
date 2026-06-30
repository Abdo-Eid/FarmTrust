"""Deterministic report brief (T-04 / T-11 Layer 7).

Narrate the grounded evidence packet into ordered, claim-typed lines with **no
LLM**. This is BOTH the always-on no-LLM narration and the automatic fallback
when the assistant model is unconfigured or errors.

It invents nothing: every line reuses the packet's own wording and the
per-claim ``claim_type`` / ``confidence`` already attached by the packet
builder (``_apply_provenance``). Same packet in -> same brief out.
"""

from __future__ import annotations

from typing import Any, Optional

LAYER_ORDER = ("observed", "interpreted", "confidence", "watch")
LAYER_LEAD = {
    "observed": "What the satellite shows",
    "interpreted": "What the pattern may suggest",
    "confidence": "How sure — and on what basis",
    "watch": "What to watch",
}


def _line(
    text: str,
    claim_type: str,
    source: str,
    *,
    confidence: Optional[str] = None,
    section: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "claim_type": claim_type,
        "source": source,
        "confidence": confidence,
        "section": section,
    }


def build_deterministic_brief(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Project the evidence packet into a flat list of claim-typed brief lines."""
    lines: list[dict[str, Any]] = []

    headline = packet.get("headline", {}) or {}
    overall = headline.get("overall_confidence")
    summary = headline.get("summary")
    if summary:
        lines.append(
            _line(summary, "deterministic_pipeline_result", "headline.summary",
                  confidence=overall, section="verdict")
        )
    intensity = headline.get("cropping_intensity")
    if intensity:
        lines.append(
            _line(intensity, "model_derived_analysis", "headline.cropping_intensity", section="verdict")
        )

    claims = packet.get("claims", []) or []
    for layer in LAYER_ORDER:
        layer_claims = [c for c in claims if c.get("layer") == layer]
        if not layer_claims:
            continue
        for claim in layer_claims:
            lines.append(
                _line(
                    str(claim.get("claim", "")),
                    str(claim.get("claim_type", "unknown")),
                    str(claim.get("id", layer)),
                    confidence=claim.get("confidence"),
                    section=layer,
                )
            )

    track = packet.get("track_record") or {}
    note = track.get("note")
    if note:
        flag = " (provisional)" if track.get("provisional") else ""
        status = track.get("status_so_far")
        prefix = f"Track record so far: {status}{flag}. " if status else ""
        lines.append(
            _line(f"{prefix}{note}", "model_derived_analysis", "track_record",
                  confidence="provisional" if track.get("provisional") else "moderate", section="track_record")
        )

    for item in packet.get("risk_register", []) or []:
        kind = item.get("kind")
        claim_type = "deterministic_pipeline_result" if kind == "land_risk" else "measured_observation"
        label = "Land risk" if kind == "land_risk" else "Evidence limitation"
        lines.append(
            _line(
                f"{label}: {item.get('item', '')} — {item.get('reason', '')}".strip(" —"),
                claim_type,
                f"risk_register:{item.get('code') or item.get('item', '')}",
                section="risk",
            )
        )

    boundaries = packet.get("boundaries", []) or []
    if boundaries:
        lines.append(
            _line(
                "What this does NOT tell you: " + "; ".join(str(b) for b in boundaries) + ".",
                "boundary_exclusion",
                "boundaries",
                section="boundaries",
            )
        )

    return lines
