import unittest

import numpy as np
import pandas as pd

from src.policies.forecasts import apply_forecast_error
from src.policies.evaluation import dataframe_to_markdown_table, summarize_policy
from src.policies.random_policy import run_safe_random_policy
from src.policies.rolling_mpc import run_rolling_mpc
from src.policies.rule_based import run_rule_based_policy


def tiny_system_config():
    return {
        "system": {"scheduling_horizon_hours": 24},
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


def policy_config():
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
        },
        "forecast_error": {
            "electric_load_relative_std": 0.05,
            "heat_load_relative_std": 0.05,
            "renewable_relative_std": 0.10,
            "cop_relative_std": 0.03,
            "price_relative_std": 0.05,
        },
        "rule_based": {
            "low_price_eur_per_mwh": 90.0,
            "high_price_eur_per_mwh": 130.0,
            "battery_low_soc_fraction": 0.25,
            "battery_high_soc_fraction": 0.75,
            "chp_heat_priority_fraction": 0.7,
        },
        "safe_random": {
            "seed": 7,
            "chp_min_fraction": 0.0,
            "chp_max_fraction": 1.0,
            "heat_pump_min_fraction": 0.0,
            "heat_pump_max_fraction": 1.0,
        },
    }


def synthetic_frame(hours=24):
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


class ForecastErrorTests(unittest.TestCase):
    def test_forecast_error_is_seeded_and_keeps_physical_lower_bounds(self):
        frame = synthetic_frame()

        first = apply_forecast_error(frame, policy_config(), seed=123)
        second = apply_forecast_error(frame, policy_config(), seed=123)

        pd.testing.assert_frame_equal(first, second)
        self.assertTrue((first["electric_load_mw"] >= 0.0).all())
        self.assertTrue((first["heat_load_mw_th"] >= 0.0).all())
        self.assertTrue((first["pv_available_mw"] >= 0.0).all())
        self.assertTrue((first["wind_available_mw"] >= 0.0).all())
        self.assertTrue((first["cop_ashp_radiator"] >= 1.0).all())


class BehaviorPolicyTests(unittest.TestCase):
    def assert_balanced(self, dispatch):
        self.assertLess(dispatch["electric_balance_residual_mw"].abs().max(), 1e-7)
        self.assertLess(dispatch["heat_balance_residual_mw_th"].abs().max(), 1e-7)

    def test_rule_policy_returns_balanced_hourly_dispatch(self):
        dispatch = run_rule_based_policy(synthetic_frame(), tiny_system_config(), policy_config())

        self.assertEqual(len(dispatch), 24)
        self.assert_balanced(dispatch)

    def test_safe_random_policy_returns_balanced_hourly_dispatch(self):
        dispatch = run_safe_random_policy(synthetic_frame(), tiny_system_config(), policy_config(), seed=11)

        self.assertEqual(len(dispatch), 24)
        self.assert_balanced(dispatch)

    def test_rolling_mpc_executes_one_action_per_evaluation_hour(self):
        frame = synthetic_frame(hours=30)

        dispatch = run_rolling_mpc(
            frame,
            tiny_system_config(),
            policy_config(),
            evaluation_hours=6,
            noisy=False,
        )

        self.assertEqual(len(dispatch), 6)
        self.assert_balanced(dispatch)


class PolicyEvaluationTests(unittest.TestCase):
    def test_summarize_policy_reports_cost_safety_and_action_coverage(self):
        dispatch = run_rule_based_policy(synthetic_frame(), tiny_system_config(), policy_config())

        summary = summarize_policy("rule", dispatch, tiny_system_config(), policy_config())

        self.assertEqual(summary["policy"], "rule")
        self.assertEqual(summary["hours"], 24)
        self.assertGreater(summary["total_cost_eur"], 0.0)
        self.assertEqual(summary["electric_shedding_mwh"], 0.0)
        self.assertEqual(summary["heat_shedding_mwh_th"], 0.0)
        self.assertGreaterEqual(summary["action_coverage_score"], 0.0)

    def test_dataframe_to_markdown_table_does_not_require_optional_tabulate(self):
        table = dataframe_to_markdown_table(pd.DataFrame([{"policy": "rule", "hours": 24}]))

        self.assertIn("| policy | hours |", table)
        self.assertIn("| rule | 24 |", table)


if __name__ == "__main__":
    unittest.main()
