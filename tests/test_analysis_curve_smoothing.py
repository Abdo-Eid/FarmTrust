from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from farmtrust_core.preprocess import analysis_curve as ac
from farmtrust_core.preprocess import (
    build_preprocess_artifacts,
    write_preprocess_outputs,
)
from tests.fixtures import phenology_synthetic as ps

INPUT_COLUMNS = [
    "item_id",
    "timestamp",
    "valid_fraction",
    "ndvi_mean",
    "ndvi_p95",
    "evi_mean",
    "evi_p95",
    "ndmi_mean",
    "ndmi_p95",
    "ndwi_mean",
    "ndwi_p95",
    "mndwi_mean",
    "mndwi_p95",
]


def _roughness(curve: list[float]) -> float:
    z = np.asarray(curve, dtype=float)
    return float(np.sum(np.diff(z, 2) ** 2))


def _write_indices_csv(path: Path, series: ps.SyntheticSeries) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(INPUT_COLUMNS)
        for i, ts in enumerate(series.timestamps):
            ndvi = series.raw["ndvi"][i]
            writer.writerow(
                [
                    f"item-{i}",
                    ts.isoformat(),
                    series.valid_fractions[i],
                    ndvi,
                    ndvi + 0.05,
                    series.raw["evi"][i],
                    series.raw["evi"][i] + 0.04,
                    series.raw["ndmi"][i],
                    series.raw["ndmi"][i] + 0.04,
                    series.raw["ndwi"][i],
                    series.raw["ndwi"][i] + 0.04,
                    series.raw["mndwi"][i],
                    series.raw["mndwi"][i] + 0.04,
                ]
            )


class AnalysisCurveUnitTests(unittest.TestCase):
    def test_penalty_bands_match_dense_second_difference(self) -> None:
        for n in (3, 4, 5, 9, 20):
            d_matrix = np.diff(np.eye(n), 2, axis=0)
            penalty = d_matrix.T @ d_matrix
            main, off1, off2 = ac._second_difference_penalty_bands(n)
            self.assertTrue(np.allclose(main, np.diag(penalty)))
            self.assertTrue(np.allclose(off1, np.diag(penalty, 1)))
            self.assertTrue(np.allclose(off2, np.diag(penalty, 2)))

    def test_lambda_from_timescale_mapping(self) -> None:
        # 45-day window lands in the documented sweet spot.
        lam, reason = ac.select_lambda()
        self.assertEqual(reason, "phenology_timescale")
        self.assertGreater(lam, 1500.0)
        self.assertLess(lam, 4000.0)
        # Longer window -> stronger smoothing.
        self.assertGreater(ac.lambda_for_timescale(60), ac.lambda_for_timescale(40))

    def test_curve_is_deterministic(self) -> None:
        series = ps.double_crop_two_year()
        values = {
            "ndvi": series.raw["ndvi"],
            "evi": series.raw["evi"],
            "ndmi": series.raw["ndmi"],
            "ndwi": series.raw["ndwi"],
            "mndwi": series.raw["mndwi"],
        }
        a = ac.build_analysis_curves(
            timestamps=series.timestamps, index_values=values, valid_fractions=series.valid_fractions
        )
        b = ac.build_analysis_curves(
            timestamps=series.timestamps, index_values=values, valid_fractions=series.valid_fractions
        )
        self.assertEqual(a.selected_lambda, b.selected_lambda)
        self.assertEqual(a.curves["ndvi"], b.curves["ndvi"])

    def test_gap_interpolation_is_finite_without_overshoot(self) -> None:
        series = ps.two_cycles_with_gap()
        result = ac.build_analysis_curves(
            timestamps=series.timestamps,
            index_values={"ndvi": series.raw["ndvi"]},
            valid_fractions=series.valid_fractions,
        )
        curve = np.asarray(result.curves["ndvi"])
        self.assertTrue(np.isfinite(curve).all())
        # Curve never escapes the observed data envelope (no wild gap overshoot).
        observed = np.asarray(series.raw["ndvi"])
        self.assertLessEqual(curve.max(), observed.max() + 0.1)
        self.assertGreaterEqual(curve.min(), observed.min() - 0.1)

    def test_higher_lambda_increases_smoothness(self) -> None:
        series = ps.double_crop_two_year()
        values = {"ndvi": series.raw["ndvi"]}
        soft = ac.build_analysis_curves(
            timestamps=series.timestamps, index_values=values,
            valid_fractions=series.valid_fractions, lam=10.0,
        )
        stiff = ac.build_analysis_curves(
            timestamps=series.timestamps, index_values=values,
            valid_fractions=series.valid_fractions, lam=20000.0,
        )
        self.assertLess(_roughness(stiff.curves["ndvi"]), _roughness(soft.curves["ndvi"]))

    def test_low_quality_cloud_dip_is_downweighted(self) -> None:
        # Flat high NDVI with one deep cloud dip carrying a low valid_fraction.
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ts = [start + timedelta(days=5 * i) for i in range(11)]
        ndvi = [0.70] * 11
        ndvi[5] = 0.20  # cloud-contaminated dip
        vf = [0.97] * 11
        vf[5] = 0.30  # low confidence at the dip
        result = ac.build_analysis_curves(
            timestamps=ts, index_values={"ndvi": ndvi}, valid_fractions=vf,
        )
        smoothed_at_dip = ac.sample_curve_at_observations(result, ts, "ndvi")[5]
        self.assertGreater(smoothed_at_dip, 0.45)  # pulled well back toward neighbours

    def test_real_time_aware_not_index_domain(self) -> None:
        # Identical value sequence, different real-day spacing -> different curves.
        vals = [0.2, 0.25, 0.7, 0.72, 0.3, 0.2]
        vf = [0.95] * 6
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        even = [start + timedelta(days=5 * i) for i in range(6)]
        uneven = [start + timedelta(days=d) for d in (0, 5, 10, 15, 60, 65)]
        a = ac.build_analysis_curves(timestamps=even, index_values={"ndvi": vals}, valid_fractions=vf, lam=100.0)
        b = ac.build_analysis_curves(timestamps=uneven, index_values={"ndvi": vals}, valid_fractions=vf, lam=100.0)
        self.assertNotEqual(a.n_days, b.n_days)
        sa = ac.sample_curve_at_observations(a, even, "ndvi")
        sb = ac.sample_curve_at_observations(b, uneven, "ndvi")
        self.assertFalse(np.allclose(sa, sb))

    def test_bare_soil_trough_preserved(self) -> None:
        series = ps.double_crop_two_year()
        result = ac.build_analysis_curves(
            timestamps=series.timestamps,
            index_values={"ndvi": series.raw["ndvi"]},
            valid_fractions=series.valid_fractions,
        )
        curve = np.asarray(result.curves["ndvi"])
        # Real bare-soil dips between cycles are not smoothed away.
        self.assertLess(curve.min(), 0.30)
        self.assertGreater(curve.max(), 0.60)

    def test_single_observation_returns_constant(self) -> None:
        ts = [datetime(2024, 1, 1, tzinfo=timezone.utc)]
        result = ac.build_analysis_curves(
            timestamps=ts, index_values={"ndvi": [0.42]}, valid_fractions=[0.95]
        )
        self.assertEqual(result.curves["ndvi"], [0.42])

    def test_no_usable_observations_raises(self) -> None:
        ts = [datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=5 * i) for i in range(4)]
        with self.assertRaises(ValueError):
            ac.build_analysis_curves(
                timestamps=ts, index_values={"ndvi": [0.4] * 4}, valid_fractions=[0.0] * 4
            )

    def test_nan_value_does_not_corrupt_curve(self) -> None:
        ts = [datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=5 * i) for i in range(8)]
        ndvi = [0.2, 0.3, float("nan"), 0.6, 0.7, 0.5, 0.3, 0.2]
        vf = [0.95, 0.95, 0.0, 0.95, 0.95, 0.95, 0.95, 0.95]
        result = ac.build_analysis_curves(
            timestamps=ts, index_values={"ndvi": ndvi}, valid_fractions=vf
        )
        self.assertTrue(np.isfinite(np.asarray(result.curves["ndvi"])).all())


class PreprocessIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="farmtrust-analysis-curve-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, series: ps.SyntheticSeries):
        input_dir = self.tmpdir / "input"
        output_dir = self.tmpdir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        csv_path = input_dir / "indices_timeseries.csv"
        metadata_path = input_dir / "run_metadata.json"
        metadata_path.write_text(json.dumps({"aoi_id": "aoi-curve"}), encoding="utf-8")
        _write_indices_csv(csv_path, series)
        artifacts = build_preprocess_artifacts(csv_path=csv_path, metadata_path=metadata_path)
        paths = write_preprocess_outputs(
            output_dir=output_dir,
            processed_observations=artifacts["processed_observations"],
            quality_metrics=artifacts["quality_metrics"],
            analysis_curve=artifacts["analysis_curve"],
        )
        return artifacts, paths

    def test_rows_preserved_and_every_row_smoothed(self) -> None:
        series = ps.double_crop_two_year()
        _, paths = self._run(series)
        with paths["csv_path"].open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), len(series.timestamps))
        for row in rows:
            self.assertNotEqual(row["ndvi_smoothed"].strip(), "")
            self.assertNotEqual(row["mndwi_smoothed"].strip(), "")
            self.assertTrue(np.isfinite(float(row["ndvi_smoothed"])))

    def test_unusable_rows_still_filled_and_smoothed(self) -> None:
        # Inject a low-valid-fraction (unusable) observation; it must keep finite
        # filled + smoothed analysis values while staying is_usable=false.
        series = ps.single_complete_cycle()
        series.valid_fractions[3] = 0.50
        _, paths = self._run(series)
        with paths["csv_path"].open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[3]["is_usable"], "false")
        self.assertNotEqual(rows[3]["ndvi_filled"].strip(), "")
        self.assertNotEqual(rows[3]["ndvi_smoothed"].strip(), "")

    def test_quality_metrics_describe_whittaker(self) -> None:
        artifacts, _ = self._run(ps.single_complete_cycle())
        metrics = artifacts["quality_metrics"]
        self.assertEqual(metrics["smoothing_method"], "weighted_whittaker_eilers_daily_grid")
        self.assertEqual(metrics["lambda_selection_method"], "phenology_timescale_fixed_day_window")
        self.assertTrue(np.isfinite(metrics["selected_lambda"]))
        self.assertGreaterEqual(metrics["selected_lambda"], ac.LAMBDA_MIN)
        self.assertLessEqual(metrics["selected_lambda"], ac.LAMBDA_MAX)
        self.assertFalse(metrics["analysis_curve_direct_evidence"])
        self.assertTrue(metrics["creates_synthetic_timestamps"])
        # The misleading legacy gap-aware keys are gone.
        self.assertNotIn("max_smoothing_gap_days", metrics)
        self.assertNotIn("minimum_local_neighbors", metrics)

    def test_daily_analysis_curve_artifact(self) -> None:
        series = ps.single_complete_cycle()
        _, paths = self._run(series)
        self.assertIn("analysis_curve_path", paths)
        with paths["analysis_curve_path"].open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            list(rows[0].keys()),
            ["date", "day_offset", "is_observed_day", "analysis_weight",
             "ndvi_curve", "evi_curve", "ndmi_curve", "ndwi_curve", "mndwi_curve"],
        )
        # One row per grid day, contiguous, observed flag true on observation dates.
        spans = (series.timestamps[-1].date() - series.timestamps[0].date()).days + 1
        self.assertEqual(len(rows), spans)
        observed = sum(1 for r in rows if r["is_observed_day"] == "true")
        observed_dates = {ts.date().isoformat() for ts in series.timestamps}
        self.assertEqual(observed, len(observed_dates))

    def test_curve_inclusion_does_not_change_gap_evidence(self) -> None:
        # Both variants keep obs[7] unusable (vf < 0.90 strict gate), so the
        # gap/usable evidence must be identical -- even though the looser curve
        # inclusion gate (0.30) treats 0.50 as an anchor and 0.20 as a gap.
        series_a = ps.single_complete_cycle()
        series_a.valid_fractions[7] = 0.50
        series_b = ps.single_complete_cycle()
        series_b.valid_fractions[7] = 0.20
        a, _ = self._run(series_a)
        b, _ = self._run(series_b)
        for key in ("usable_observation_count", "gap_ratio", "max_gap_days", "gap_risk"):
            self.assertEqual(a["quality_metrics"][key], b["quality_metrics"][key])


if __name__ == "__main__":
    unittest.main()
