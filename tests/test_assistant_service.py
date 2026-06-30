"""Assistant service orchestration tests (T-04).

No live Azure: the LLM is monkeypatched. These assert the deterministic fallback
is clean, the LLM path is used only when configured AND guardrail-clean, and that
every call writes an ``AssistantMessage`` audit row.
"""

from __future__ import annotations

import json

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from api.assistant import config, llm, service
from api.models import AssistantMessage, Land
from farmtrust_core.io.paths import report_evidence_packet_path

PACKET = {
    "aoi_id": "aoi-svc",
    "assessment_status": "complete",
    "interval": {"start_date": "2024-01-01", "end_date": "2026-01-01", "duration_days": 730},
    "headline": {
        "state_label": "Active — multiple cycles observed",
        "overall_confidence": "medium",
        "cropping_intensity": "2 complete cycle(s) observed (provisional)",
        "summary": "Active — multiple cycles observed. Evidence is satellite greenness only — "
        "not crop identity, yield, or financial outcome.",
    },
    "claims": [
        {"id": "observation_coverage", "layer": "observed", "claim": "Coverage is good.",
         "confidence": "moderate", "claim_type": "measured_observation"},
        {"id": "conf_yield", "layer": "confidence", "claim": "Confidence in yield, output, or income.",
         "confidence": "none", "claim_type": "boundary_exclusion"},
    ],
    "track_record": {"seasons_observed": 2, "seasons_for_certifiable_trend": 5, "fraction": 0.4,
                     "status_so_far": "stable", "provisional": True, "note": "2 of ~5 seasons."},
    "risk_register": [{"item": "Short satellite record", "kind": "evidence_limitation",
                       "severity": "low", "reason": "Track record is too short."}],
    "boundaries": ["Harvested yield, tonnage, or output volume", "Crop identity (not proven from satellite)"],
    "indicators": {"values": {"ndvi_peak": 0.88}, "interpretation_notes": {}},
}

CLEAN_LINES = [
    {"text": "The parcel shows two activity cycles over the window.", "claim_type": "deterministic_pipeline_result",
     "source": "activity_cycles_observed", "confidence": "strong"},
    {"text": "Yield is not observable from greenness.", "claim_type": "boundary_exclusion",
     "source": "conf_yield", "confidence": "none"},
]


def _write_packet(aoi_id: str) -> None:
    path = report_evidence_packet_path(aoi_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(PACKET), encoding="utf-8")


@pytest.fixture
def land_session(tmp_path, monkeypatch):
    monkeypatch.setenv("FARMTRUST_DATA_DIR", str(tmp_path))
    _write_packet("aoi-svc")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    land = Land(id="land-svc", name="Test", governorate="Menofia", geometry="{}",
                area_feddan=1.0, aoi_id="aoi-svc", job_id="job-svc")
    with Session(engine) as session:
        session.add(land)
        session.commit()
        session.refresh(land)
        yield land, session


def _rows(session: Session) -> list[AssistantMessage]:
    return list(session.exec(select(AssistantMessage)).all())


def test_narrate_falls_back_when_unconfigured(land_session, monkeypatch) -> None:
    land, session = land_session
    monkeypatch.setattr(config, "is_llm_configured", lambda: False)
    result = service.narrate(session, land)
    assert result is not None
    assert result["source_mode"] == "deterministic"
    assert result["fallback_used"] is True
    assert result["model"] is None
    assert result["lines"] and all(line["claim_type"] for line in result["lines"])
    rows = _rows(session)
    assert len(rows) == 1 and rows[0].source_mode == "deterministic" and rows[0].kind == "narrate"
    assert rows[0].packet_hash and rows[0].prompt_version


def test_narrate_uses_llm_when_configured_and_clean(land_session, monkeypatch) -> None:
    land, session = land_session
    monkeypatch.setattr(config, "is_llm_configured", lambda: True)
    monkeypatch.setattr(llm, "narrate", lambda packet: [dict(line) for line in CLEAN_LINES])
    result = service.narrate(session, land)
    assert result["source_mode"] == "llm"
    assert result["fallback_used"] is False
    assert result["model"] == config.azure_deployment()
    rows = _rows(session)
    assert len(rows) == 1 and rows[0].source_mode == "llm" and rows[0].model_name == config.azure_deployment()


def test_chat_fallback_returns_brief(land_session, monkeypatch) -> None:
    land, session = land_session
    monkeypatch.setattr(config, "is_llm_configured", lambda: False)
    result = service.answer(session, land, "Is this parcel active?")
    assert result["source_mode"] == "deterministic"
    assert result["fallback_used"] is True
    assert result["lines"][0]["section"] == "chat"
    rows = _rows(session)
    assert len(rows) == 1 and rows[0].kind == "chat" and rows[0].question == "Is this parcel active?"


def test_chat_uses_llm_when_clean(land_session, monkeypatch) -> None:
    land, session = land_session
    monkeypatch.setattr(config, "is_llm_configured", lambda: True)
    monkeypatch.setattr(llm, "answer", lambda packet, question, history=None:
                        "The parcel shows two activity cycles; yield is not observable.")
    result = service.answer(session, land, "What did the satellite see?")
    assert result["source_mode"] == "llm"
    assert len(result["lines"]) == 1
    assert result["lines"][0]["claim_type"] == "interpretation"


def test_missing_packet_returns_none(land_session, monkeypatch) -> None:
    land, session = land_session
    monkeypatch.setattr(config, "is_llm_configured", lambda: False)
    absent = Land(id="land-absent", name="No packet", governorate="Menofia", geometry="{}",
                  area_feddan=1.0, aoi_id="aoi-absent", job_id="job-svc")
    session.add(absent)
    session.commit()
    assert service.narrate(session, absent) is None
    assert service.answer(session, absent, "anything?") is None
    # nothing persisted for the packet-less land
    assert all(row.land_id == "land-svc" for row in _rows(session))
