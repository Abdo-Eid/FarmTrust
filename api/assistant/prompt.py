"""Grounded system prompt for the expert satellite-agronomy assistant.

The prompt is built from the evidence packet plus a curated field-knowledge file
(``api/assistant/knowledge.md``) that is loaded at runtime — edit that file to
teach the assistant, no code change needed. The hard rules keep it bounded:
anchor parcel facts in the packet, reason with the user's declared context, and
never estimate yield/income or make a financing decision.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROMPT_VERSION = "assistant-prompt-v2-2026-07-01"

# Curated field knowledge, loaded fresh from this file each call so edits apply
# without a code change (a backend restart is not even required for .md edits).
KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge.md"
_KNOWLEDGE_FALLBACK = (
    "Operating region: Egyptian Nile Delta / valley (e.g. Menofia). "
    "Winter (~Nov–May): wheat, berseem/clover, sometimes beans/fasolia before wheat. "
    "Summer (~May–Oct): maize, rice, cotton. 2–3 cycles/year is a normal intensive rotation. "
    "Greenness is not yield; do not infer crop identity, yield, or pests from the signal alone; "
    "'summer'/'winter' are calendar descriptors, not crop names."
)


def load_knowledge() -> str:
    """Return the curated field knowledge (or a compact fallback if the file is missing)."""
    try:
        text = KNOWLEDGE_PATH.read_text(encoding="utf-8").strip()
        return text or _KNOWLEDGE_FALLBACK
    except OSError:
        return _KNOWLEDGE_FALLBACK


CLAIM_TYPE_RULES = (
    "Each narration line carries a structured claim_type field. Choose one of: "
    "measured_observation (a number read off the data), "
    "deterministic_pipeline_result (a rule/detector output), "
    "model_derived_analysis (derived from the smoothed model curve), "
    "interpretation (an inferred pattern — keep it confidence-gated and hedged), "
    "boundary_exclusion (a statement of what is NOT observable), "
    "user_provided_local_context (the curated field knowledge or what the user tells you — context, not measured truth), "
    "unknown (the packet does not say). "
    "These claim types, the source, and any confidence go ONLY in their structured fields — "
    "NEVER write a claim type, a source, a field name, or a bracketed [...] tag inside the text."
)

HARD_RULES = [
    "Anchor every parcel-specific fact (cycles, dates, coverage, confidence) in the evidence packet below. You MAY use general agronomy knowledge to interpret and reason — just keep measured facts and interpretation distinct.",
    "Satellite greenness cannot PROVE a crop, so never assert a specific crop identity from the satellite signal alone.",
    "When the user tells you what was grown, treat it as ground truth (their input). Map it onto the observed cycles, check whether the timing and shape are consistent, and reason it through with them — this is exactly your job.",
    "Separate, in plain words, what is measured, what you are inferring, and what the user told you (e.g. 'the data shows…', 'this would suggest…', 'you mentioned…'). Never present a hypothesis as a measured fact.",
    "If the packet is silent and the user gives no input, say what is unknown rather than inventing it.",
    "Never estimate yield, output, tonnage, harvest, income, revenue, profit, or price — they are not observable here.",
    "Never approve, reject, recommend, or score a loan, credit, or financing decision. This is decision SUPPORT, not a decision.",
    "Never diagnose pests or disease, and never claim their absence, from greenness.",
    "Never assert ownership, title, legal status, or water rights.",
    "Preserve uncertainty: surface confidence and the 'Watch' caveats.",
    "Write every answer as clean, natural prose. Never put claim-type names, sources, field names, or bracketed [...] tags inside the text.",
    "Reply in the same language the user uses — if they write in Arabic, answer in Arabic; if in English, answer in English.",
]


def _format_claims(claims: list[dict[str, Any]]) -> str:
    by_layer: dict[str, list[str]] = {"observed": [], "interpreted": [], "confidence": [], "watch": []}
    for claim in claims:
        layer = str(claim.get("layer", "observed"))
        tag = f"[{claim.get('claim_type', 'unknown')} | confidence={claim.get('confidence', 'n/a')}]"
        line = f"- {claim.get('claim', '')} {tag}"
        rests_on = claim.get("rests_on")
        if rests_on:
            line += f" (rests on: {rests_on})"
        by_layer.setdefault(layer, []).append(line)
    blocks = []
    for layer in ("observed", "interpreted", "confidence", "watch"):
        items = by_layer.get(layer, [])
        if items:
            blocks.append(f"{layer.upper()}:\n" + "\n".join(items))
    return "\n\n".join(blocks)


def _format_activity_record(packet: dict[str, Any]) -> str:
    record = packet.get("activity_record", {}) or {}
    cycles = record.get("cycles", []) or []
    if not cycles:
        return "No individual activity cycles were recorded."
    lines = []
    for index, cycle in enumerate(cycles, 1):
        label = cycle.get("season_calendar_label") or "unknown"
        status = "open/incomplete at the window edge" if cycle.get("is_open") else "complete"
        bits = [f"Cycle {index}: {label} season"]
        if cycle.get("start_date") or cycle.get("end_date"):
            bits.append(f"{cycle.get('start_date') or '?'} to {cycle.get('end_date') or '?'}")
        if cycle.get("peak_date"):
            bits.append(f"peak {cycle.get('peak_date')}")
        if cycle.get("peak_ndvi") is not None:
            bits.append(f"peak NDVI {cycle.get('peak_ndvi')}")
        bits.append(status)
        lines.append("- " + ", ".join(bits))
    counts = (
        f"({record.get('complete_window_count', 0)} complete, "
        f"{record.get('open_window_count', 0)} open, "
        f"{record.get('borderline_window_count', 0)} borderline)"
    )
    return "\n".join(lines) + "\n" + counts


def _format_risk(risk_register: list[dict[str, Any]]) -> str:
    if not risk_register:
        return "No land risks or evidence limitations recorded."
    lines = []
    for item in risk_register:
        lines.append(
            f"- [{item.get('kind', 'risk')} | {item.get('severity', 'moderate')}] "
            f"{item.get('item', '')}: {item.get('reason', '')}"
        )
    return "\n".join(lines)


def _format_indicators(indicators: dict[str, Any]) -> str:
    values = (indicators or {}).get("values", {}) or {}
    parts = [f"{key}={value}" for key, value in values.items() if value is not None]
    return ", ".join(parts) if parts else "No indicator values available."


def build_system_prompt(packet: dict[str, Any]) -> str:
    headline = packet.get("headline", {}) or {}
    interval = packet.get("interval", {}) or {}
    track = packet.get("track_record", {}) or {}

    sections = [
        "You are FarmTrust's expert satellite-agronomy analyst, supporting a LENDER.",
        "You explain and reason over an already-computed satellite land-assessment report; you never change the assessment or its scores.",
        "Anchor parcel-specific facts in the evidence packet below, and use your agronomy knowledge to interpret, connect, and think with the user — decision SUPPORT, never a yield estimate or a financing decision.",
        "",
        "HARD RULES:",
        "\n".join(f"- {rule}" for rule in HARD_RULES),
        "",
        CLAIM_TYPE_RULES,
        "",
        "=== EVIDENCE PACKET ===",
        f"State: {headline.get('state_label', 'unknown')}",
        f"Overall confidence: {headline.get('overall_confidence', 'unknown')}",
        f"Cropping intensity: {headline.get('cropping_intensity') or 'not established'}",
        f"Summary: {headline.get('summary', '')}",
        f"Observation window: {interval.get('start_date')} to {interval.get('end_date')} "
        f"({interval.get('duration_days')} days)",
        f"Track record: {track.get('seasons_observed')} of "
        f"~{track.get('seasons_for_certifiable_trend')} seasons toward a certifiable trend; "
        f"status_so_far={track.get('status_so_far')} (provisional={track.get('provisional')}).",
        "",
        "ACTIVITY RECORD (the cycle-by-cycle timeline — use this to map any crops the user names onto specific cycles):",
        _format_activity_record(packet),
        "",
        "CLAIMS (Observed / Interpreted / Confidence / Watch):",
        _format_claims(packet.get("claims", []) or []),
        "",
        "RISK REGISTER:",
        _format_risk(packet.get("risk_register", []) or []),
        "",
        "INDICATORS (signals, not outcomes): " + _format_indicators(packet.get("indicators", {}) or {}),
        "",
        "WHAT THIS DOES NOT TELL YOU (hard boundaries): "
        + "; ".join(str(b) for b in (packet.get("boundaries", []) or [])),
        "",
        "FARMTRUST FIELD KNOWLEDGE (curated local agronomy + interpretation lessons — "
        "background to reason with and to sense-check the user, NOT parcel evidence):",
        load_knowledge(),
    ]
    return "\n".join(sections)


def packet_digest(packet: dict[str, Any]) -> str:
    """Stable compact digest of the packet, handy for debugging/logging (no secrets)."""
    return json.dumps(
        {
            "aoi_id": packet.get("aoi_id"),
            "state": (packet.get("headline") or {}).get("state_label"),
            "claims": len(packet.get("claims", []) or []),
        },
        sort_keys=True,
    )


CHAT_STYLE = (
    "Format your answer as clean prose. Light Markdown is welcome — short paragraphs, **bold** for "
    "key terms, and simple bullet lists where they help. Do not use headings or tables. Never write "
    "bracketed [...] tags, claim-type names, or field names in the text. "
    "When you answer in a non-English language (e.g. Arabic), write the ENTIRE answer in that language "
    "— do not mix in English words; you may keep short index acronyms (NDVI, EVI, NDMI, MNDWI) in Latin."
)

NARRATE_INSTRUCTION = (
    "Narrate this report for a lender as a short sequence of lines. Walk through, in order: "
    "the overall verdict and confidence; what the satellite observed; what the pattern may suggest "
    "(hedged); how confident and on what basis; what to watch; and finally the hard boundaries. "
    "For each line, set its claim_type, source, and confidence in the structured fields — do NOT "
    "write them in the text. Write each line's text as one clean, plain sentence: no Markdown and no "
    "bracketed tags. Be concise and do not restate the boundary list verbatim — summarise it as scope "
    "limits. Do not invent anything not in the packet."
)
