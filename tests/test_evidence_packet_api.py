"""API-layer tests for the evidence packet: the mapper + DTO + path wiring.

There is no FastAPI TestClient harness in this repo, so we exercise the new
``map_evidence_packet_response`` mapper directly (the endpoint is a thin land
lookup + 404 wrapper around it).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.assessment_mapper import map_evidence_packet_response
from api.models import Land
from api.schemas import EvidencePacketResponse
from farmtrust_core.io.paths import assessment_dir, report_evidence_packet_path
from farmtrust_core.report import write_report_evidence_packet


def _sample_packet(aoi_id: str) -> dict:
    return {
        "packet_version": "1.0",
        "schema": "farmtrust_report_evidence_packet",
        "aoi_id": aoi_id,
        "assessment_status": "complete",
        "source_artifacts": ["land_assessment.json", "season_windows.json"],
        "interval": {"start_date": "2024-01-01", "end_date": "2026-01-01", "duration_days": 730},
        "headline": {
            "state_label": "Active — multiple cycles observed",
            "cropping_intensity": "4 complete cycle(s) over 2.0 yr (~2.0/yr, provisional)",
            "overall_confidence": "medium",
            "summary": "Active — multiple cycles observed.",
        },
        "claims": [
            {"id": "c1", "layer": "observed", "claim": "x", "confidence": "strong", "rests_on": "y"},
            {"id": "c2", "layer": "watch", "claim": "z", "confidence": "none", "rests_on": "w"},
        ],
        "layers": {"observed": ["c1"], "interpreted": [], "confidence": [], "watch": ["c2"]},
        "activity_record": {
            "cycles": [
                {
                    "season_id": "season_01",
                    "start_date": "2024-01-10",
                    "peak_date": "2024-03-01",
                    "end_date": "2024-04-20",
                    "season_calendar_label": "winter",
                    "lifecycle_status": "complete",
                    "is_open": False,
                    "peak_ndvi": 0.7,
                    "duration_days": 100.0,
                    "detection_status": "confirmed",
                    "cycle_split_merged": False,
                }
            ],
            "complete_window_count": 1,
            "open_window_count": 0,
            "borderline_window_count": 0,
        },
        "track_record": {
            "seasons_observed": 4,
            "seasons_for_certifiable_trend": 5,
            "fraction": 0.8,
            "status_so_far": "improving",
            "provisional": True,
            "note": "n",
        },
        "risk_register": [
            {"item": "Weak activity risk", "kind": "land_risk", "severity": "moderate", "reason": "z", "code": "weak"}
        ],
        "limitations": ["l"],
        "boundaries": ["Harvested yield, tonnage, or output volume"],
        "indicators": {"values": {"ndvi_peak": 0.8}, "interpretation_notes": {"ndvi_peak": "note"}},
        "local_context": [],
    }


def _land(aoi_id: str) -> Land:
    return Land(
        id=f"land-{aoi_id}",
        name="Plot",
        governorate="Sharqia",
        geometry="{}",
        area_feddan=2.0,
        aoi_id=aoi_id,
        job_id=f"job-{aoi_id}",
    )


class EvidencePacketApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="farmtrust-packet-api-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_returns_none_when_packet_absent(self) -> None:
        with patch.dict(os.environ, {"FARMTRUST_DATA_DIR": str(self.root)}):
            self.assertIsNone(map_evidence_packet_response(_land("missing")))

    def test_maps_written_packet_to_dto(self) -> None:
        aoi_id = "aoi-packet-api"
        with patch.dict(os.environ, {"FARMTRUST_DATA_DIR": str(self.root)}):
            write_report_evidence_packet(assessment_dir(aoi_id), _sample_packet(aoi_id))
            self.assertTrue(report_evidence_packet_path(aoi_id).exists())
            dto = map_evidence_packet_response(_land(aoi_id))

        self.assertIsInstance(dto, EvidencePacketResponse)
        assert dto is not None
        self.assertEqual(dto.aoi_id, aoi_id)
        self.assertEqual(dto.packet_schema, "farmtrust_report_evidence_packet")
        self.assertEqual(dto.headline.overall_confidence, "medium")
        self.assertEqual(len(dto.claims), 2)
        self.assertTrue(dto.track_record.provisional)
        self.assertEqual(dto.activity_record.cycles[0].season_calendar_label, "winter")
        self.assertEqual(dto.risk_register[0].kind, "land_risk")
        # The wire form re-exposes the reserved "schema" key via the alias.
        dumped = dto.model_dump(by_alias=True)
        self.assertEqual(dumped["schema"], "farmtrust_report_evidence_packet")
        self.assertNotIn("packet_schema", dumped)


if __name__ == "__main__":
    unittest.main()
