import unittest

import pandas as pd

from src.data.build_joint_dataset import (
    build_joint_dataset,
    build_reference_heat_demand,
    normalize_hourly_utc,
)


class NormalizeHourlyUtcTests(unittest.TestCase):
    def test_averages_duplicates_and_interpolates_one_hour_gap(self):
        frame = pd.DataFrame(
            {
                "utc_timestamp": [
                    "2019-10-27T00:00:00Z",
                    "2019-10-27T00:00:00Z",
                    "2019-10-27T02:00:00Z",
                ],
                "value": [10.0, 14.0, 20.0],
            }
        )

        result, report = normalize_hourly_utc(
            frame,
            start="2019-10-27T00:00:00Z",
            end="2019-10-27T02:00:00Z",
            max_interpolation_gap=1,
            source_name="test",
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result.loc[pd.Timestamp("2019-10-27T00:00:00Z"), "value"], 12.0)
        self.assertEqual(result.loc[pd.Timestamp("2019-10-27T01:00:00Z"), "value"], 16.0)
        self.assertTrue(result.loc[pd.Timestamp("2019-10-27T01:00:00Z"), "imputed_test"])
        self.assertEqual(report["duplicate_rows"], 1)
        self.assertEqual(report["imputed_cells"], 1)

    def test_rejects_gap_longer_than_allowed(self):
        frame = pd.DataFrame(
            {
                "utc_timestamp": [
                    "2019-01-01T00:00:00Z",
                    "2019-01-01T03:00:00Z",
                ],
                "value": [10.0, 20.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "unresolved missing values"):
            normalize_hourly_utc(
                frame,
                start="2019-01-01T00:00:00Z",
                end="2019-01-01T03:00:00Z",
                max_interpolation_gap=1,
                source_name="test",
            )


class ReferenceHeatDemandTests(unittest.TestCase):
    def test_multiplies_profiles_by_annual_twh_weights(self):
        profiles = pd.DataFrame(
            {
                "space_com": [2.0],
                "space_mfh": [3.0],
                "water_sfh": [5.0],
            }
        )
        annual_twh = {
            "space_com": 10.0,
            "space_mfh": 20.0,
            "water_sfh": 30.0,
        }

        result = build_reference_heat_demand(profiles, annual_twh)

        self.assertEqual(result.iloc[0], 230.0)


class RawDataIntegrationTests(unittest.TestCase):
    def test_builds_complete_three_year_joint_table(self):
        result, report = build_joint_dataset(
            raw_root="data/raw",
            start_year=2017,
            end_year=2019,
        )

        self.assertEqual(len(result), 26280)
        self.assertEqual(result["utc_timestamp"].iloc[0], "2017-01-01T00:00:00Z")
        self.assertEqual(result["utc_timestamp"].iloc[-1], "2019-12-31T23:00:00Z")
        self.assertFalse(result.isna().any().any())
        self.assertFalse(result["utc_timestamp"].duplicated().any())
        self.assertEqual(report["when2heat"]["imputed_rows"], 3)
        self.assertGreater(report["heat_reference_annual_twh"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
