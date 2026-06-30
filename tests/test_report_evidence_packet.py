"""Tests for the report evidence packet (T-11 Layer 5).

Deterministic unit tests drive the real pipeline assessment from minimal
on-disk fixtures, then build the packet from the written artifacts. Invariant
tests run the full chain on the two reference AOIs and skip if data is absent.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from farmtrust_core.report import build_report_evidence_packet, write_report_evidence_packet
from farmtrust_core.report.evidence_packet import BOUNDARIES, LAYERS
from farmtrust_core.scoring import build_land_assessment

REPO_ROOT = Path(__file__).resolve().parents[1]
MENOFIA = REPO_ROOT / "data" / "aoi_demo_01"
SHORT_AOI = REPO_ROOT / "data" / "land-c92521f9627b4cc1a9e0ef65909a1820"

ALLOWED_CONFIDENCE = {"strong", "moderate", "limited", "provisional", "none"}
# Crop-identity terms that must NEVER appear anywhere in a packet (calendar
# descriptors summer/winter/transition are allowed; word-boundary matched so
# "price" does not trip "rice").
FORBIDDEN_CROP_TOKENS = (
    "wheat",
    "maize",
    "corn",
    "berseem",
    "clover",
    "rice",
    "fasolia",
    "cotton",
    "sorghum",
    "beans",
)


def _season(
    season_id: str,
    start: str,
    peak: str,
    end: str,
    *,
    calendar: str,
    lifecycle: str = "complete",
    is_open: bool = False,
    peak_ndvi: float = 0.70,
    gap_stage: str = "none",
    gap_risk: str = "low",
    detection_status: str = "confirmed",
    cycle_split_merged: bool = False,
    quality_label: str = "good",
    confirmation_level: str = "strong",
) -> dict[str, object]:
    return {
        "season_id": season_id,
        "start_date": start,
        "peak_date": peak,
        "end_date": end,
        "season_calendar_label": calendar,
        "lifecycle_status": lifecycle,
        "is_open": is_open,
        "peak_ndvi": peak_ndvi,
        "duration_days": 100,
        "quality_label": quality_label,
        "confirmation_level": confirmation_level,
        "evidence_summary": "Observed strong seasonal vegetation activity.",
        "detection_status": detection_status,
        "gap_overlap_stage": gap_stage,
        "gap_overlap_risk": gap_risk,
        "cycle_split_merged": cycle_split_merged,
    }


class _Harness(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="farmtrust-packet-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _quality_metrics(self, *, aoi_id: str = "aoi-test", **overrides: object) -> dict[str, object]:
        metrics = {
            "aoi_id": aoi_id,
            "usable_observation_count": 80,
            "gap_ratio": 0.05,
            "max_gap_days": 5.0,
            "long_gap_count": 0,
            "long_gap_windows": [],
            "gap_risk": "low",
            "gap_risk_reason": "Observation continuity is strong enough for assessment.",
        }
        metrics.update(overrides)
        return metrics

    def _build_packet(
        self,
        *,
        quality_metrics: dict[str, object],
        seasons: list[dict[str, object]],
        ndvi_value: float = 0.62,
        evi_value: float = 0.48,
        run_metadata_extra: dict[str, object] | None = None,
    ) -> tuple[dict, dict]:
        aoi_id = str(quality_metrics["aoi_id"])
        run_metadata_path = self.tmp / "run_metadata.json"
        smoothed_csv_path = self.tmp / "ndvi_smoothed.csv"
        quality_metrics_path = self.tmp / "quality_metrics.json"
        season_payload_path = self.tmp / "season_windows.json"
        assessment_path = self.tmp / "land_assessment.json"

        run_metadata = {"aoi_id": aoi_id, "start_date": "2024-01-01", "end_date": "2025-02-04"}
        if run_metadata_extra:
            run_metadata.update(run_metadata_extra)
        run_metadata_path.write_text(json.dumps(run_metadata), encoding="utf-8")
        quality_metrics_path.write_text(json.dumps(quality_metrics), encoding="utf-8")

        complete = sum(1 for s in seasons if s.get("lifecycle_status") == "complete")
        season_payload_path.write_text(
            json.dumps(
                {
                    "aoi_id": aoi_id,
                    "season_count": len(seasons),
                    "complete_window_count": complete,
                    "open_window_count": len(seasons) - complete,
                    "borderline_window_count": 0,
                    "gap_risk": quality_metrics["gap_risk"],
                    "seasons": seasons,
                }
            ),
            encoding="utf-8",
        )

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        observation_count = int(quality_metrics.get("usable_observation_count", 80))
        with smoothed_csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "timestamp",
                    "ndvi_smoothed",
                    "ndvi_p95_raw",
                    "ndvi_spread_raw",
                    "evi_smoothed",
                    "ndmi_smoothed",
                    "ndwi_smoothed",
                    "mndwi_smoothed",
                    "is_usable",
                ]
            )
            for index in range(observation_count):
                timestamp = start + timedelta(days=index * 5)
                writer.writerow(
                    [
                        timestamp.isoformat(),
                        ndvi_value,
                        ndvi_value + 0.05,
                        0.05,
                        evi_value,
                        0.20,
                        -0.20,
                        -0.30,
                        "true",
                    ]
                )

        assessment = build_land_assessment(
            run_metadata_path=run_metadata_path,
            smoothed_csv_path=smoothed_csv_path,
            quality_metrics_path=quality_metrics_path,
            season_payload_path=season_payload_path,
        )
        assessment_path.write_text(json.dumps(assessment), encoding="utf-8")

        packet = build_report_evidence_packet(
            assessment_path=assessment_path,
            season_payload_path=season_payload_path,
            quality_metrics_path=quality_metrics_path,
            run_metadata_path=run_metadata_path,
        )
        return packet, assessment

    # -- dict-driven fixtures (full control over claim-logic inputs) ---------

    def _assessment(self, **over: object) -> dict[str, object]:
        base = {
            "aoi_id": "aoi-x",
            "assessment_status": "complete",
            "interval": {"start_date": "2024-01-01", "end_date": "2026-01-01"},
            "land_status": "active",
            "trend_2y": "improving",
            "history_coverage": {
                "status": "sufficient_history",
                "rationale": "Multiple vegetation activity cycles were observed.",
                "observed_activity_cycle_count": 4,
                "complete_activity_cycle_count": 4,
                "assessment_interval_days": 760,
            },
            "absence_assessment": {"status": "activity_present", "rationale": "Activity detected."},
            "season_count": 4,
            "risk_flags": [],
            "satellite_evidence_coverage": {"status": "good", "rationale": "Strong coverage."},
            "confidence": {"level": "medium", "reasons": [], "components": {}},
            "evidence": {"land_status_basis": "Recent vegetation activity observed."},
            "metrics_summary": {
                "usable_observation_count": 120,
                "gap_risk": "low",
                "interval_max_ndvi": 0.88,
                "interval_max_ndvi_p95": 0.95,
                "interval_median_ndvi_spread": 0.05,
                "interval_max_evi": 0.78,
                "interval_median_ndmi": 0.23,
                "interval_median_mndwi": -0.42,
            },
        }
        base.update(over)
        return base

    def _payload(self, *, seasons: list[dict[str, object]], complete: int, open_: int = 0, borderline: int = 0) -> dict[str, object]:
        return {
            "aoi_id": "aoi-x",
            "season_count": len(seasons),
            "complete_window_count": complete,
            "open_window_count": open_,
            "borderline_window_count": borderline,
            "gap_risk": "low",
            "seasons": seasons,
        }

    def _packet_from_dicts(
        self,
        assessment: dict[str, object],
        season_payload: dict[str, object],
        *,
        run_metadata: dict[str, object] | None = None,
        area_feddan: float | None = None,
    ) -> dict:
        a = self.tmp / "land_assessment.json"
        s = self.tmp / "season_windows.json"
        q = self.tmp / "quality_metrics.json"
        r = self.tmp / "run_metadata.json"
        a.write_text(json.dumps(assessment), encoding="utf-8")
        s.write_text(json.dumps(season_payload), encoding="utf-8")
        q.write_text(json.dumps({"aoi_id": assessment.get("aoi_id", "aoi-x")}), encoding="utf-8")
        r.write_text(json.dumps(run_metadata or {}), encoding="utf-8")
        return build_report_evidence_packet(
            assessment_path=a,
            season_payload_path=s,
            quality_metrics_path=q,
            run_metadata_path=r,
            area_feddan=area_feddan,
        )

    # -- shared assertions ---------------------------------------------------

    def _assert_well_formed(self, packet: dict) -> None:
        for key in (
            "packet_version",
            "schema",
            "aoi_id",
            "interval",
            "headline",
            "claims",
            "layers",
            "activity_record",
            "track_record",
            "risk_register",
            "limitations",
            "boundaries",
            "indicators",
            "local_context",
        ):
            self.assertIn(key, packet)
        self.assertEqual(packet["schema"], "farmtrust_report_evidence_packet")
        self.assertEqual(packet["boundaries"], list(BOUNDARIES))
        self.assertTrue(packet["boundaries"])

        for claim in packet["claims"]:
            self.assertIn(claim["layer"], LAYERS)
            self.assertTrue(claim["claim"])
            self.assertIsInstance(claim["claim"], str)
            self.assertIn(claim["confidence"], ALLOWED_CONFIDENCE)
            self.assertIsInstance(claim["rests_on"], str)

        # layers projection mirrors claims exactly
        for layer in LAYERS:
            expected = [c["id"] for c in packet["claims"] if c["layer"] == layer]
            self.assertEqual(packet["layers"].get(layer, []), expected)

        for item in packet["risk_register"]:
            self.assertIn(item["kind"], ("land_risk", "evidence_limitation"))

    def _assert_no_crop_tokens(self, packet: dict) -> None:
        text = json.dumps(packet).lower()
        for token in FORBIDDEN_CROP_TOKENS:
            self.assertIsNone(
                re.search(rf"\b{token}\b", text),
                msg=f"forbidden crop token '{token}' leaked into packet",
            )


class PacketStructureTests(_Harness):
    def test_active_two_cycle_packet(self) -> None:
        seasons = [
            _season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter"),
            _season("season_02", "2024-06-01", "2024-07-15", "2024-09-01", calendar="summer"),
        ]
        packet, assessment = self._build_packet(
            quality_metrics=self._quality_metrics(), seasons=seasons
        )

        self._assert_well_formed(packet)
        self._assert_no_crop_tokens(packet)
        self.assertEqual(assessment["land_status"], "active")
        self.assertTrue(packet["headline"]["state_label"].startswith("Active"))
        self.assertEqual(len(packet["activity_record"]["cycles"]), 2)
        self.assertNotIn("abandonment", json.dumps(packet).lower())
        # observed + interpreted + confidence + watch all represented
        present = {c["layer"] for c in packet["claims"]}
        self.assertEqual(present, set(LAYERS))

    def test_one_cycle_is_active_limited_history(self) -> None:
        seasons = [
            _season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter"),
        ]
        packet, assessment = self._build_packet(
            quality_metrics=self._quality_metrics(), seasons=seasons
        )

        self._assert_well_formed(packet)
        self._assert_no_crop_tokens(packet)
        self.assertEqual(assessment["history_coverage"]["status"], "limited_history")
        self.assertEqual(packet["headline"]["state_label"], "Active — limited history")
        self.assertEqual(packet["track_record"]["status_so_far"], "too_soon_to_tell")
        self.assertEqual(packet["track_record"]["fraction"], 0.2)
        self.assertTrue(any(c["id"] == "watch_short_record" for c in packet["claims"]))
        self.assertNotIn("abandonment", json.dumps(packet).lower())

    def test_fallow_does_not_overclaim(self) -> None:
        packet, assessment = self._build_packet(
            quality_metrics=self._quality_metrics(),
            seasons=[],
            ndvi_value=0.12,
            evi_value=0.10,
        )

        self._assert_well_formed(packet)
        self._assert_no_crop_tokens(packet)
        self.assertEqual(assessment["land_status"], "inactive")
        self.assertEqual(assessment["absence_assessment"]["status"], "absence_supported")
        self.assertEqual(packet["headline"]["state_label"], "Low activity — absence-gated")
        # the only place 'abandonment' may appear is the idle disclaimer
        idle = [c for c in packet["claims"] if c["id"] == "idle_interpreted"]
        self.assertEqual(len(idle), 1)
        self.assertIn("not the same as abandonment", idle[0]["claim"])
        # no risk flag mapped to an abandonment land risk
        self.assertFalse(
            any(item.get("code") == "abandonment" for item in packet["risk_register"])
        )
        self.assertEqual(packet["activity_record"]["cycles"], [])

    def test_manual_review_packet_builds(self) -> None:
        quality_metrics = self._quality_metrics(
            usable_observation_count=8,
            gap_ratio=0.70,
            gap_risk="high",
            gap_risk_reason="Satellite evidence gaps dominate the assessment window.",
        )
        packet, assessment = self._build_packet(quality_metrics=quality_metrics, seasons=[])

        self._assert_well_formed(packet)
        self._assert_no_crop_tokens(packet)
        self.assertEqual(assessment["assessment_status"], "manual_review_required")
        self.assertEqual(
            packet["headline"]["state_label"], "Not assessed — satellite evidence insufficient"
        )
        self.assertTrue(any(c["id"] == "not_assessed_interpreted" for c in packet["claims"]))

    def test_small_parcel_limitation_from_run_metadata_feddan(self) -> None:
        seasons = [
            _season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter"),
        ]
        packet, _ = self._build_packet(
            quality_metrics=self._quality_metrics(),
            seasons=seasons,
            run_metadata_extra={"area_feddan": 0.5},
        )
        small = [item for item in packet["risk_register"] if item["item"].startswith("Small parcel")]
        self.assertEqual(len(small), 1)
        self.assertIn("feddan", small[0]["reason"])
        self.assertNotIn("hectare", json.dumps(packet).lower())  # project unit is feddan, not ha

    def test_determinism(self) -> None:
        seasons = [
            _season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter"),
            _season("season_02", "2024-06-01", "2024-07-15", "2024-09-01", calendar="summer"),
        ]
        first, _ = self._build_packet(quality_metrics=self._quality_metrics(), seasons=seasons)
        second, _ = self._build_packet(quality_metrics=self._quality_metrics(), seasons=seasons)
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
        )

    def test_write_round_trips(self) -> None:
        seasons = [
            _season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter"),
        ]
        packet, _ = self._build_packet(quality_metrics=self._quality_metrics(), seasons=seasons)
        out_dir = self.tmp / "assessment"
        path = write_report_evidence_packet(out_dir, packet)
        self.assertTrue(path.exists())
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(reloaded, packet)


class ClaimLogicTests(_Harness):
    def test_intensity_fires_only_for_genuine_multicrop(self) -> None:
        seasons = [
            _season(f"season_0{i}", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter")
            for i in range(1, 5)
        ]
        packet = self._packet_from_dicts(self._assessment(), self._payload(seasons=seasons, complete=4))
        intensity = [c for c in packet["claims"] if c["id"] == "intensity_interpreted"]
        self.assertEqual(len(intensity), 1)  # 4 cycles / ~2.08 yr = ~1.9/yr
        self.assertIn("per year", intensity[0]["claim"])
        self.assertNotIn("intensively managed", json.dumps(packet))
        self._assert_no_crop_tokens(packet)

    def test_intensity_absent_for_single_crop_over_two_years(self) -> None:
        # 2 complete cycles over ~2 years = ~1/yr -> single-cropping, NOT intensive.
        seasons = [
            _season("season_01", "2024-02-01", "2024-03-01", "2024-04-20", calendar="winter"),
            _season("season_02", "2025-02-01", "2025-03-01", "2025-04-20", calendar="winter"),
        ]
        packet = self._packet_from_dicts(
            self._assessment(
                history_coverage={
                    "status": "sufficient_history",
                    "rationale": "Two cycles observed.",
                    "observed_activity_cycle_count": 2,
                    "complete_activity_cycle_count": 2,
                    "assessment_interval_days": 760,
                }
            ),
            self._payload(seasons=seasons, complete=2),
        )
        self.assertFalse(any(c["id"] == "intensity_interpreted" for c in packet["claims"]))
        self.assertNotIn("per year", json.dumps(packet))
        self.assertNotIn("intensively managed", json.dumps(packet))

    def test_track_record_provisional_flag_set_below_threshold(self) -> None:
        packet = self._packet_from_dicts(
            self._assessment(trend_2y="stable"),
            self._payload(seasons=[_season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter")], complete=4),
        )
        # 4 complete cycles observed, but < 5 toward a certifiable trend -> provisional.
        self.assertEqual(packet["track_record"]["status_so_far"], "stable")
        self.assertTrue(packet["track_record"]["provisional"])

    def test_intermittent_state_label_and_claim(self) -> None:
        packet = self._packet_from_dicts(
            self._assessment(
                land_status="intermittent",
                history_coverage={
                    "status": "limited_history",
                    "rationale": "Activity is intermittent.",
                    "observed_activity_cycle_count": 2,
                    "complete_activity_cycle_count": 1,
                    "assessment_interval_days": 500,
                },
            ),
            self._payload(
                seasons=[_season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter")],
                complete=1,
            ),
        )
        self.assertEqual(packet["headline"]["state_label"], "Intermittent activity")
        self.assertTrue(any(c["id"] == "intermittent_interpreted" for c in packet["claims"]))

    def test_open_cycle_and_key_stage_gap_surface_as_watch(self) -> None:
        seasons = [
            _season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter"),
            _season(
                "season_02", "2024-06-01", "2024-07-15", "2024-09-01", calendar="summer",
                is_open=True, lifecycle="open_right", gap_stage="onset", gap_risk="high",
            ),
        ]
        packet = self._packet_from_dicts(self._assessment(), self._payload(seasons=seasons, complete=1, open_=1))
        ids = {c["id"] for c in packet["claims"]}
        self.assertIn("watch_open_cycle", ids)
        self.assertIn("watch_key_stage_gaps", ids)
        self.assertTrue(
            any(i["item"] == "Gaps at key cycle stages" and i["kind"] == "evidence_limitation"
                for i in packet["risk_register"])
        )
        self.assertTrue(any("incomplete at the window edge" in line for line in packet["limitations"]))

    def test_risk_flag_maps_to_watch_and_land_risk(self) -> None:
        packet = self._packet_from_dicts(
            self._assessment(
                risk_flags=[{"code": "weak_activity_risk", "severity": "moderate", "reason": "Latest cycle is weak."}]
            ),
            self._payload(seasons=[_season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter")], complete=1),
        )
        self.assertTrue(any(c["id"] == "watch_weak_activity_risk" for c in packet["claims"]))
        self.assertTrue(
            any(i["code"] == "weak_activity_risk" and i["kind"] == "land_risk" for i in packet["risk_register"])
        )

    def test_small_parcel_from_area_feddan_param(self) -> None:
        seasons = [_season("season_01", "2024-01-10", "2024-03-01", "2024-04-20", calendar="winter")]
        small = self._packet_from_dicts(
            self._assessment(), self._payload(seasons=seasons, complete=1), area_feddan=0.5
        )
        self.assertTrue(
            any(i["item"].startswith("Small parcel") and "feddan" in i["reason"] for i in small["risk_register"])
        )
        big = self._packet_from_dicts(
            self._assessment(), self._payload(seasons=seasons, complete=1), area_feddan=2.0
        )
        self.assertFalse(any(i["item"].startswith("Small parcel") for i in big["risk_register"]))


# --------------------------------------------------------------------------
# Invariant tests on the real reference AOIs
# --------------------------------------------------------------------------


def _build_real_aoi_packet(source: Path, tmp: Path) -> tuple[dict, dict, dict]:
    from farmtrust_core.preprocess import build_preprocess_artifacts, write_preprocess_outputs
    from farmtrust_core.seasonal import build_season_payload, write_season_payload

    artifacts = build_preprocess_artifacts(
        csv_path=source / "indices_timeseries.csv",
        metadata_path=source / "run_metadata.json",
    )
    paths = write_preprocess_outputs(
        output_dir=tmp,
        processed_observations=artifacts["processed_observations"],
        quality_metrics=artifacts["quality_metrics"],
        analysis_curve=artifacts["analysis_curve"],
    )
    payload = build_season_payload(
        smoothed_csv_path=paths["csv_path"],
        quality_metrics_path=paths["metrics_path"],
        daily_curve_path=paths["analysis_curve_path"],
    )
    season_windows_path = write_season_payload(output_dir=tmp, payload=payload)
    assessment = build_land_assessment(
        run_metadata_path=source / "run_metadata.json",
        smoothed_csv_path=paths["csv_path"],
        quality_metrics_path=paths["metrics_path"],
        season_payload_path=season_windows_path,
    )
    assessment_path = tmp / "land_assessment.json"
    assessment_path.write_text(json.dumps(assessment), encoding="utf-8")
    packet = build_report_evidence_packet(
        assessment_path=assessment_path,
        season_payload_path=season_windows_path,
        quality_metrics_path=paths["metrics_path"],
        run_metadata_path=source / "run_metadata.json",
    )
    return packet, assessment, payload


class _RealAoiPacketMixin:
    source: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="farmtrust-packet-real-"))
        cls.packet, cls.assessment, cls.payload = _build_real_aoi_packet(cls.source, cls.tmp)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_cycle_count_matches_activity_record(self) -> None:
        self.assertEqual(
            len(self.packet["activity_record"]["cycles"]), self.payload["season_count"]
        )

    def test_claims_well_formed(self) -> None:
        for claim in self.packet["claims"]:
            self.assertIn(claim["layer"], LAYERS)
            self.assertIn(claim["confidence"], ALLOWED_CONFIDENCE)
            self.assertTrue(claim["claim"])
        for layer in LAYERS:
            expected = [c["id"] for c in self.packet["claims"] if c["layer"] == layer]
            self.assertEqual(self.packet["layers"].get(layer, []), expected)

    def test_no_crop_tokens(self) -> None:
        text = json.dumps(self.packet).lower()
        for token in FORBIDDEN_CROP_TOKENS:
            self.assertIsNone(re.search(rf"\b{token}\b", text))


@unittest.skipUnless(MENOFIA.exists(), "aoi_demo_01 source data not present")
class MenofiaPacketTests(_RealAoiPacketMixin, unittest.TestCase):
    source = MENOFIA

    def test_active_no_false_abandonment(self) -> None:
        self.assertEqual(self.assessment["land_status"], "active")
        self.assertTrue(self.packet["headline"]["state_label"].startswith("Active"))
        self.assertNotIn("abandonment", json.dumps(self.packet).lower())


@unittest.skipUnless(SHORT_AOI.exists(), "short land AOI source data not present")
class ShortAoiPacketTests(_RealAoiPacketMixin, unittest.TestCase):
    source = SHORT_AOI

    def test_limited_history_no_false_abandonment(self) -> None:
        self.assertIn(self.assessment["land_status"], ("active", "intermittent"))
        self.assertNotIn("abandonment", json.dumps(self.packet).lower())


if __name__ == "__main__":
    unittest.main()
