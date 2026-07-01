import unittest

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.experiments.week13_14 import (
    ConstantPolicy,
    build_repeated_risk_scores,
    evaluate_policy_with_safety_mode,
    summarize_main_results,
)
from src.safety.adaptive_layer import AdaptiveSafetyConfig, AdaptiveSafetyLayer
from src.safety.fixed_projection import FixedProjectionConfig, FixedSafetyProjectionLayer


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


def stress_frame(hours=24):
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


class Week1314ExperimentTests(unittest.TestCase):
    def test_evaluate_policy_with_fixed_safety_reduces_hard_safety(self):
        policy = ConstantPolicy(np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32))
        fixed = FixedSafetyProjectionLayer(FixedProjectionConfig(prefer_fast_fallback=True))

        none = evaluate_policy_with_safety_mode(
            policy,
            stress_frame(),
            tiny_system_config(),
            tiny_cost_config(),
            episode_starts=[0],
            episode_hours=6,
            safety_mode="none",
        )
        projected = evaluate_policy_with_safety_mode(
            policy,
            stress_frame(),
            tiny_system_config(),
            tiny_cost_config(),
            episode_starts=[0],
            episode_hours=6,
            safety_mode="fixed",
            fixed_layer=fixed,
        )

        self.assertLess(projected["mean_episode_hard_safety_cost"], none["mean_episode_hard_safety_cost"])
        self.assertGreater(projected["mean_projection_distance_l2"], 0.0)

    def test_evaluate_policy_with_adaptive_safety_reports_mode_rates(self):
        policy = ConstantPolicy(np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32))
        fixed = FixedSafetyProjectionLayer(FixedProjectionConfig(prefer_fast_fallback=True))
        adaptive = AdaptiveSafetyLayer(
            fixed,
            AdaptiveSafetyConfig(low_risk_threshold=3.0, high_risk_threshold=4.0, force_project_if_hard_violation=False),
        )

        metrics = evaluate_policy_with_safety_mode(
            policy,
            stress_frame(),
            tiny_system_config(),
            tiny_cost_config(),
            episode_starts=[0],
            episode_hours=6,
            safety_mode="adaptive",
            adaptive_layer=adaptive,
            risk_scores=build_repeated_risk_scores([3.5], 6),
        )

        self.assertGreater(metrics["partial_projection_rate"] + metrics["full_projection_rate"], 0.0)
        self.assertLess(metrics["mean_episode_hard_safety_cost"], metrics["raw_mean_episode_hard_safety_cost"])

    def test_summarize_main_results_aggregates_seed_statistics(self):
        results = pd.DataFrame(
            {
                "method": ["a", "a", "b"],
                "scenario": ["s", "s", "s"],
                "mean_episode_cost_eur": [10.0, 14.0, 20.0],
                "mean_episode_hard_safety_cost": [1.0, 3.0, 4.0],
                "mean_projection_distance_l2": [0.1, 0.3, 0.0],
                "mean_decision_time_ms": [1.0, 2.0, 0.5],
            }
        )

        summary = summarize_main_results(results)

        row = summary.loc[summary["method"] == "a"].iloc[0]
        self.assertAlmostEqual(row["mean_episode_cost_eur"], 12.0)
        self.assertAlmostEqual(row["std_episode_cost_eur"], np.sqrt(8.0))
        self.assertAlmostEqual(row["mean_hard_safety_cost"], 2.0)


if __name__ == "__main__":
    unittest.main()
