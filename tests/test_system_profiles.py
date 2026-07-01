import unittest

import pandas as pd

from src.data.system_profiles import (
    choose_representative_day,
    scale_series_to_peak,
)


class ScaleSeriesTests(unittest.TestCase):
    def test_scales_series_to_requested_peak(self):
        values = pd.Series([2.0, 4.0, 8.0])

        scaled, factor = scale_series_to_peak(values, target_peak=10.0)

        self.assertAlmostEqual(scaled.max(), 10.0)
        self.assertAlmostEqual(factor, 1.25)


class RepresentativeDayTests(unittest.TestCase):
    def test_selects_actual_day_nearest_daily_feature_median(self):
        index = pd.date_range("2019-01-01", periods=72, freq="h", tz="UTC")
        frame = pd.DataFrame(
            {
                "electric_load_mw": [1.0] * 24 + [5.0] * 24 + [9.0] * 24,
                "heat_load_mw": [2.0] * 24 + [6.0] * 24 + [10.0] * 24,
                "temperature_c": [0.0] * 24 + [5.0] * 24 + [10.0] * 24,
            },
            index=index,
        )

        selected = choose_representative_day(
            frame,
            months=[1],
            feature_columns=[
                "electric_load_mw",
                "heat_load_mw",
                "temperature_c",
            ],
        )

        self.assertEqual(selected, pd.Timestamp("2019-01-02", tz="UTC"))


if __name__ == "__main__":
    unittest.main()
