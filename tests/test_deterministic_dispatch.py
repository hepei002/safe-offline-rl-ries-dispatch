import unittest

import numpy as np
import pandas as pd

from src.optimization.deterministic_dispatch import solve_dispatch_day


def tiny_system_config():
    return {
        "system": {"scheduling_horizon_hours": 24},
        "grid": {"import_capacity_mw": 5.0, "export_capacity_mw": 2.0},
        "chp": {
            "electric_capacity_mw": 2.0,
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


def dispatch_cost_config():
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


class DeterministicDispatchTests(unittest.TestCase):
    def test_solves_balanced_24_hour_lp_without_shedding(self):
        index = pd.date_range("2019-01-01", periods=24, freq="h", tz="UTC")
        frame = pd.DataFrame(
            {
                "electric_load_mw": np.full(24, 2.0),
                "heat_load_mw_th": np.full(24, 2.0),
                "pv_available_mw": np.zeros(24),
                "wind_available_mw": np.full(24, 0.5),
                "cop_ashp_radiator": np.full(24, 2.5),
                "temperature_c": np.full(24, 5.0),
            },
            index=index,
        )

        result = solve_dispatch_day(frame, tiny_system_config(), dispatch_cost_config())

        self.assertEqual(result.status, "optimal")
        self.assertLess(result.frame["electric_shedding_mw"].sum(), 1e-7)
        self.assertLess(result.frame["heat_shedding_mw_th"].sum(), 1e-7)
        self.assertTrue((result.frame["battery_soc_mwh"] >= 0.2 - 1e-7).all())
        self.assertTrue((result.frame["thermal_soc_mwh_th"] >= 0.3 - 1e-7).all())

    def test_solves_multi_day_perfect_information_horizon(self):
        index = pd.date_range("2019-01-01", periods=48, freq="h", tz="UTC")
        frame = pd.DataFrame(
            {
                "electric_load_mw": np.full(48, 2.0),
                "heat_load_mw_th": np.full(48, 2.0),
                "pv_available_mw": np.zeros(48),
                "wind_available_mw": np.full(48, 0.5),
                "cop_ashp_radiator": np.full(48, 2.5),
                "temperature_c": np.full(48, 5.0),
            },
            index=index,
        )

        result = solve_dispatch_day(frame, tiny_system_config(), dispatch_cost_config())

        self.assertEqual(result.status, "optimal")
        self.assertEqual(len(result.frame), 48)

    def test_can_relax_terminal_storage_for_benchmark_upper_bound(self):
        index = pd.date_range("2019-01-01", periods=24, freq="h", tz="UTC")
        frame = pd.DataFrame(
            {
                "electric_load_mw": np.full(24, 2.0),
                "heat_load_mw_th": np.full(24, 2.0),
                "pv_available_mw": np.zeros(24),
                "wind_available_mw": np.full(24, 0.5),
                "cop_ashp_radiator": np.full(24, 2.5),
                "temperature_c": np.full(24, 5.0),
            },
            index=index,
        )

        result = solve_dispatch_day(
            frame,
            tiny_system_config(),
            dispatch_cost_config(),
            enforce_terminal_soc=False,
        )

        self.assertEqual(result.status, "optimal")
        self.assertEqual(len(result.frame), 24)


if __name__ == "__main__":
    unittest.main()
