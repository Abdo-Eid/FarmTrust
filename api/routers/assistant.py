"""Bounded report-assistant endpoints (T-04 / T-11 Layer 7)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.assistant import service
from api.database import get_session
from api.models import Land
from api.schemas import AssistantResponse, ChatRequest


router = APIRouter(prefix="/lands", tags=["assistant"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/{land_id}/assistant/narrate", response_model=AssistantResponse)
def narrate_report(land_id: str, session: SessionDep) -> AssistantResponse:
    land = session.get(Land, land_id)
    if land is None:
        raise HTTPException(status_code=404, detail="Land not found")
    result = service.narrate(session, land)
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence packet not yet generated")
    return AssistantResponse(**result)


@router.post("/{land_id}/assistant/chat", response_model=AssistantResponse)
def chat_about_report(land_id: str, payload: ChatRequest, session: SessionDep) -> AssistantResponse:
    land = session.get(Land, land_id)
    if land is None:
        raise HTTPException(status_code=404, detail="Land not found")
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty")
    history = [turn.model_dump() for turn in payload.history] if payload.history else None
    result = service.answer(session, land, question, history)
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence packet not yet generated")
    return AssistantResponse(**result)
