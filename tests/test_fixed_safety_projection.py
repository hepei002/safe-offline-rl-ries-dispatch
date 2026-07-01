import unittest

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.safety.fixed_projection import (
    FixedProjectionConfig,
    FixedSafetyProjectionLayer,
    evaluate_fixed_projection_layer,
)


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


class FixedSafetyProjectionTests(unittest.TestCase):
    def test_fixed_projection_reports_status_distance_time_and_reduces_hard_safety(self):
        env = IntegratedEnergyEnv(stress_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env.reset(seed=0)
        layer = FixedSafetyProjectionLayer(FixedProjectionConfig(max_iterations=40))
        unsafe_action = np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32)

        result = layer.project(env, unsafe_action)

        self.assertEqual(result.action.shape, unsafe_action.shape)
        self.assertLess(result.projected_hard_safety_cost, result.raw_hard_safety_cost)
        self.assertGreater(result.projection_distance_l2, 0.0)
        self.assertGreaterEqual(result.solve_time_ms, 0.0)
        self.assertIn(result.status, {"optimal", "fallback"})

    def test_fixed_projection_fallback_covers_solver_failure(self):
        env = IntegratedEnergyEnv(stress_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        env.reset(seed=0)
        layer = FixedSafetyProjectionLayer(FixedProjectionConfig(force_solver_failure=True))

        result = layer.project(env, np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32))

        self.assertEqual(result.status, "fallback")
        self.assertLess(result.projected_hard_safety_cost, result.raw_hard_safety_cost)
        self.assertTrue(np.isfinite(result.action).all())
        self.assertTrue((result.action <= 1.0).all())
        self.assertTrue((result.action >= -1.0).all())

    def test_evaluate_fixed_projection_layer_reduces_episode_hard_safety(self):
        env = IntegratedEnergyEnv(stress_frame(), tiny_system_config(), tiny_cost_config(), episode_hours=24)
        layer = FixedSafetyProjectionLayer(FixedProjectionConfig(max_iterations=40))
        actions = [np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32) for _ in range(6)]

        metrics = evaluate_fixed_projection_layer(env, layer, actions)

        self.assertLess(metrics["projected_hard_safety_cost"], metrics["raw_hard_safety_cost"])
        self.assertGreater(metrics["intervention_rate"], 0.0)
        self.assertGreaterEqual(metrics["fallback_rate"], 0.0)
        self.assertGreater(metrics["mean_solve_time_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
