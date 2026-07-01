import unittest

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.ood.risk import OodRiskScorer, evaluate_ood_scores
from src.safety.costs import split_safety_cost
from src.safety.projection import project_action, evaluate_projected_actions


def tiny_system_config():
    return {
        "system": {"scheduling_horizon_hours": 24},
        "data_scaling": {
            "electricity": {"target_peak_mw": 10.0},
            "heat": {"target_peak_mw_th": 18.0},
        },
        "grid": {"import_capacity_mw": 3.0, "export_capacity_mw": 2.0},
        "renewables": {
            "photovoltaic": {"capacity_mw": 1.0},
            "wind": {"capacity_mw": 1.0},
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


def hard_frame(hours=24):
    index = pd.date_range("2019-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "electric_load_mw": np.full(hours, 4.5),
            "heat_load_mw_th": np.full(hours, 5.0),
            "pv_available_mw": np.zeros(hours),
            "wind_available_mw": np.zeros(hours),
            "cop_ashp_radiator": np.full(hours, 2.0),
            "temperature_c": np.full(hours, 0.0),
        },
        index=index,
    )


class SafetyAndOodTests(unittest.TestCase):
    def test_split_safety_cost_separates_hard_and_soft_components(self):
        dispatch = {
            "electric_shedding_mw": 1.0,
            "heat_shedding_mw_th": 2.0,
            "heat_dump_mw_th": 3.0,
            "pv_curtailment_mw": 4.0,
            "wind_curtailment_mw": 5.0,
        }

        split = split_safety_cost(dispatch)

        self.assertEqual(split["hard_safety_cost"], 3.0)
        self.assertEqual(split["soft_operation_cost"], 12.0)
        self.assertEqual(split["safety_cost"], 15.0)

    def test_environment_info_reports_hard_and_soft_costs(self):
        env = IntegratedEnergyEnv(hard_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env.reset(seed=0)

        _, _, _, _, info = env.step(np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32))

        self.assertGreater(info["hard_safety_cost"], 0.0)
        self.assertGreaterEqual(info["soft_operation_cost"], 0.0)
        self.assertAlmostEqual(
            info["safety_cost"],
            info["hard_safety_cost"] + info["soft_operation_cost"],
        )

    def test_ood_scores_are_higher_for_shifted_samples_and_predict_risk(self):
        rng = np.random.default_rng(1)
        train = rng.normal(0.0, 0.2, size=(80, 4))
        risky = rng.normal(2.0, 0.2, size=(20, 4))
        safe = rng.normal(0.0, 0.2, size=(20, 4))
        samples = np.vstack([safe, risky])
        hard_cost = np.asarray([0.0] * 20 + [1.0] * 20)
        scorer = OodRiskScorer(method="mahalanobis").fit(train)

        scores = scorer.score(samples)
        metrics = evaluate_ood_scores(scores, hard_cost)

        self.assertGreater(scores[20:].mean(), scores[:20].mean())
        self.assertGreater(metrics["auroc"], 0.9)
        self.assertGreater(metrics["spearman_corr"], 0.8)

    def test_ood_risk_labels_ignore_tiny_hard_safety_residuals(self):
        scores = np.asarray([0.1, 0.2, 0.3], dtype=float)
        hard_cost = np.asarray([0.0, 1e-8, 1.0], dtype=float)

        metrics = evaluate_ood_scores(scores, hard_cost)

        self.assertAlmostEqual(metrics["unsafe_rate"], 1.0 / 3.0)
        self.assertGreater(metrics["mean_score_unsafe"], metrics["mean_score_safe"])

    def test_projection_reduces_hard_safety_cost_for_unsafe_action(self):
        env = IntegratedEnergyEnv(hard_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        observation, _ = env.reset(seed=0)
        unsafe_action = np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32)

        safe_action, report = project_action(env, unsafe_action)

        self.assertEqual(safe_action.shape, unsafe_action.shape)
        self.assertLess(report["projected_hard_safety_cost"], report["raw_hard_safety_cost"])
        self.assertGreater(report["projection_distance_l2"], 0.0)
        self.assertTrue(np.isfinite(observation).all())

    def test_projected_action_evaluation_reports_lower_hard_safety(self):
        env = IntegratedEnergyEnv(hard_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        actions = [np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32) for _ in range(4)]

        metrics = evaluate_projected_actions(env, actions)

        self.assertLess(metrics["projected_hard_safety_cost"], metrics["raw_hard_safety_cost"])
        self.assertGreater(metrics["mean_projection_distance_l2"], 0.0)


if __name__ == "__main__":
    unittest.main()
