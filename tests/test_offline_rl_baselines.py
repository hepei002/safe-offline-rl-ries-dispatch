import unittest

import numpy as np
import pandas as pd

from src.offline_rl.baselines import (
    OfflineTransitions,
    apply_shift_scenario,
    load_transition_arrays,
    train_offline_algorithm,
)
from src.offline_rl.evaluation import evaluate_policy_on_frame, evaluate_rule_policy_on_frame


def tiny_transition_frame(n=64):
    rng = np.random.default_rng(7)
    obs = rng.uniform(0.0, 1.0, size=(n, 10)).astype(np.float32)
    actions = np.tanh(obs[:, :4] * 1.5 - 0.5).astype(np.float32)
    next_obs = np.roll(obs, shift=-1, axis=0)
    reward = -(actions**2).sum(axis=1).astype(np.float32)
    frame = pd.DataFrame(
        {
            **{f"obs_o{i}": obs[:, i] for i in range(obs.shape[1])},
            **{f"action_a{i}": actions[:, i] for i in range(actions.shape[1])},
            **{f"next_obs_o{i}": next_obs[:, i] for i in range(next_obs.shape[1])},
            "reward": reward,
            "terminal": [False] * (n - 1) + [True],
            "safety_cost": np.zeros(n, dtype=np.float32),
        }
    )
    return frame


def tiny_system_config():
    return {
        "system": {"scheduling_horizon_hours": 24},
        "data_scaling": {
            "electricity": {"target_peak_mw": 10.0},
            "heat": {"target_peak_mw_th": 18.0},
        },
        "grid": {"import_capacity_mw": 6.0, "export_capacity_mw": 3.0},
        "renewables": {
            "photovoltaic": {"capacity_mw": 2.0},
            "wind": {"capacity_mw": 2.0},
        },
        "chp": {
            "electric_capacity_mw": 2.0,
            "heat_capacity_mw_th": 2.4,
            "heat_to_power_ratio": 1.2,
            "minimum_electric_output_mw": 0.0,
            "electric_efficiency_lhv": 0.4,
            "ramp_up_mw_per_hour": 2.0,
            "ramp_down_mw_per_hour": 2.0,
        },
        "heat_pump": {
            "heat_capacity_mw_th": 3.0,
            "minimum_heat_output_mw_th": 0.0,
            "ramp_up_mw_th_per_hour": 3.0,
            "ramp_down_mw_th_per_hour": 3.0,
        },
        "battery": {
            "energy_capacity_mwh": 2.0,
            "charge_power_mw": 1.0,
            "discharge_power_mw": 1.0,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "hourly_self_discharge": 0.0,
            "soc_min": 0.1,
            "soc_max": 0.9,
            "soc_initial": 0.5,
            "soc_terminal": 0.5,
        },
        "thermal_storage": {
            "energy_capacity_mwh_th": 3.0,
            "charge_power_mw_th": 1.0,
            "discharge_power_mw_th": 1.0,
            "charge_efficiency": 0.95,
            "discharge_efficiency": 0.95,
            "hourly_heat_loss": 0.0,
            "soc_min": 0.1,
            "soc_max": 0.9,
            "soc_initial": 0.5,
            "soc_terminal": 0.5,
        },
        "reliability": {
            "electricity_shedding_penalty_eur_per_mwh": 10000.0,
            "heat_shedding_penalty_eur_per_mwh_th": 8000.0,
        },
    }


def tiny_cost_config():
    return {
        "costs": {
            "natural_gas_eur_per_mwh_lhv": 55.0,
            "electricity_import_eur_per_mwh": {
                "base": 95.0,
                "daytime_adder": 20.0,
                "evening_peak_adder": 45.0,
                "night_discount": -15.0,
            },
            "electricity_export_eur_per_mwh": 40.0,
            "renewable_curtailment_penalty_eur_per_mwh": 1.0,
        }
    }


def tiny_eval_frame(hours=24):
    index = pd.date_range("2019-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "electric_load_mw": np.full(hours, 2.0),
            "heat_load_mw_th": np.full(hours, 2.0),
            "pv_available_mw": np.where((index.hour >= 9) & (index.hour <= 15), 0.8, 0.0),
            "wind_available_mw": np.full(hours, 0.5),
            "cop_ashp_radiator": np.full(hours, 2.5),
            "temperature_c": np.full(hours, 5.0),
        },
        index=index,
    )


class OfflineRlBaselineTests(unittest.TestCase):
    def test_load_transition_arrays_extracts_standard_columns(self):
        arrays = load_transition_arrays(tiny_transition_frame())

        self.assertIsInstance(arrays, OfflineTransitions)
        self.assertEqual(arrays.observations.shape, (64, 10))
        self.assertEqual(arrays.actions.shape, (64, 4))
        self.assertEqual(arrays.next_observations.shape, (64, 10))
        self.assertEqual(arrays.rewards.shape, (64, 1))

    def test_train_bc_reduces_behavior_cloning_loss(self):
        arrays = load_transition_arrays(tiny_transition_frame())

        result = train_offline_algorithm(
            "bc",
            arrays,
            {"steps": 40, "batch_size": 32, "hidden_dim": 32, "learning_rate": 0.003},
            seed=1,
        )

        self.assertLess(result.learning_curve["actor_loss"][-1], result.learning_curve["actor_loss"][0])
        action = result.policy.predict(np.ones(10, dtype=np.float32) * 0.5)
        self.assertEqual(action.shape, (4,))
        self.assertTrue(np.isfinite(action).all())
        self.assertTrue((action <= 1.0).all())
        self.assertTrue((action >= -1.0).all())

    def test_all_algorithm_interfaces_return_finite_policy_actions(self):
        arrays = load_transition_arrays(tiny_transition_frame())
        for name in ["td3_bc", "cql", "iql"]:
            result = train_offline_algorithm(
                name,
                arrays,
                {"steps": 5, "batch_size": 32, "hidden_dim": 16, "learning_rate": 0.003},
                seed=2,
            )
            action = result.policy.predict(np.ones(10, dtype=np.float32) * 0.5)
            self.assertEqual(action.shape, (4,))
            self.assertTrue(np.isfinite(action).all())

    def test_shift_scenarios_modify_inputs_in_expected_direction(self):
        frame = tiny_eval_frame()
        cost = tiny_cost_config()

        load_frame, load_cost = apply_shift_scenario(frame, cost, {"type": "load_up", "multiplier": 1.2})
        price_frame, price_cost = apply_shift_scenario(frame, cost, {"type": "price_spike", "multiplier": 2.0})
        eff_frame, eff_cost = apply_shift_scenario(frame, cost, {"type": "efficiency_drop", "cop_multiplier": 0.8})

        self.assertGreater(load_frame["electric_load_mw"].mean(), frame["electric_load_mw"].mean())
        self.assertGreater(price_cost["costs"]["electricity_import_eur_per_mwh"]["base"], cost["costs"]["electricity_import_eur_per_mwh"]["base"])
        self.assertLess(eff_frame["cop_ashp_radiator"].mean(), frame["cop_ashp_radiator"].mean())
        self.assertEqual(load_cost["costs"]["natural_gas_eur_per_mwh_lhv"], cost["costs"]["natural_gas_eur_per_mwh_lhv"])

    def test_evaluate_policy_on_frame_returns_cost_and_safety_metrics(self):
        arrays = load_transition_arrays(tiny_transition_frame())
        result = train_offline_algorithm(
            "bc",
            arrays,
            {"steps": 5, "batch_size": 32, "hidden_dim": 16, "learning_rate": 0.003},
            seed=3,
        )

        metrics = evaluate_policy_on_frame(
            result.policy,
            tiny_eval_frame(),
            tiny_system_config(),
            tiny_cost_config(),
            episode_starts=[0],
            episode_hours=24,
        )

        self.assertEqual(metrics["episodes"], 1)
        self.assertGreater(metrics["mean_episode_cost_eur"], 0.0)
        self.assertGreaterEqual(metrics["mean_episode_safety_cost"], 0.0)
        self.assertGreater(metrics["mean_decision_time_ms"], 0.0)

    def test_evaluate_rule_policy_on_frame_returns_same_metric_schema(self):
        metrics = evaluate_rule_policy_on_frame(
            tiny_eval_frame(),
            tiny_system_config(),
            tiny_cost_config(),
            episode_starts=[0],
            episode_hours=24,
        )

        self.assertEqual(metrics["episodes"], 1)
        self.assertGreater(metrics["mean_episode_cost_eur"], 0.0)
        self.assertGreaterEqual(metrics["mean_episode_safety_cost"], 0.0)
        self.assertGreaterEqual(metrics["mean_decision_time_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
