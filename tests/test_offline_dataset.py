import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.offline.dataset import (
    build_transition_frame,
    generate_offline_datasets,
    make_policy_schedule,
    summarize_dataset_quality,
)
from src.policies.rule_based import run_rule_based_policy


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
            "electric_load_relative_std": 0.02,
            "heat_load_relative_std": 0.02,
            "renewable_relative_std": 0.05,
            "cop_relative_std": 0.02,
            "price_relative_std": 0.03,
        },
        "rule_based": {
            "low_price_eur_per_mwh": 90.0,
            "high_price_eur_per_mwh": 130.0,
            "battery_low_soc_fraction": 0.25,
            "battery_high_soc_fraction": 0.75,
            "chp_heat_priority_fraction": 0.7,
        },
        "safe_random": {
            "seed": 3,
            "chp_min_fraction": 0.0,
            "chp_max_fraction": 1.0,
            "heat_pump_min_fraction": 0.0,
            "heat_pump_max_fraction": 1.0,
        },
        "noisy_mpc": {"seed": 5},
    }


def synthetic_frame(hours=96):
    index = pd.date_range("2019-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "electric_load_mw": 2.0 + 0.2 * np.sin(np.arange(hours) / 24 * 2 * np.pi),
            "heat_load_mw_th": 2.0 + 0.4 * np.cos(np.arange(hours) / 24 * 2 * np.pi),
            "pv_available_mw": np.where((index.hour >= 9) & (index.hour <= 15), 0.8, 0.0),
            "wind_available_mw": np.full(hours, 0.5),
            "cop_ashp_radiator": np.full(hours, 2.5),
            "temperature_c": np.full(hours, 5.0),
        },
        index=index,
    )


class OfflineDatasetTests(unittest.TestCase):
    def test_make_policy_schedule_respects_equal_mixture_counts(self):
        schedule = make_policy_schedule(
            {
                "rolling_mpc": 0.25,
                "noisy_rolling_mpc": 0.25,
                "rule_based": 0.25,
                "safe_random": 0.25,
            },
            episodes=8,
        )

        self.assertEqual(schedule.count("rolling_mpc"), 2)
        self.assertEqual(schedule.count("noisy_rolling_mpc"), 2)
        self.assertEqual(schedule.count("rule_based"), 2)
        self.assertEqual(schedule.count("safe_random"), 2)

    def test_build_transition_frame_contains_observation_action_reward_and_next_observation(self):
        frame = synthetic_frame(hours=24)
        system = tiny_system_config()
        costs = policy_config()
        dispatch = run_rule_based_policy(frame, system, costs)

        transitions = build_transition_frame(
            frame,
            dispatch,
            system,
            costs,
            quality="expert",
            policy_name="rule_based",
            episode_id="expert_0000",
            start_index=0,
        )

        self.assertEqual(len(transitions), 24)
        self.assertIn("obs_electric_load_norm", transitions.columns)
        self.assertIn("action_chp_electric_fraction", transitions.columns)
        self.assertIn("next_obs_electric_load_norm", transitions.columns)
        self.assertIn("reward", transitions.columns)
        self.assertIn("safety_cost", transitions.columns)
        self.assertTrue(transitions["terminal"].iloc[-1])
        self.assertTrue(np.isfinite(transitions.select_dtypes(include=[float, int]).to_numpy()).all())

    def test_generate_offline_datasets_writes_three_quality_parquet_files_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = generate_offline_datasets(
                synthetic_frame(hours=96),
                tiny_system_config(),
                policy_config(),
                {
                    "episode_hours": 24,
                    "qualities": {
                        "expert": {"episodes": 1, "policy_mix": {"perfect_information_lp": 1.0}},
                        "mixed": {"episodes": 1, "policy_mix": {"rule_based": 0.5, "safe_random": 0.5}},
                        "poor": {"episodes": 1, "policy_mix": {"safe_random": 1.0}},
                    },
                },
                output_dir,
            )

            self.assertEqual(set(result.keys()), {"expert", "mixed", "poor"})
            for quality in result:
                self.assertTrue((output_dir / f"{quality}.parquet").exists())
            summary = summarize_dataset_quality(result)
            self.assertEqual(set(summary["quality"]), {"expert", "mixed", "poor"})
            self.assertTrue((summary["transitions"] == 24).all())

    def test_generate_offline_datasets_accepts_nested_source_period_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = generate_offline_datasets(
                synthetic_frame(hours=96),
                tiny_system_config(),
                policy_config(),
                {
                    "source_period": {
                        "episode_hours": 24,
                        "lookahead_hours": 47,
                    },
                    "qualities": {
                        "expert": {"episodes": 1, "policy_mix": {"perfect_information_lp": 1.0}},
                        "mixed": {"episodes": 1, "policy_mix": {"rule_based": 1.0}},
                        "poor": {"episodes": 1, "policy_mix": {"safe_random": 1.0}},
                    },
                },
                output_dir,
            )

            self.assertEqual(set(result.keys()), {"expert", "mixed", "poor"})


if __name__ == "__main__":
    unittest.main()
