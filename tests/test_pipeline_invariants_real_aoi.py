"""Invariant integration tests on the real reference AOIs.

These are NOT golden-file tests (T-11 decided against locking exact values during
active iteration). They assert structural invariants on the two reference parcels
and skip cleanly if the source data is absent.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from farmtrust_core.preprocess import build_preprocess_artifacts, write_preprocess_outputs
from farmtrust_core.preprocess.analysis_curve import LAMBDA_MAX, LAMBDA_MIN
from farmtrust_core.scoring import build_land_assessment
from farmtrust_core.seasonal import build_season_payload, write_season_payload
from farmtrust_core.seasonal.seasons import load_daily_analysis_curve
from outputs.tools.hmm_comparison import compare_detector_and_hmm
from outputs.tools.hmm_phenology import decode_phenology

REPO_ROOT = Path(__file__).resolve().parents[1]
MENOFIA = REPO_ROOT / "data" / "aoi_demo_01"
SHORT_AOI = REPO_ROOT / "data" / "land-c92521f9627b4cc1a9e0ef65909a1820"


def _status_value(value) -> str:
    if isinstance(value, dict):
        return str(value.get("status", ""))
    return str(value)


class _RealAoiRun:
    def __init__(self, source: Path) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="farmtrust-real-aoi-"))
        artifacts = build_preprocess_artifacts(
            csv_path=source / "indices_timeseries.csv",
            metadata_path=source / "run_metadata.json",
        )
        paths = write_preprocess_outputs(
            output_dir=self.tmp,
            processed_observations=artifacts["processed_observations"],
            quality_metrics=artifacts["quality_metrics"],
            analysis_curve=artifacts["analysis_curve"],
        )
        self.quality_metrics = artifacts["quality_metrics"]
        self.payload = build_season_payload(
            smoothed_csv_path=paths["csv_path"],
            quality_metrics_path=paths["metrics_path"],
            daily_curve_path=paths["analysis_curve_path"],
        )
        self.season_windows_path = write_season_payload(output_dir=self.tmp, payload=self.payload)
        self.assessment = build_land_assessment(
            run_metadata_path=source / "run_metadata.json",
            smoothed_csv_path=paths["csv_path"],
            quality_metrics_path=paths["metrics_path"],
            season_payload_path=self.season_windows_path,
        )
        self.curve = load_daily_analysis_curve(paths["analysis_curve_path"])

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


def _assert_window_invariants(testcase: unittest.TestCase, payload: dict) -> None:
    seasons = payload["seasons"]
    prev_start = None
    open_left = open_right = 0
    for season in seasons:
        start = date.fromisoformat(season["start_date"])
        peak = date.fromisoformat(season["peak_date"])
        end = date.fromisoformat(season["end_date"])
        testcase.assertLessEqual(start, peak)
        testcase.assertLessEqual(peak, end)
        if prev_start is not None:
            testcase.assertGreaterEqual(start, prev_start)  # start-sorted
        prev_start = start
        if season["lifecycle_status"] in ("open_left", "open_both"):
            open_left += 1
        if season["lifecycle_status"] in ("open_right", "open_both"):
            open_right += 1
        testcase.assertEqual(season["start_boundary_source"], "model_derived_analysis_curve")
    testcase.assertLessEqual(open_left, 1)
    testcase.assertLessEqual(open_right, 1)


@unittest.skipUnless(MENOFIA.exists(), "aoi_demo_01 source data not present")
class MenofiaInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aoi = _RealAoiRun(MENOFIA)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.aoi.cleanup()

    def test_plausible_cycle_count(self) -> None:
        self.assertGreaterEqual(self.aoi.payload["season_count"], 3)
        self.assertLessEqual(self.aoi.payload["season_count"], 6)

    def test_no_false_abandonment(self) -> None:
        self.assertEqual(_status_value(self.aoi.assessment["land_status"]), "active")
        self.assertEqual(_status_value(self.aoi.assessment["absence_assessment"]), "activity_present")
        self.assertNotIn("abandonment", json.dumps(self.aoi.assessment).lower())

    def test_window_invariants(self) -> None:
        _assert_window_invariants(self, self.aoi.payload)

    def test_lambda_in_bounds_not_pinned(self) -> None:
        lam = self.aoi.quality_metrics["selected_lambda"]
        self.assertGreater(lam, LAMBDA_MIN)
        self.assertLess(lam, LAMBDA_MAX)

    def test_bare_soil_troughs_preserved(self) -> None:
        curve = np.asarray(self.aoi.curve.ndvi)
        self.assertLess(curve.min(), 0.35)  # real turnover dips not smoothed away
        self.assertGreater(curve.max(), 0.6)

    def test_determinism(self) -> None:
        second = build_season_payload(
            smoothed_csv_path=self.aoi.tmp / "ndvi_smoothed.csv",
            quality_metrics_path=self.aoi.tmp / "quality_metrics.json",
            daily_curve_path=self.aoi.tmp / "season_analysis_curve.csv",
        )
        self.assertEqual(
            json.dumps(self.aoi.payload, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_hmm_agrees_on_cycle_count(self) -> None:
        result = decode_phenology(self.aoi.curve.dates, self.aoi.curve.ndvi)
        comparison = compare_detector_and_hmm(self.aoi.payload["seasons"], result.cycles)
        self.assertEqual(comparison["cycle_count_delta"], 0)
        self.assertLessEqual(comparison["max_abs_pos_delta_days"] or 0, 30)


@unittest.skipUnless(SHORT_AOI.exists(), "short land AOI source data not present")
class ShortAoiInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aoi = _RealAoiRun(SHORT_AOI)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.aoi.cleanup()

    def test_cycle_count_small(self) -> None:
        self.assertLessEqual(self.aoi.payload["season_count"], 2)

    def test_no_false_abandonment_on_short_history(self) -> None:
        self.assertIn(_status_value(self.aoi.assessment["land_status"]), ("active", "intermittent"))
        self.assertIn(
            _status_value(self.aoi.assessment["history_coverage"]),
            ("limited_history", "insufficient_history"),
        )
        self.assertNotEqual(_status_value(self.aoi.assessment["absence_assessment"]), "absence_supported")

    def test_window_invariants(self) -> None:
        _assert_window_invariants(self, self.aoi.payload)


if __name__ == "__main__":
    unittest.main()
