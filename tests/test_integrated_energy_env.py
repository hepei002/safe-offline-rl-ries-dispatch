import unittest

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import (
    IntegratedEnergyEnv,
    encode_dispatch_action,
)
from src.optimization.deterministic_dispatch import solve_dispatch_day


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


def cost_config():
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


def synthetic_frame(hours=24):
    index = pd.date_range("2019-03-01", periods=hours, freq="h", tz="UTC")
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


class IntegratedEnergyEnvTests(unittest.TestCase):
    def test_reset_returns_normalized_finite_observation(self):
        env = IntegratedEnergyEnv(synthetic_frame(), tiny_system_config(), cost_config(), episode_hours=24)

        observation, info = env.reset(seed=123)

        self.assertEqual(observation.shape, env.observation_space.shape)
        self.assertTrue(np.isfinite(observation).all())
        self.assertTrue(env.observation_space.contains(observation))
        self.assertEqual(info["utc_timestamp"], "2019-03-01T00:00:00+00:00")

    def test_environment_step_matches_optimizer_for_same_device_action(self):
        frame = synthetic_frame()
        system = tiny_system_config()
        costs = cost_config()
        optimizer = solve_dispatch_day(frame, system, costs)
        env = IntegratedEnergyEnv(frame, system, costs, episode_hours=24)
        env.reset(seed=0)

        action = encode_dispatch_action(optimizer.frame.iloc[0], system)
        _, reward, terminated, truncated, info = env.step(action)
        dispatch = info["dispatch"]

        self.assertFalse(terminated)
        self.assertFalse(truncated)
        self.assertLess(reward, 0.0)
        self.assertAlmostEqual(dispatch["battery_soc_mwh"], optimizer.frame.iloc[0]["battery_soc_mwh"], places=7)
        self.assertAlmostEqual(dispatch["thermal_soc_mwh_th"], optimizer.frame.iloc[0]["thermal_soc_mwh_th"], places=7)
        self.assertAlmostEqual(dispatch["grid_import_mw"], optimizer.frame.iloc[0]["grid_import_mw"], places=7)
        self.assertAlmostEqual(dispatch["electric_balance_residual_mw"], 0.0, places=7)
        self.assertAlmostEqual(dispatch["heat_balance_residual_mw_th"], 0.0, places=7)

    def test_random_action_stress_has_no_nan_and_no_state_leak_after_reset(self):
        env = IntegratedEnergyEnv(synthetic_frame(), tiny_system_config(), cost_config(), episode_hours=24)

        first_observation, _ = env.reset(seed=7)
        for _ in range(24):
            observation, reward, terminated, truncated, info = env.step(env.action_space.sample())
            self.assertTrue(np.isfinite(observation).all())
            self.assertTrue(np.isfinite(reward))
            self.assertFalse(truncated)
            self.assertLess(abs(info["dispatch"]["electric_balance_residual_mw"]), 1e-7)
            self.assertLess(abs(info["dispatch"]["heat_balance_residual_mw_th"]), 1e-7)
            if terminated:
                break

        reset_observation, _ = env.reset(seed=7)
        np.testing.assert_allclose(first_observation, reset_observation)


if __name__ == "__main__":
    unittest.main()
