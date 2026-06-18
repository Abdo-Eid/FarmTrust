from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from farmtrust_core.scoring import build_land_assessment
from farmtrust_core.seasonal.seasons import (
    MIN_ACTIVITY_AMPLITUDE,
    SeasonWindow,
    SeasonalObservation,
    build_season_payload,
    detect_season_windows,
)


def _timestamp(day: int) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)


def _observations(
    days: list[int],
    ndvi_values: list[float],
    *,
    evi: float = 0.26,
    ndmi: float = 0.12,
    ndwi: float = -0.12,
) -> list[SeasonalObservation]:
    return [
        SeasonalObservation(
            timestamp=_timestamp(day),
            ndvi_smoothed=ndvi,
            evi_smoothed=evi,
            ndmi_smoothed=ndmi,
            ndwi_smoothed=ndwi,
            valid_fraction=0.95,
            source_row_count=1,
        )
        for day, ndvi in zip(days, ndvi_values)
    ]


class ActivityWindowDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="farmtrust-activity-window-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_activity_detects_no_windows(self) -> None:
        windows = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25],
                [0.10, 0.12, 0.13, 0.12, 0.14, 0.13],
            )
        )

        self.assertEqual(windows, [])

    def test_weak_activity_below_minimum_amplitude_is_ignored(self) -> None:
        windows = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25],
                [0.18, 0.19, 0.20, 0.21, 0.205, 0.19],
            )
        )

        self.assertEqual(windows, [])
        self.assertGreater(MIN_ACTIVITY_AMPLITUDE, 0.0)

    def test_sustained_activity_window_is_detected_from_smoothed_ndvi(self) -> None:
        windows = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                [0.12, 0.13, 0.15, 0.20, 0.25, 0.32, 0.42, 0.38, 0.31, 0.25, 0.17],
            )
        )

        self.assertEqual(len(windows), 1)
        window = windows[0]
        self.assertEqual(window.window_type, "vegetation_activity")
        self.assertEqual(window.quality_label, "good")
        self.assertEqual(window.confirmation_level, "strong")
        self.assertEqual(window.start_date, "2024-01-21")
        self.assertEqual(window.peak_date, "2024-01-31")
        self.assertEqual(window.end_date, "2024-02-15")
        self.assertGreaterEqual(window.amplitude_ndvi, 0.08)
        self.assertFalse(window.provisional)

    def test_two_activity_windows_are_detected_when_separated_by_low_observations(self) -> None:
        windows = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25, 30, 60, 65, 70, 75, 80, 85, 90],
                [0.12, 0.22, 0.33, 0.41, 0.35, 0.25, 0.12, 0.13, 0.23, 0.34, 0.43, 0.36, 0.25, 0.13],
            )
        )

        self.assertEqual(len(windows), 2)
        self.assertEqual([window.season_id for window in windows], ["season_01", "season_02"])

    def test_gap_overlap_marks_boundary_certainty_without_changing_window_label(self) -> None:
        observations = _observations(
            [0, 5, 10, 15, 20, 25, 30, 35, 40],
            [0.12, 0.25, 0.31, 0.41, 0.39, 0.35, 0.31, 0.25, 0.14],
        )
        windows = detect_season_windows(
            observations,
            long_gap_windows=[
                {
                    "start_timestamp": _timestamp(10).isoformat(),
                    "end_timestamp": _timestamp(12).isoformat(),
                    "gap_days": 12.5,
                }
            ],
        )

        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].quality_label, "good")
        self.assertTrue(windows[0].provisional)
        self.assertEqual(windows[0].start_boundary_certainty, "limited")
        self.assertEqual(windows[0].peak_certainty, "limited")
        self.assertEqual(windows[0].gap_overlap_stage, "multiple")

    def test_open_right_edge_window_is_provisional(self) -> None:
        windows = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25, 30, 35, 40],
                [0.12, 0.14, 0.20, 0.26, 0.33, 0.37, 0.40, 0.42, 0.43],
            )
        )

        self.assertEqual(len(windows), 1)
        self.assertTrue(windows[0].is_open)
        self.assertTrue(windows[0].provisional)
        self.assertEqual(windows[0].end_boundary_certainty, "open")
        self.assertIn("provisional", windows[0].evidence_summary)

    def test_confirmation_support_uses_evi_ndmi_ndwi(self) -> None:
        weak_support = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25, 30, 35],
                [0.12, 0.21, 0.30, 0.40, 0.38, 0.32, 0.25, 0.13],
                evi=0.10,
                ndmi=0.00,
                ndwi=0.30,
            )
        )
        strong_support = detect_season_windows(
            _observations(
                [0, 5, 10, 15, 20, 25, 30, 35],
                [0.12, 0.21, 0.30, 0.40, 0.38, 0.32, 0.25, 0.13],
                evi=0.26,
                ndmi=0.10,
                ndwi=-0.10,
            )
        )

        self.assertEqual(weak_support[0].confirmation_level, "weak")
        self.assertEqual(weak_support[0].quality_label, "weak")
        self.assertEqual(strong_support[0].confirmation_level, "strong")
        self.assertEqual(strong_support[0].quality_label, "good")

    def test_build_payload_allows_no_activity_windows(self) -> None:
        smoothed_csv_path = self.tmpdir / "ndvi_smoothed.csv"
        quality_metrics_path = self.tmpdir / "quality_metrics.json"
        quality_metrics_path.write_text(
            json.dumps(
                {
                    "aoi_id": "aoi-no-activity",
                    "usable_observation_count": 6,
                    "gap_ratio": 0.0,
                    "max_gap_days": 5.0,
                    "gap_risk": "low",
                    "long_gap_windows": [],
                }
            ),
            encoding="utf-8",
        )
        self._write_smoothed_csv(
            smoothed_csv_path,
            _observations(
                [0, 5, 10, 15, 20, 25],
                [0.10, 0.12, 0.13, 0.12, 0.14, 0.13],
            ),
        )

        payload = build_season_payload(smoothed_csv_path, quality_metrics_path)

        self.assertEqual(payload["season_count"], 0)
        self.assertEqual(payload["seasons"], [])
        self.assertIn("activity window", payload["terminology"]["season"])

    def test_scoring_handles_no_activity_window_payload(self) -> None:
        run_metadata_path = self.tmpdir / "run_metadata.json"
        smoothed_csv_path = self.tmpdir / "ndvi_smoothed.csv"
        quality_metrics_path = self.tmpdir / "quality_metrics.json"
        season_payload_path = self.tmpdir / "season_windows.json"
        run_metadata_path.write_text(
            json.dumps({"aoi_id": "aoi-inactive", "start_date": "2024-01-01", "end_date": "2024-01-30"}),
            encoding="utf-8",
        )
        quality_metrics_path.write_text(
            json.dumps(
                {
                    "aoi_id": "aoi-inactive",
                    "usable_observation_count": 80,
                    "gap_ratio": 0.0,
                    "max_gap_days": 5.0,
                    "long_gap_count": 0,
                    "long_gap_windows": [],
                    "gap_risk": "low",
                    "gap_risk_reason": "Observation continuity is strong enough for assessment.",
                }
            ),
            encoding="utf-8",
        )
        observations = _observations(
            list(range(0, 400, 5)),
            [0.12] * 80,
        )
        self._write_smoothed_csv(smoothed_csv_path, observations)
        season_payload_path.write_text(
            json.dumps(
                {
                    "aoi_id": "aoi-inactive",
                    "season_count": 0,
                    "gap_risk": "low",
                    "terminology": {
                        "season": "detected vegetation activity window, not an agronomic crop season",
                    },
                    "seasons": [],
                }
            ),
            encoding="utf-8",
        )

        assessment = build_land_assessment(
            run_metadata_path=run_metadata_path,
            smoothed_csv_path=smoothed_csv_path,
            quality_metrics_path=quality_metrics_path,
            season_payload_path=season_payload_path,
        )

        self.assertEqual(assessment["assessment_status"], "complete")
        self.assertEqual(assessment["land_status"], "inactive")
        self.assertEqual(assessment["trend_2y"], "uncertain")
        self.assertIsNone(assessment["latest_season_performance"])

    def _write_smoothed_csv(self, path: Path, observations: list[SeasonalObservation]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "timestamp",
                    "ndvi_smoothed",
                    "evi_smoothed",
                    "ndmi_smoothed",
                    "ndwi_smoothed",
                    "is_usable",
                    "valid_fraction",
                    "source_row_count",
                ]
            )
            for observation in observations:
                writer.writerow(
                    [
                        observation.timestamp.isoformat(),
                        observation.ndvi_smoothed,
                        observation.evi_smoothed,
                        observation.ndmi_smoothed,
                        observation.ndwi_smoothed,
                        "true",
                        observation.valid_fraction,
                        observation.source_row_count,
                    ]
                )


if __name__ == "__main__":
    unittest.main()
