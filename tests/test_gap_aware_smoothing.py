from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from farmtrust_core.preprocess.pipeline import (
    build_preprocess_artifacts,
    write_preprocess_outputs,
)
from farmtrust_core.preprocess.smoothing import (
    LOCAL_WINDOW_DAYS,
    MAX_SMOOTHING_GAP_DAYS,
    MIN_LOCAL_NEIGHBORS,
    SMOOTHING_METHOD_NAME,
    smooth_usable_values,
)
from farmtrust_core.seasonal.seasons import (
    SeasonalObservation,
    _compute_multi_index_confirmation,
)


def _timestamps(*days: int) -> list[datetime]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [start + timedelta(days=day) for day in days]


class GapAwareSmoothingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="farmtrust-gap-smoothing-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_spike_reduction_inside_continuous_segment(self) -> None:
        result = smooth_usable_values(
            timestamps=_timestamps(0, 5, 10, 15, 20),
            values=[0.30, 0.31, 0.90, 0.32, 0.33],
            valid_fractions=[0.95, 0.95, 0.95, 0.95, 0.95],
        )

        self.assertLess(result[2], 0.50)
        self.assertGreater(result[2], 0.30)

    def test_gap_greater_than_12_days_blocks_smoothing_continuity(self) -> None:
        result = smooth_usable_values(
            timestamps=_timestamps(0, 5, 10, 23, 28, 33),
            values=[0.30, 0.90, 0.31, 0.20, 0.90, 0.21],
            valid_fractions=[0.95] * 6,
        )

        self.assertLess(result[1], 0.60)
        self.assertLess(result[4], 0.60)

    def test_gap_exactly_12_days_remains_continuous(self) -> None:
        result = smooth_usable_values(
            timestamps=_timestamps(0, 12, 24),
            values=[0.30, 0.90, 0.31],
            valid_fractions=[0.95, 0.95, 0.95],
        )

        self.assertLess(result[1], 0.90)

    def test_insufficient_neighbors_keep_raw_at_edges(self) -> None:
        result = smooth_usable_values(
            timestamps=_timestamps(0, 5, 17),
            values=[0.30, 0.90, 0.31],
            valid_fractions=[0.95, 0.95, 0.95],
        )

        self.assertEqual(result[0], 0.30)
        self.assertNotEqual(result[1], 0.90)

    def test_one_and_two_point_segments_keep_raw(self) -> None:
        one_point = smooth_usable_values(
            timestamps=_timestamps(0),
            values=[0.30],
            valid_fractions=[0.95],
        )
        two_points = smooth_usable_values(
            timestamps=_timestamps(0, 5),
            values=[0.30, 0.90],
            valid_fractions=[0.95, 0.95],
        )

        self.assertEqual(one_point, [0.30])
        self.assertEqual(two_points, [0.30, 0.90])

    def test_preprocess_preserves_rows_without_interpolation_and_keeps_unusable_blank(self) -> None:
        input_dir = self.tmpdir / "input"
        output_dir = self.tmpdir / "output"
        input_dir.mkdir()
        csv_path = input_dir / "indices_timeseries.csv"
        metadata_path = input_dir / "run_metadata.json"
        metadata_path.write_text(json.dumps({"aoi_id": "aoi-smoothing"}), encoding="utf-8")

        rows = [
            (0, 0.95, 0.30),
            (5, 0.95, 0.31),
            (10, 0.50, 0.95),
            (15, 0.95, 0.90),
            (20, 0.95, 0.32),
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "item_id",
                    "timestamp",
                    "valid_fraction",
                    "ndvi_mean",
                    "evi_mean",
                    "ndmi_mean",
                    "ndwi_mean",
                ]
            )
            for index, (day, valid_fraction, ndvi) in enumerate(rows):
                writer.writerow(
                    [
                        f"item-{index}",
                        _timestamps(day)[0].isoformat(),
                        valid_fraction,
                        ndvi,
                        ndvi * 0.8,
                        0.20,
                        -0.20,
                    ]
                )

        artifacts = build_preprocess_artifacts(csv_path=csv_path, metadata_path=metadata_path)
        paths = write_preprocess_outputs(
            output_dir=output_dir,
            processed_observations=artifacts["processed_observations"],
            quality_metrics=artifacts["quality_metrics"],
        )

        with paths["csv_path"].open("r", newline="", encoding="utf-8") as handle:
            output_rows = list(csv.DictReader(handle))

        self.assertEqual(len(output_rows), len(rows))
        self.assertEqual(output_rows[2]["is_usable"], "false")
        self.assertEqual(output_rows[2]["ndvi_smoothed"], "")
        self.assertEqual(output_rows[2]["ndvi_raw"], "0.95")
        self.assertEqual([row["timestamp"] for row in output_rows], [_timestamps(day)[0].isoformat() for day, _, _ in rows])

    def test_quality_metrics_include_smoothing_metadata(self) -> None:
        input_dir = self.tmpdir / "metadata-input"
        input_dir.mkdir()
        csv_path = input_dir / "indices_timeseries.csv"
        metadata_path = input_dir / "run_metadata.json"
        metadata_path.write_text(json.dumps({"aoi_id": "aoi-metadata"}), encoding="utf-8")

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "item_id",
                    "timestamp",
                    "valid_fraction",
                    "ndvi_mean",
                    "evi_mean",
                    "ndmi_mean",
                    "ndwi_mean",
                ]
            )
            for index, timestamp in enumerate(_timestamps(0, 5, 10)):
                writer.writerow([f"item-{index}", timestamp.isoformat(), 0.95, 0.30, 0.24, 0.20, -0.20])

        artifacts = build_preprocess_artifacts(csv_path=csv_path, metadata_path=metadata_path)
        metrics = artifacts["quality_metrics"]

        self.assertEqual(metrics["smoothing_method"], SMOOTHING_METHOD_NAME)
        self.assertEqual(metrics["max_smoothing_gap_days"], MAX_SMOOTHING_GAP_DAYS)
        self.assertEqual(metrics["local_window_days"], LOCAL_WINDOW_DAYS)
        self.assertEqual(metrics["minimum_local_neighbors"], MIN_LOCAL_NEIGHBORS)
        self.assertEqual(metrics["interpolation_policy"], "none")
        self.assertFalse(metrics["creates_synthetic_timestamps"])
        self.assertTrue(metrics["smooths_only_usable_observations"])

    def test_seasonal_confirmation_uses_smoothed_non_ndvi_signals(self) -> None:
        observations = [
            SeasonalObservation(
                timestamp=timestamp,
                ndvi_smoothed=ndvi,
                evi_smoothed=evi,
                ndmi_smoothed=ndmi,
                ndwi_smoothed=ndwi,
                valid_fraction=0.95,
                source_row_count=1,
            )
            for timestamp, ndvi, evi, ndmi, ndwi in zip(
                _timestamps(0, 5, 10),
                [0.30, 0.50, 0.35],
                [0.20, 0.35, 0.25],
                [0.02, 0.12, 0.05],
                [0.18, -0.10, 0.10],
            )
        ]

        level, evidence = _compute_multi_index_confirmation(observations)

        self.assertEqual(level, "strong")
        self.assertIn("Multi-index confirmation=strong", evidence)


if __name__ == "__main__":
    unittest.main()
