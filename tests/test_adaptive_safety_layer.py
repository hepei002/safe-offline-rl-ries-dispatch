import unittest

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.safety.adaptive_layer import (
    AdaptiveSafetyConfig,
    AdaptiveSafetyLayer,
    evaluate_adaptive_safety_layer,
)
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


def easy_frame(hours=24):
    index = pd.date_range("2019-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "electric_load_mw": np.full(hours, 2.0),
            "heat_load_mw_th": np.full(hours, 2.0),
            "pv_available_mw": np.zeros(hours),
            "wind_available_mw": np.zeros(hours),
            "cop_ashp_radiator": np.full(hours, 2.5),
            "temperature_c": np.full(hours, 5.0),
        },
        index=index,
    )


class AdaptiveSafetyLayerTests(unittest.TestCase):
    def test_low_risk_safe_action_passes_through_without_projection(self):
        env = IntegratedEnergyEnv(easy_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env.reset(seed=0)
        fixed = FixedSafetyProjectionLayer(FixedProjectionConfig(prefer_fast_fallback=True))
        layer = AdaptiveSafetyLayer(fixed, AdaptiveSafetyConfig(low_risk_threshold=1.0, high_risk_threshold=3.0))
        safe_action = np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)

        result = layer.project(env, safe_action, risk_score=0.2)

        self.assertEqual(result.mode, "pass_through")
        self.assertAlmostEqual(result.projection_distance_l2, 0.0)
        self.assertEqual(result.projected_hard_safety_cost, result.raw_hard_safety_cost)

    def test_high_risk_unsafe_action_uses_full_projection(self):
        env = IntegratedEnergyEnv(stress_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env.reset(seed=0)
        fixed = FixedSafetyProjectionLayer(FixedProjectionConfig(prefer_fast_fallback=True))
        layer = AdaptiveSafetyLayer(fixed, AdaptiveSafetyConfig(low_risk_threshold=1.0, high_risk_threshold=3.0))
        unsafe_action = np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32)

        result = layer.project(env, unsafe_action, risk_score=4.0)

        self.assertEqual(result.mode, "full_projection")
        self.assertLess(result.projected_hard_safety_cost, result.raw_hard_safety_cost)
        self.assertGreater(result.projection_distance_l2, 0.0)

    def test_medium_risk_blends_to_lower_distance_than_fixed_when_feasible(self):
        env_adaptive = IntegratedEnergyEnv(stress_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env_fixed = IntegratedEnergyEnv(stress_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env_adaptive.reset(seed=0)
        env_fixed.reset(seed=0)
        fixed = FixedSafetyProjectionLayer(FixedProjectionConfig(prefer_fast_fallback=True))
        layer = AdaptiveSafetyLayer(fixed, AdaptiveSafetyConfig(low_risk_threshold=1.0, high_risk_threshold=5.0, blend_grid_size=9))
        action = np.asarray([-0.2, -0.2, 0.4, 0.4], dtype=np.float32)

        fixed_result = fixed.project(env_fixed, action)
        adaptive_result = layer.project(env_adaptive, action, risk_score=2.0)

        self.assertIn(adaptive_result.mode, {"partial_projection", "full_projection"})
        self.assertLessEqual(adaptive_result.projected_hard_safety_cost, fixed_result.projected_hard_safety_cost + 1e-6)
        self.assertLessEqual(adaptive_result.projection_distance_l2, fixed_result.projection_distance_l2 + 1e-6)

    def test_adaptive_episode_evaluation_reports_lower_correction_than_fixed(self):
        actions = [np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)] * 3
        actions += [np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32)] * 3
        risks = [0.1, 0.2, 0.3, 4.0, 4.2, 4.5]
        env = IntegratedEnergyEnv(easy_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        fixed = FixedSafetyProjectionLayer(FixedProjectionConfig(prefer_fast_fallback=True))
        layer = AdaptiveSafetyLayer(fixed, AdaptiveSafetyConfig(low_risk_threshold=1.0, high_risk_threshold=3.0))

        metrics = evaluate_adaptive_safety_layer(env, layer, actions, risks)

        self.assertGreater(metrics["pass_through_rate"], 0.0)
        self.assertGreater(metrics["full_projection_rate"], 0.0)
        self.assertLess(metrics["projected_hard_safety_cost"], metrics["raw_hard_safety_cost"])
        self.assertLess(metrics["mean_projection_distance_l2"], 2.5)


if __name__ == "__main__":
    unittest.main()
