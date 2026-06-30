from __future__ import annotations

import unittest
from datetime import date, timedelta

from farmtrust_core.seasonal.seasons import SeasonalObservation, daily_curve_from_observations
from outputs.tools.hmm_comparison import compare_detector_and_hmm
from outputs.tools.hmm_phenology import HmmCycle, decode_phenology
from tests.fixtures import phenology_synthetic as ps


def _daily_curve(series: ps.SyntheticSeries):
    obs = [
        SeasonalObservation(
            timestamp=series.timestamps[i],
            ndvi_smoothed=series.clean["ndvi"][i],
            evi_smoothed=series.clean["evi"][i],
            ndmi_smoothed=series.clean["ndmi"][i],
            ndwi_smoothed=series.clean["ndwi"][i],
            valid_fraction=series.valid_fractions[i],
            source_row_count=1,
        )
        for i in range(len(series.timestamps))
    ]
    return daily_curve_from_observations(obs)


class HmmPhenologyTests(unittest.TestCase):
    def test_decode_is_deterministic(self) -> None:
        curve = _daily_curve(ps.double_crop_two_year())
        a = decode_phenology(curve.dates, curve.ndvi)
        b = decode_phenology(curve.dates, curve.ndvi)
        self.assertEqual(a.states, b.states)
        self.assertEqual(
            [(c.sos_date, c.pos_date, c.eos_date) for c in a.cycles],
            [(c.sos_date, c.pos_date, c.eos_date) for c in b.cycles],
        )

    def test_no_high_state_on_flat_fallow(self) -> None:
        curve = _daily_curve(ps.flat_fallow())
        result = decode_phenology(curve.dates, curve.ndvi)
        self.assertFalse(result.has_high_state)
        self.assertEqual(result.cycles, [])

    def test_state_ordering_within_cycle(self) -> None:
        curve = _daily_curve(ps.single_complete_cycle())
        result = decode_phenology(curve.dates, curve.ndvi)
        self.assertIn("RISING", result.states)
        self.assertIn("HIGH", result.states)
        self.assertIn("DECLINING", result.states)
        first_rising = result.states.index("RISING")
        first_high = result.states.index("HIGH")
        last_declining = len(result.states) - 1 - result.states[::-1].index("DECLINING")
        self.assertLess(first_rising, first_high)
        self.assertLess(first_high, last_declining)

    def test_two_cycles_recovered(self) -> None:
        series = ps.two_cycles_with_gap()
        curve = _daily_curve(series)
        result = decode_phenology(curve.dates, curve.ndvi)
        self.assertEqual(len(result.cycles), 2)
        injected = [
            (series.timestamps[0].date() + timedelta(days=int(d))) for d in series.true_peak_days
        ]
        for cycle in result.cycles:
            nearest = min(abs((cycle.pos_date - peak).days) for peak in injected)
            self.assertLessEqual(nearest, 25)

    def test_short_series_runs_deterministically(self) -> None:
        curve = _daily_curve(ps.single_winter_cycle())
        a = decode_phenology(curve.dates, curve.ndvi)
        b = decode_phenology(curve.dates, curve.ndvi)
        self.assertEqual(a.states, b.states)
        self.assertGreaterEqual(len(a.cycles), 1)


class HmmComparisonTests(unittest.TestCase):
    def test_matched_cycles_within_tolerance(self) -> None:
        seasons = [
            {
                "season_id": "season_01",
                "start_date": "2024-02-01",
                "peak_date": "2024-03-15",
                "end_date": "2024-05-01",
                "lifecycle_status": "complete",
            }
        ]
        cycles = [HmmCycle(date(2024, 2, 3), date(2024, 3, 16), date(2024, 5, 5), 0.8, "complete", 92)]
        result = compare_detector_and_hmm(seasons, cycles)
        self.assertEqual(result["matched_count"], 1)
        self.assertTrue(result["agreement_within_tolerance"])
        self.assertEqual(result["matches"][0]["pos_delta_days"], 1)
        self.assertTrue(result["matches"][0]["lifecycle_match"])

    def test_extra_hmm_cycle_breaks_agreement(self) -> None:
        seasons = [
            {
                "season_id": "season_01",
                "start_date": "2024-02-01",
                "peak_date": "2024-03-15",
                "end_date": "2024-05-01",
                "lifecycle_status": "complete",
            }
        ]
        cycles = [
            HmmCycle(date(2024, 2, 3), date(2024, 3, 16), date(2024, 5, 5), 0.8, "complete", 92),
            HmmCycle(date(2024, 8, 1), date(2024, 9, 1), date(2024, 10, 1), 0.7, "complete", 61),
        ]
        result = compare_detector_and_hmm(seasons, cycles)
        self.assertEqual(result["cycle_count_delta"], 1)
        self.assertFalse(result["agreement_within_tolerance"])
        self.assertEqual(result["unmatched_hmm_indices"], [1])


if __name__ == "__main__":
    unittest.main()
