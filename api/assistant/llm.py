"""Azure ``gpt-4o`` adapter for the assistant (LangChain isolated here).

Everything LangChain-specific lives in this module, so the provider is
swappable and the rest of the codebase never imports it. Imports are lazy: when
the LLM is unconfigured (no API key) nothing here touches LangChain, so the
deterministic path and the tests run with or without the package installed.

Both entry points return ``None`` on missing config or *any* error; the caller
(``service.py``) then falls back to the deterministic brief. The API key is
read via ``config`` and never logged.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from api.assistant import config
from api.assistant.prompt import CHAT_STYLE, NARRATE_INSTRUCTION, build_system_prompt

_ClaimType = Literal[
    "measured_observation",
    "deterministic_pipeline_result",
    "model_derived_analysis",
    "interpretation",
    "boundary_exclusion",
    "user_provided_local_context",
    "unknown",
]


class NarrationLine(BaseModel):
    text: str = Field(description="One grounded narration sentence for a lender.")
    claim_type: _ClaimType = Field(description="The provenance type of this line.")
    source: str = Field(description="The packet field/claim id this line rests on.")
    confidence: Optional[str] = Field(default=None, description="Confidence label if one applies.")


class Narration(BaseModel):
    lines: list[NarrationLine]


def _model():
    # Lazy import: only reached when an API key is configured.
    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_endpoint=config.azure_endpoint(),
        api_key=config.azure_api_key(),
        api_version=config.azure_api_version(),
        azure_deployment=config.azure_deployment(),
        temperature=0,
    )


def narrate(packet: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
    """Structured, claim-typed narration. Returns line dicts or ``None`` on failure."""
    if not config.is_llm_configured():
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = _model().with_structured_output(Narration)
        result = model.invoke(
            [
                SystemMessage(content=build_system_prompt(packet)),
                HumanMessage(content=NARRATE_INSTRUCTION),
            ]
        )
        lines = [line.model_dump() for line in result.lines]
        return lines or None
    except Exception:
        return None


def answer(
    packet: dict[str, Any],
    question: str,
    history: Optional[list[dict[str, str]]] = None,
) -> Optional[str]:
    """Free-form bounded answer. Returns text or ``None`` on failure."""
    if not config.is_llm_configured():
        return None
    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        messages: list[Any] = [
            SystemMessage(content=build_system_prompt(packet)),
            SystemMessage(content=CHAT_STYLE),
        ]
        for turn in history or []:
            role = turn.get("role")
            content = str(turn.get("content", ""))
            if not content:
                continue
            if role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        messages.append(HumanMessage(content=question))

        result = _model().invoke(messages)
        content = result.content
        text = content if isinstance(content, str) else str(content)
        return text.strip() or None
    except Exception:
        return None
