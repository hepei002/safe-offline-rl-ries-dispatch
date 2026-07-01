import unittest

import numpy as np
import pandas as pd

from src.ood.ensemble import DynamicsEnsembleRiskEstimator, evaluate_ensemble_risk_by_scenario
from src.shift.protocols import (
    ShiftScenario,
    apply_shift_protocol,
    load_shift_protocol,
    summarize_shift_protocol,
)


def tiny_exogenous_frame(hours=48):
    index = pd.date_range("2019-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "electric_load_mw": np.full(hours, 2.0),
            "heat_load_mw_th": np.full(hours, 3.0),
            "pv_available_mw": np.where((index.hour >= 9) & (index.hour <= 15), 1.0, 0.0),
            "wind_available_mw": np.full(hours, 0.8),
            "cop_ashp_radiator": np.full(hours, 2.6),
            "temperature_c": np.full(hours, 5.0),
        },
        index=index,
    )


def tiny_transition_frame(n=120, *, shifted=False):
    rng = np.random.default_rng(11 if not shifted else 12)
    obs = rng.normal(0.0 if not shifted else 1.2, 0.2, size=(n, 10)).astype(np.float32)
    actions = rng.normal(0.0 if not shifted else 0.8, 0.15, size=(n, 4)).astype(np.float32)
    actions = np.clip(actions, -1.0, 1.0)
    dynamics = obs[:, :10] + 0.15 * np.pad(actions, ((0, 0), (0, 6)), mode="constant")
    next_obs = (dynamics + rng.normal(0.0, 0.03, size=(n, 10))).astype(np.float32)
    reward = -np.square(actions).sum(axis=1)
    hard = np.zeros(n, dtype=np.float32)
    if shifted:
        hard[:] = 1.0
    return pd.DataFrame(
        {
            **{f"obs_o{i}": obs[:, i] for i in range(obs.shape[1])},
            **{f"action_a{i}": actions[:, i] for i in range(actions.shape[1])},
            **{f"next_obs_o{i}": next_obs[:, i] for i in range(next_obs.shape[1])},
            "reward": reward,
            "terminal": np.zeros(n, dtype=bool),
            "hard_safety_cost": hard,
            "scenario": "shifted" if shifted else "id",
        }
    )


class ShiftProtocolAndEnsembleOodTests(unittest.TestCase):
    def test_load_shift_protocol_returns_named_scenarios(self):
        protocol = load_shift_protocol()

        names = [scenario.name for scenario in protocol.scenarios]

        self.assertIn("in_distribution", names)
        self.assertIn("load_up_20", names)
        self.assertIn("renewable_down_20", names)
        self.assertTrue(all(isinstance(scenario, ShiftScenario) for scenario in protocol.scenarios))

    def test_apply_shift_protocol_changes_only_declared_variables(self):
        frame = tiny_exogenous_frame()
        scenario = ShiftScenario(
            name="stress",
            family="compound",
            description="test stress",
            parameters={
                "electric_load_multiplier": 1.2,
                "heat_load_multiplier": 1.3,
                "pv_multiplier": 0.7,
                "wind_multiplier": 0.8,
                "cop_multiplier": 0.9,
                "temperature_delta_c": -4.0,
            },
        )

        shifted, metadata = apply_shift_protocol(frame, scenario)

        self.assertAlmostEqual(shifted["electric_load_mw"].mean(), frame["electric_load_mw"].mean() * 1.2)
        self.assertAlmostEqual(shifted["heat_load_mw_th"].mean(), frame["heat_load_mw_th"].mean() * 1.3)
        self.assertLess(shifted["pv_available_mw"].mean(), frame["pv_available_mw"].mean())
        self.assertLess(shifted["wind_available_mw"].mean(), frame["wind_available_mw"].mean())
        self.assertLess(shifted["cop_ashp_radiator"].mean(), frame["cop_ashp_radiator"].mean())
        self.assertAlmostEqual(shifted["temperature_c"].mean(), frame["temperature_c"].mean() - 4.0)
        self.assertEqual(metadata["scenario"], "stress")
        self.assertGreater(metadata["mean_absolute_relative_change"], 0.0)

    def test_summarize_shift_protocol_reports_intensity(self):
        frame = tiny_exogenous_frame()
        scenarios = [
            ShiftScenario("in_distribution", "baseline", "no shift", {}),
            ShiftScenario("load_up_20", "load", "load increase", {"electric_load_multiplier": 1.2, "heat_load_multiplier": 1.2}),
        ]

        summary = summarize_shift_protocol(frame, scenarios)

        self.assertEqual(set(summary["scenario"]), {"in_distribution", "load_up_20"})
        self.assertEqual(float(summary.loc[summary["scenario"] == "in_distribution", "mean_absolute_relative_change"].iloc[0]), 0.0)
        self.assertGreater(float(summary.loc[summary["scenario"] == "load_up_20", "mean_absolute_relative_change"].iloc[0]), 0.0)

    def test_dynamics_ensemble_scores_shifted_transitions_as_riskier(self):
        id_frame = tiny_transition_frame(120, shifted=False)
        shifted_frame = tiny_transition_frame(60, shifted=True)
        estimator = DynamicsEnsembleRiskEstimator(n_models=4, hidden_dim=16, epochs=15, seed=5)

        estimator.fit(id_frame)
        id_scores = estimator.score(id_frame)
        shifted_scores = estimator.score(shifted_frame)

        self.assertEqual(id_scores.shape, (120,))
        self.assertGreater(shifted_scores.mean(), id_scores.mean())

    def test_evaluate_ensemble_risk_by_scenario_returns_auc_metrics(self):
        frame = pd.concat([tiny_transition_frame(120, shifted=False), tiny_transition_frame(60, shifted=True)], ignore_index=True)
        estimator = DynamicsEnsembleRiskEstimator(n_models=4, hidden_dim=16, epochs=15, seed=6)
        estimator.fit(frame.loc[frame["scenario"] == "id"])

        scored, summary = evaluate_ensemble_risk_by_scenario(estimator, frame, scenario_column="scenario")

        self.assertIn("ensemble_ood_score", scored.columns)
        self.assertIn("auroc", summary.columns)
        self.assertGreater(float(summary.loc[summary["scenario"] == "shifted", "mean_ood_score"].iloc[0]), float(summary.loc[summary["scenario"] == "id", "mean_ood_score"].iloc[0]))
        self.assertGreaterEqual(float(summary["auroc"].max()), 0.9)


if __name__ == "__main__":
    unittest.main()
