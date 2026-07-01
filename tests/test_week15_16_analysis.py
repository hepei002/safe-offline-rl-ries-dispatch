import unittest

import numpy as np
import pandas as pd

from src.experiments.week15_16 import (
    compute_confidence_intervals,
    compute_pairwise_tests,
    make_generalization_scenarios,
    summarize_failure_modes,
)


class Week1516AnalysisTests(unittest.TestCase):
    def test_make_generalization_scenarios_covers_required_families(self):
        scenarios = make_generalization_scenarios()
        families = {scenario["family"] for scenario in scenarios}

        self.assertIn("cross_year", families)
        self.assertIn("cross_season", families)
        self.assertIn("climate_zone", families)
        self.assertIn("compound_stress", families)
        self.assertGreaterEqual(len(scenarios), 8)

    def test_compute_confidence_intervals_reports_95_percent_ci(self):
        frame = pd.DataFrame(
            {
                "method": ["a", "a", "a", "b"],
                "scenario": ["s", "s", "s", "s"],
                "seed": [0, 1, 2, 0],
                "mean_episode_cost_eur": [10.0, 12.0, 14.0, 20.0],
                "mean_episode_hard_safety_cost": [1.0, 2.0, 3.0, 4.0],
                "unsafe_episode_rate": [0.0, 1.0, 1.0, 1.0],
            }
        )

        ci = compute_confidence_intervals(frame, ["mean_episode_cost_eur", "mean_episode_hard_safety_cost"])

        row = ci.loc[(ci["method"] == "a") & (ci["metric"] == "mean_episode_cost_eur")].iloc[0]
        self.assertAlmostEqual(row["mean"], 12.0)
        self.assertGreater(row["ci95_half_width"], 0.0)
        single = ci.loc[(ci["method"] == "b") & (ci["metric"] == "mean_episode_cost_eur")].iloc[0]
        self.assertEqual(single["ci95_half_width"], 0.0)

    def test_compute_pairwise_tests_uses_paired_seeds(self):
        rows = []
        for seed in range(5):
            rows.append({"method": "base", "scenario": "s", "seed": seed, "mean_episode_hard_safety_cost": 10.0 + seed})
            rows.append({"method": "safe", "scenario": "s", "seed": seed, "mean_episode_hard_safety_cost": 1.0})
        frame = pd.DataFrame(rows)

        tests = compute_pairwise_tests(
            frame,
            pairs=[("base", "safe")],
            metric="mean_episode_hard_safety_cost",
        )

        self.assertEqual(len(tests), 1)
        self.assertLess(tests.iloc[0]["mean_delta"], 0.0)
        self.assertLess(tests.iloc[0]["p_value"], 0.05)

    def test_summarize_failure_modes_lists_residual_violations(self):
        frame = pd.DataFrame(
            {
                "method": ["safe", "safe", "base"],
                "scenario": ["a", "b", "a"],
                "mean_episode_hard_safety_cost": [0.0, 2.0, 10.0],
                "unsafe_episode_rate": [0.0, 1.0, 1.0],
                "mean_episode_cost_eur": [100.0, 200.0, 500.0],
            }
        )

        failures = summarize_failure_modes(frame, hard_safety_threshold=1e-6)

        self.assertIn("b", set(failures["scenario"]))
        self.assertIn("base", set(failures["method"]))


if __name__ == "__main__":
    unittest.main()
