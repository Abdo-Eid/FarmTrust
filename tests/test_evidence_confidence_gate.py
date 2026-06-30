from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from api.assessment_mapper import map_land_response
from api.models import Job, Land
from farmtrust_core.io.paths import assessment_dir
from farmtrust_core.scoring import build_land_assessment, write_land_assessment


class EvidenceConfidenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="farmtrust-evidence-gate-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _base_quality_metrics(self, *, aoi_id: str = "aoi-test") -> dict[str, object]:
        return {
            "aoi_id": aoi_id,
            "usable_observation_count": 80,
            "gap_ratio": 0.05,
            "max_gap_days": 5.0,
            "long_gap_count": 0,
            "long_gap_windows": [],
            "gap_risk": "low",
            "gap_risk_reason": "Observation continuity is strong enough for assessment.",
        }

    def _write_fixture_files(
        self,
        *,
        quality_metrics: dict[str, object],
        seasons: list[dict[str, object]] | None = None,
        ndvi_value: float = 0.62,
        evi_value: float = 0.48,
    ) -> dict[str, Path]:
        fixture_dir = self.tmpdir / str(quality_metrics["aoi_id"])
        fixture_dir.mkdir(parents=True)

        run_metadata_path = fixture_dir / "run_metadata.json"
        smoothed_csv_path = fixture_dir / "ndvi_smoothed.csv"
        quality_metrics_path = fixture_dir / "quality_metrics.json"
        season_payload_path = fixture_dir / "season_windows.json"

        run_metadata_path.write_text(
            json.dumps(
                {
                    "aoi_id": quality_metrics["aoi_id"],
                    "start_date": "2024-01-01",
                    "end_date": "2025-01-30",
                }
            ),
            encoding="utf-8",
        )
        quality_metrics_path.write_text(json.dumps(quality_metrics), encoding="utf-8")
        if seasons is None:
            seasons = [
                {
                    "season_id": "S1",
                    "start_date": "2024-01-01",
                    "end_date": "2024-04-15",
                    "peak_date": "2024-03-01",
                    "quality_label": "good",
                    "confirmation_level": "strong",
                    "is_open": False,
                    "duration_days": 106,
                    "peak_ndvi": 0.70,
                    "evidence_summary": "Observed strong seasonal vegetation activity.",
                },
                {
                    "season_id": "S2",
                    "start_date": "2024-05-01",
                    "end_date": "2024-08-15",
                    "peak_date": "2024-07-01",
                    "quality_label": "good",
                    "confirmation_level": "strong",
                    "is_open": False,
                    "duration_days": 107,
                    "peak_ndvi": 0.71,
                    "evidence_summary": "Observed strong seasonal vegetation activity.",
                },
            ]

        season_payload_path.write_text(
            json.dumps(
                {
                    "aoi_id": quality_metrics["aoi_id"],
                    "season_count": len(seasons),
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

        return {
            "run_metadata_path": run_metadata_path,
            "smoothed_csv_path": smoothed_csv_path,
            "quality_metrics_path": quality_metrics_path,
            "season_payload_path": season_payload_path,
        }

    def _build_assessment(self, quality_metrics: dict[str, object]) -> dict[str, object]:
        paths = self._write_fixture_files(quality_metrics=quality_metrics)
        return build_land_assessment(**paths)

    def _land_and_job(self, *, aoi_id: str) -> tuple[Land, Job]:
        land = Land(
            id=f"land-{aoi_id}",
            name="Safety Slice Plot",
            governorate="Sharqia",
            geometry=json.dumps(
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [31.0, 30.0],
                            [31.1, 30.0],
                            [31.1, 30.1],
                            [31.0, 30.1],
                            [31.0, 30.0],
                        ]
                    ],
                }
            ),
            area_feddan=25.0,
            aoi_id=aoi_id,
            job_id=f"job-{aoi_id}",
        )
        job = Job(id=f"job-{aoi_id}", land_id=land.id, status="succeeded")
        return land, job

    def test_good_coverage_completes_with_observed_land_status(self) -> None:
        assessment = self._build_assessment(self._base_quality_metrics())

        self.assertEqual(assessment["assessment_status"], "complete")
        self.assertEqual(assessment["satellite_evidence_coverage"]["status"], "good")
        self.assertEqual(assessment["confidence"]["level"], "high")
        self.assertEqual(assessment["land_status"], "active")
        self.assertEqual(assessment["risk_flags"], [])

    def test_limited_coverage_caps_confidence_without_changing_land_status(self) -> None:
        quality_metrics = self._base_quality_metrics()
        quality_metrics.update(
            {
                "gap_ratio": 0.35,
                "max_gap_days": 30.0,
                "gap_risk": "high",
                "gap_risk_reason": "Large observation gaps limit satellite evidence coverage.",
            }
        )

        assessment = self._build_assessment(quality_metrics)

        self.assertEqual(assessment["assessment_status"], "complete")
        self.assertEqual(assessment["satellite_evidence_coverage"]["status"], "limited")
        self.assertEqual(assessment["confidence"]["level"], "low")
        self.assertEqual(assessment["land_status"], "active")
        self.assertEqual(assessment["risk_flags"], [])

    def test_one_good_cycle_is_active_with_limited_history(self) -> None:
        quality_metrics = self._base_quality_metrics()
        paths = self._write_fixture_files(
            quality_metrics=quality_metrics,
            seasons=[
                {
                    "season_id": "S1",
                    "start_date": "2024-01-01",
                    "end_date": "2024-04-15",
                    "peak_date": "2024-03-01",
                    "quality_label": "good",
                    "confirmation_level": "strong",
                    "is_open": False,
                    "duration_days": 106,
                    "peak_ndvi": 0.70,
                    "evidence_summary": "Observed strong seasonal vegetation activity.",
                }
            ],
        )

        assessment = build_land_assessment(**paths)

        self.assertEqual(assessment["land_status"], "active")
        self.assertEqual(assessment["trend_2y"], "uncertain")
        self.assertEqual(assessment["history_coverage"]["status"], "limited_history")
        self.assertEqual(assessment["absence_assessment"]["status"], "activity_present")
        self.assertEqual(assessment["metrics_summary"]["interval_median_mndwi"], -0.3)
        self.assertEqual(assessment["metrics_summary"]["interval_median_ndvi_spread"], 0.05)
        self.assertFalse(any(flag["code"] == "possible_inactivity" for flag in assessment["risk_flags"]))

    def test_short_no_activity_window_does_not_claim_inactivity(self) -> None:
        quality_metrics = self._base_quality_metrics()
        quality_metrics.update({"usable_observation_count": 20})
        paths = self._write_fixture_files(
            quality_metrics=quality_metrics,
            seasons=[],
            ndvi_value=0.12,
            evi_value=0.10,
        )

        assessment = build_land_assessment(**paths)

        self.assertIsNone(assessment["land_status"])
        self.assertEqual(assessment["absence_assessment"]["status"], "not_assessed")
        self.assertFalse(any(flag["code"] == "possible_inactivity" for flag in assessment["risk_flags"]))

    def test_public_api_does_not_map_possible_inactivity_to_abandonment(self) -> None:
        data_root = self.tmpdir / "data-root-inactivity"
        aoi_id = "aoi-inactivity-public"
        quality_metrics = self._base_quality_metrics(aoi_id=aoi_id)
        paths = self._write_fixture_files(
            quality_metrics=quality_metrics,
            seasons=[],
            ndvi_value=0.12,
            evi_value=0.10,
        )
        assessment = build_land_assessment(**paths)

        with patch.dict(os.environ, {"FARMTRUST_DATA_DIR": str(data_root)}):
            write_land_assessment(assessment_dir(aoi_id), assessment)
            land, job = self._land_and_job(aoi_id=aoi_id)

            response = map_land_response(land, job)

        self.assertEqual(assessment["land_status"], "inactive")
        self.assertTrue(any(flag["code"] == "possible_inactivity" for flag in assessment["risk_flags"]))
        self.assertEqual(response.absence_assessment.status, "absence_supported")
        self.assertEqual(response.indicators.mndwi_median, -0.3)
        self.assertEqual(response.indicators.ndvi_spread_median, 0.05)
        self.assertNotIn("abandonment", response.flags or [])

    def test_insufficient_coverage_requires_manual_review(self) -> None:
        quality_metrics = self._base_quality_metrics()
        quality_metrics.update(
            {
                "gap_ratio": 0.70,
                "gap_risk": "high",
                "gap_risk_reason": "Satellite evidence gaps dominate the assessment window.",
            }
        )

        assessment = self._build_assessment(quality_metrics)

        self.assertEqual(assessment["assessment_status"], "manual_review_required")
        self.assertEqual(assessment["satellite_evidence_coverage"]["status"], "insufficient")
        self.assertEqual(assessment["confidence"]["level"], "low")
        self.assertIsNone(assessment["land_status"])
        self.assertIsNone(assessment["trend_2y"])
        self.assertIsNone(assessment["latest_season_performance"])
        self.assertEqual(assessment["risk_flags"], [])

    def test_public_api_mapping_suppresses_manual_review_outputs(self) -> None:
        data_root = self.tmpdir / "data-root"
        aoi_id = "aoi-public"
        quality_metrics = self._base_quality_metrics(aoi_id=aoi_id)
        quality_metrics.update(
            {
                "usable_observation_count": 8,
                "gap_risk": "high",
                "gap_risk_reason": "Too few usable satellite observations.",
            }
        )
        assessment = self._build_assessment(quality_metrics)

        with patch.dict(os.environ, {"FARMTRUST_DATA_DIR": str(data_root)}):
            write_land_assessment(assessment_dir(aoi_id), assessment)
            land = Land(
                id="land-public",
                name="Manual Review Plot",
                governorate="Sharqia",
                geometry=json.dumps(
                    {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [31.0, 30.0],
                                [31.1, 30.0],
                                [31.1, 30.1],
                                [31.0, 30.1],
                                [31.0, 30.0],
                            ]
                        ],
                    }
                ),
                area_feddan=25.0,
                aoi_id=aoi_id,
                job_id="job-public",
            )
            job = Job(id="job-public", land_id="land-public", status="succeeded")

            response = map_land_response(land, job)

        self.assertEqual(response.assessment_status, "manual_review_required")
        self.assertIsNone(response.land_status)
        self.assertIsNone(response.trend_2y)
        self.assertIsNone(response.season_performance)
        self.assertIsNone(response.risk_tier)
        self.assertEqual(response.flags, [])


if __name__ == "__main__":
    unittest.main()
