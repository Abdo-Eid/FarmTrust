"""Assistant orchestration: packet -> (LLM | deterministic brief) -> audit row.

Deterministic-first. The LLM path runs only when configured; grounding is
enforced by the system prompt (no separate output guardrail). When the LLM is
unconfigured or errors, the deterministic brief answers. Every call (narrate or
chat) writes one ``AssistantMessage`` audit row.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional
from uuid import uuid4

from sqlmodel import Session

from api.assistant import config, llm
from api.assistant.prompt import PROMPT_VERSION
from api.models import AssistantMessage, Land, utc_now
from farmtrust_core.io.paths import report_evidence_packet_path
from farmtrust_core.report.brief import build_deterministic_brief


def _load_packet(aoi_id: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Return (packet, sha256-hex) or (None, None) if not generated yet."""
    path = report_evidence_packet_path(aoi_id)
    if not path.exists():
        return None, None
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _persist(
    session: Session,
    land: Land,
    *,
    kind: str,
    question: Optional[str],
    lines: list[dict[str, Any]],
    source_mode: str,
    model_name: Optional[str],
    packet_hash: str,
) -> None:
    row = AssistantMessage(
        id=f"amsg-{uuid4().hex}",
        land_id=land.id,
        aoi_id=land.aoi_id,
        kind=kind,
        question=question,
        response_text=json.dumps(lines),
        source_mode=source_mode,
        model_name=model_name,
        prompt_version=PROMPT_VERSION,
        packet_hash=packet_hash,
        guardrail_result=None,  # vestigial: the forbidden-phrase scan was removed
    )
    session.add(row)
    session.commit()


def narrate(session: Session, land: Land) -> Optional[dict[str, Any]]:
    """On-demand grounded narration. Returns the response dict, or None if no packet."""
    packet, packet_hash = _load_packet(land.aoi_id)
    if packet is None or packet_hash is None:
        return None

    lines: Optional[list[dict[str, Any]]] = None
    source_mode = "deterministic"
    model_name: Optional[str] = None

    if config.is_llm_configured():
        llm_lines = llm.narrate(packet)
        if llm_lines:
            lines = llm_lines
            source_mode = "llm"
            model_name = config.azure_deployment()

    if lines is None:
        lines = build_deterministic_brief(packet)

    fallback_used = source_mode != "llm"
    _persist(
        session, land, kind="narrate", question=None, lines=lines,
        source_mode=source_mode, model_name=model_name, packet_hash=packet_hash,
    )
    return {
        "lines": lines,
        "source_mode": source_mode,
        "fallback_used": fallback_used,
        "model": model_name,
    }


def answer(
    session: Session,
    land: Land,
    question: str,
    history: Optional[list[dict[str, str]]] = None,
) -> Optional[dict[str, Any]]:
    """Bounded analyst chat. Returns the response dict, or None if no packet."""
    packet, packet_hash = _load_packet(land.aoi_id)
    if packet is None or packet_hash is None:
        return None

    lines: Optional[list[dict[str, Any]]] = None
    source_mode = "deterministic"
    model_name: Optional[str] = None

    if config.is_llm_configured():
        llm_text = llm.answer(packet, question, history)
        if llm_text:
            lines = [{
                "text": llm_text,
                "claim_type": "interpretation",
                "source": "assistant",
                "confidence": None,
                "section": "chat",
            }]
            source_mode = "llm"
            model_name = config.azure_deployment()

    if lines is None:
        # No model (or it errored): answer honestly with the grounded brief.
        brief = build_deterministic_brief(packet)
        preface = {
            "text": (
                "The assistant model is not available for free-form analysis right now, "
                "so here is the grounded brief for this report."
            ),
            "claim_type": "deterministic_pipeline_result",
            "source": "assistant",
            "confidence": None,
            "section": "chat",
        }
        lines = [preface, *brief]

    fallback_used = source_mode != "llm"
    _persist(
        session, land, kind="chat", question=question, lines=lines,
        source_mode=source_mode, model_name=model_name, packet_hash=packet_hash,
    )
    return {
        "lines": lines,
        "source_mode": source_mode,
        "fallback_used": fallback_used,
        "model": model_name,
    }
