from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from datetime import timedelta

from farmtrust_core.scoring import build_land_assessment
from farmtrust_core.seasonal.seasons import (
    SeasonalObservation,
    build_season_payload,
    detect_activity_windows,
    detect_season_windows,
)
from tests.fixtures import phenology_synthetic as ps


def _observations(series: ps.SyntheticSeries, *, use_clean: bool = True) -> list[SeasonalObservation]:
    """Build detector observations from a synthetic series.

    ``use_clean`` feeds the noise-free true curve as the smoothed signal (a
    perfect upstream smoother); the detector re-derives its daily curve from it.
    """
    src = series.clean if use_clean else series.raw
    return [
        SeasonalObservation(
            timestamp=series.timestamps[i],
            ndvi_smoothed=src["ndvi"][i],
            evi_smoothed=src["evi"][i],
            ndmi_smoothed=src["ndmi"][i],
            ndwi_smoothed=src["ndwi"][i],
            valid_fraction=series.valid_fractions[i],
            source_row_count=1,
            is_usable=series.valid_fractions[i] >= 0.90,
        )
        for i in range(len(series.timestamps))
    ]


class ActivityWindowDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="farmtrust-activity-window-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_activity_detects_no_windows(self) -> None:
        windows = detect_season_windows(_observations(ps.flat_fallow()))
        self.assertEqual(windows, [])

    def test_weak_activity_below_minimum_amplitude_is_ignored(self) -> None:
        weak = ps.make_phenology_series(
            cycles=[ps.Cycle(peak_day=120.0, amplitude=0.08, rise_width=28.0, fall_width=34.0)],
            base=0.15,
            total_days=240,
            seed=41,
        )
        self.assertEqual(detect_season_windows(_observations(weak)), [])

    def test_borderline_activity_is_reported_separately(self) -> None:
        borderline_series = ps.make_phenology_series(
            cycles=[ps.Cycle(peak_day=120.0, amplitude=0.17, rise_width=28.0, fall_width=34.0)],
            base=0.16,
            total_days=240,
            seed=42,
        )
        confirmed, borderline = detect_activity_windows(_observations(borderline_series))
        self.assertEqual(confirmed, [])
        self.assertEqual(len(borderline), 1)
        self.assertEqual(borderline[0].detection_status, "borderline")

    def test_sustained_activity_window_is_detected(self) -> None:
        windows = detect_season_windows(_observations(ps.single_complete_cycle()))
        self.assertEqual(len(windows), 1)
        window = windows[0]
        self.assertEqual(window.window_type, "vegetation_activity")
        self.assertEqual(window.detection_status, "confirmed")
        self.assertEqual(window.lifecycle_status, "complete")
        self.assertEqual(window.quality_label, "good")
        self.assertFalse(window.provisional)
        self.assertFalse(window.is_open)
        # Monotonic boundaries.
        self.assertLess(window.start_date, window.peak_date)
        self.assertLess(window.peak_date, window.end_date)
        # Boundaries are model-derived but checked against real observations.
        self.assertEqual(window.start_boundary_source, "model_derived_analysis_curve")
        self.assertIsNotNone(window.start_nearest_real_observation_date)
        self.assertIsNotNone(window.peak_nearest_real_observation_days)
        self.assertIn("model-derived season-analysis curve", window.evidence_summary)

    def test_two_activity_windows_separated_by_a_gap(self) -> None:
        windows = detect_season_windows(_observations(ps.two_cycles_with_gap()))
        self.assertEqual(len(windows), 2)
        self.assertEqual([w.season_id for w in windows], ["season_01", "season_02"])
        for window in windows:
            self.assertEqual(window.lifecycle_status, "complete")

    def test_berseem_multicut_sawtooth_is_a_single_cycle(self) -> None:
        # A clover field cut several times should not fracture into many cycles.
        windows = detect_season_windows(_observations(ps.berseem_multicut_sawtooth()))
        self.assertEqual(len(windows), 1)

    def test_open_right_edge_window_is_provisional(self) -> None:
        windows = detect_season_windows(_observations(ps.open_right_cycle()))
        self.assertEqual(len(windows), 1)
        self.assertTrue(windows[0].is_open)
        self.assertTrue(windows[0].provisional)
        self.assertEqual(windows[0].lifecycle_status, "open_right")
        self.assertEqual(windows[0].end_boundary_certainty, "open")
        self.assertIn("provisional", windows[0].evidence_summary)

    def test_open_left_window_is_provisional(self) -> None:
        windows = detect_season_windows(_observations(ps.open_left_cycle()))
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].lifecycle_status, "open_left")
        self.assertTrue(windows[0].provisional)
        self.assertEqual(windows[0].start_boundary_certainty, "open")
        self.assertFalse(windows[0].is_open)  # is_open means right-edge unobserved only

    def test_detection_is_deterministic(self) -> None:
        obs = _observations(ps.double_crop_two_year())
        first = detect_season_windows(obs)
        second = detect_season_windows(obs)
        self.assertEqual(
            [(w.season_id, w.start_date, w.peak_date, w.end_date) for w in first],
            [(w.season_id, w.start_date, w.peak_date, w.end_date) for w in second],
        )

    def test_gap_overlap_marks_boundary_certainty(self) -> None:
        series = ps.single_complete_cycle()
        obs = _observations(series)
        # A long gap straddling the green-up third of the cycle.
        onset = series.timestamps[0] + timedelta(days=70)
        windows = detect_season_windows(
            obs,
            long_gap_windows=[
                {
                    "start_timestamp": onset.isoformat(),
                    "end_timestamp": (onset + timedelta(days=15)).isoformat(),
                    "gap_days": 15.0,
                }
            ],
        )
        self.assertEqual(len(windows), 1)
        self.assertTrue(windows[0].provisional)
        self.assertGreaterEqual(windows[0].gap_overlap_count, 1)

    def test_multi_index_confirmation_levels(self) -> None:
        base = ps.single_complete_cycle()
        strong = _observations(base)  # companion indices derived from NDVI -> support
        # Weak: flat companion indices that do not track the NDVI peak.
        weak = [
            SeasonalObservation(
                timestamp=o.timestamp,
                ndvi_smoothed=o.ndvi_smoothed,
                evi_smoothed=0.10,
                ndmi_smoothed=0.00,
                ndwi_smoothed=0.30,
                valid_fraction=o.valid_fraction,
                source_row_count=1,
                is_usable=o.is_usable,
            )
            for o in strong
        ]
        strong_windows = detect_season_windows(strong)
        weak_windows = detect_season_windows(weak)
        self.assertEqual(len(strong_windows), 1)
        self.assertEqual(len(weak_windows), 1)
        self.assertEqual(strong_windows[0].confirmation_level, "strong")
        self.assertEqual(weak_windows[0].confirmation_level, "weak")

    # ------------------------------------------------------------------
    # Payload + scoring integration (no-activity path)
    # ------------------------------------------------------------------

    def _write_smoothed_csv(self, path, observations) -> None:
        with open(path, "w", newline="", encoding="utf-8") as handle:
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
                    "valid_fraction",
                    "source_row_count",
                ]
            )
            for o in observations:
                writer.writerow(
                    [
                        o.timestamp.isoformat(),
                        o.ndvi_smoothed,
                        o.ndvi_smoothed + 0.05,
                        0.05,
                        o.evi_smoothed,
                        o.ndmi_smoothed,
                        o.ndwi_smoothed,
                        -0.30,
                        str(o.is_usable).lower(),
                        o.valid_fraction,
                        o.source_row_count,
                    ]
                )

    def test_build_payload_allows_no_activity_windows(self) -> None:
        from pathlib import Path

        smoothed_csv_path = Path(self.tmpdir) / "ndvi_smoothed.csv"
        quality_metrics_path = Path(self.tmpdir) / "quality_metrics.json"
        quality_metrics_path.write_text(
            json.dumps(
                {
                    "aoi_id": "aoi-no-activity",
                    "usable_observation_count": 30,
                    "gap_ratio": 0.0,
                    "max_gap_days": 5.0,
                    "gap_risk": "low",
                    "long_gap_windows": [],
                }
            ),
            encoding="utf-8",
        )
        self._write_smoothed_csv(smoothed_csv_path, _observations(ps.flat_fallow()))

        payload = build_season_payload(smoothed_csv_path, quality_metrics_path)

        self.assertEqual(payload["season_count"], 0)
        self.assertEqual(payload["seasons"], [])
        self.assertIn("activity window", payload["terminology"]["season"])
        self.assertEqual(
            payload["activity_detection_model"]["gap_confidence_source"],
            "real_usable_observation_timestamps",
        )

    def test_scoring_handles_no_activity_window_payload(self) -> None:
        from pathlib import Path

        run_metadata_path = Path(self.tmpdir) / "run_metadata.json"
        smoothed_csv_path = Path(self.tmpdir) / "ndvi_smoothed.csv"
        quality_metrics_path = Path(self.tmpdir) / "quality_metrics.json"
        season_payload_path = Path(self.tmpdir) / "season_windows.json"
        run_metadata_path.write_text(
            json.dumps({"aoi_id": "aoi-inactive", "start_date": "2024-01-01", "end_date": "2024-12-30"}),
            encoding="utf-8",
        )
        quality_metrics_path.write_text(
            json.dumps(
                {
                    "aoi_id": "aoi-inactive",
                    "usable_observation_count": 60,
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
        fallow = ps.flat_fallow()
        self._write_smoothed_csv(smoothed_csv_path, _observations(fallow))
        season_payload_path.write_text(
            json.dumps(
                {
                    "aoi_id": "aoi-inactive",
                    "season_count": 0,
                    "gap_risk": "low",
                    "terminology": {"season": "detected vegetation activity window, not an agronomic crop season"},
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


if __name__ == "__main__":
    unittest.main()
