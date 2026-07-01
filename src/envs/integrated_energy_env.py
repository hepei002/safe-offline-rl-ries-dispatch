from __future__ import annotations

from pathlib import Path
from typing import Any

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import yaml

from src.optimization.deterministic_dispatch import (
    CONFIG_PATH,
    DISPATCH_CONFIG_PATH,
    load_dispatch_inputs,
)
from src.policies.common import (
    balance_electricity,
    finalize_dispatch_frame,
    import_price_series,
    initial_storage,
    policy_cost,
    storage_bounds,
    update_battery_soc,
    update_thermal_soc,
)
from src.safety.costs import split_safety_cost


ACTION_NAMES = [
    "chp_electric_fraction",
    "heat_pump_heat_fraction",
    "battery_power_fraction",
    "thermal_power_fraction",
]

OBSERVATION_NAMES = [
    "electric_load_norm",
    "heat_load_norm",
    "pv_available_norm",
    "wind_available_norm",
    "cop_norm",
    "import_price_norm",
    "battery_soc_norm",
    "thermal_soc_norm",
    "hour_sin",
    "hour_cos",
]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def encode_dispatch_action(dispatch_row: pd.Series, system_config: dict) -> np.ndarray:
    """Map a physical dispatch row into the normalized environment action."""

    chp = 2.0 * float(dispatch_row["chp_electric_mw"]) / float(system_config["chp"]["electric_capacity_mw"]) - 1.0
    hp = 2.0 * float(dispatch_row["heat_pump_heat_mw_th"]) / float(system_config["heat_pump"]["heat_capacity_mw_th"]) - 1.0

    battery_charge = float(dispatch_row.get("battery_charge_mw", 0.0))
    battery_discharge = float(dispatch_row.get("battery_discharge_mw", 0.0))
    if battery_charge >= battery_discharge:
        battery = battery_charge / float(system_config["battery"]["charge_power_mw"])
    else:
        battery = -battery_discharge / float(system_config["battery"]["discharge_power_mw"])

    thermal_charge = float(dispatch_row.get("thermal_charge_mw_th", 0.0))
    thermal_discharge = float(dispatch_row.get("thermal_discharge_mw_th", 0.0))
    if thermal_charge >= thermal_discharge:
        thermal = thermal_charge / float(system_config["thermal_storage"]["charge_power_mw_th"])
    else:
        thermal = -thermal_discharge / float(system_config["thermal_storage"]["discharge_power_mw_th"])

    return np.clip(np.asarray([chp, hp, battery, thermal], dtype=np.float32), -1.0, 1.0)


class IntegratedEnergyEnv(gym.Env):
    """A Gymnasium environment for one-zone electricity-heat dispatch.

    The agent chooses CHP, heat-pump, battery and thermal-storage set-points.
    Grid import/export, curtailment, heat dump and emergency shedding are then
    computed as deterministic balancing variables.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        frame: pd.DataFrame,
        system_config: dict,
        cost_config: dict,
        *,
        episode_hours: int = 24,
        start_index: int = 0,
    ) -> None:
        super().__init__()
        if episode_hours <= 0:
            raise ValueError("episode_hours must be positive")
        if len(frame) < start_index + episode_hours:
            raise ValueError("frame does not contain enough rows for the requested episode")
        self.frame = frame.sort_index().copy()
        self.system_config = system_config
        self.cost_config = cost_config
        self.episode_hours = int(episode_hours)
        self.start_index = int(start_index)
        self.current_step = 0
        self.battery_soc_mwh = 0.0
        self.thermal_soc_mwh_th = 0.0
        self.import_prices = import_price_series(self.frame.index, cost_config)

        self.action_space = spaces.Box(
            low=np.full(len(ACTION_NAMES), -1.0, dtype=np.float32),
            high=np.full(len(ACTION_NAMES), 1.0, dtype=np.float32),
            dtype=np.float32,
        )
        self.observation_space = spaces.Box(
            low=np.asarray([0, 0, 0, 0, 0, 0, 0, 0, -1, -1], dtype=np.float32),
            high=np.asarray([2, 2, 2, 2, 2, 2, 1, 1, 1, 1], dtype=np.float32),
            dtype=np.float32,
        )

    @classmethod
    def from_config(
        cls,
        *,
        system_config_path: Path = CONFIG_PATH,
        cost_config_path: Path = DISPATCH_CONFIG_PATH,
        episode_hours: int = 24,
        start_index: int = 0,
    ) -> "IntegratedEnergyEnv":
        frame, system_config = load_dispatch_inputs(system_config_path=system_config_path)
        cost_config = load_yaml(cost_config_path)
        return cls(
            frame,
            system_config,
            cost_config,
            episode_hours=episode_hours,
            start_index=start_index,
        )

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        if options and "start_index" in options:
            start_index = int(options["start_index"])
            if len(self.frame) < start_index + self.episode_hours:
                raise ValueError("frame does not contain enough rows for requested start_index")
            self.start_index = start_index
        self.current_step = 0
        self.battery_soc_mwh, self.thermal_soc_mwh_th = initial_storage(self.system_config)
        return self._observation(), self._info_base()

    def step(
        self,
        action: np.ndarray,
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.current_step >= self.episode_hours:
            raise RuntimeError("episode is done; call reset() before step()")

        row = self._current_row()
        action = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        dispatch = self._dispatch_from_action(row, action)
        reward = -policy_cost(dispatch, self.system_config, self.cost_config)
        info = self._info_base()

        self.battery_soc_mwh = float(dispatch["battery_soc_mwh"].iloc[0])
        self.thermal_soc_mwh_th = float(dispatch["thermal_soc_mwh_th"].iloc[0])
        self.current_step += 1
        terminated = self.current_step >= self.episode_hours
        truncated = False
        observation = self._terminal_observation() if terminated else self._observation()
        info["dispatch"] = {
            key: float(value)
            for key, value in dispatch.iloc[0].items()
            if isinstance(value, (int, float, np.integer, np.floating, bool, np.bool_))
        }
        split = split_safety_cost(info["dispatch"])
        info.update(split)
        return observation, float(reward), terminated, truncated, info

    def _dispatch_from_action(self, row: pd.Series, action: np.ndarray) -> pd.DataFrame:
        chp_electric = (float(action[0]) + 1.0) * 0.5 * float(self.system_config["chp"]["electric_capacity_mw"])
        heat_pump_heat = (float(action[1]) + 1.0) * 0.5 * float(self.system_config["heat_pump"]["heat_capacity_mw_th"])

        battery_charge, battery_discharge = self._signed_storage_power(
            float(action[2]),
            float(self.system_config["battery"]["charge_power_mw"]),
            float(self.system_config["battery"]["discharge_power_mw"]),
        )
        thermal_charge, thermal_discharge = self._signed_storage_power(
            float(action[3]),
            float(self.system_config["thermal_storage"]["charge_power_mw_th"]),
            float(self.system_config["thermal_storage"]["discharge_power_mw_th"]),
        )

        (battery_min, battery_max), (thermal_min, thermal_max) = storage_bounds(self.system_config)
        battery_charge = min(
            battery_charge,
            max((battery_max - self.battery_soc_mwh) / float(self.system_config["battery"]["charge_efficiency"]), 0.0),
        )
        battery_discharge = min(
            battery_discharge,
            max((self.battery_soc_mwh - battery_min) * float(self.system_config["battery"]["discharge_efficiency"]), 0.0),
        )
        thermal_charge = min(
            thermal_charge,
            max((thermal_max - self.thermal_soc_mwh_th) / float(self.system_config["thermal_storage"]["charge_efficiency"]), 0.0),
        )
        thermal_discharge = min(
            thermal_discharge,
            max((self.thermal_soc_mwh_th - thermal_min) * float(self.system_config["thermal_storage"]["discharge_efficiency"]), 0.0),
        )

        next_battery_soc = update_battery_soc(
            self.battery_soc_mwh,
            battery_charge,
            battery_discharge,
            self.system_config,
        )
        next_thermal_soc = update_thermal_soc(
            self.thermal_soc_mwh_th,
            thermal_charge,
            thermal_discharge,
            self.system_config,
        )

        heat_supply = (
            chp_electric * float(self.system_config["chp"]["heat_to_power_ratio"])
            + heat_pump_heat
            + thermal_discharge
            - thermal_charge
        )
        heat_gap = float(row["heat_load_mw_th"]) - heat_supply
        heat_shedding = max(heat_gap, 0.0)
        heat_dump = max(-heat_gap, 0.0)
        electric = balance_electricity(
            row,
            self.system_config,
            chp_electric,
            heat_pump_heat,
            battery_charge,
            battery_discharge,
        )
        payload = {
            **row.to_dict(),
            **electric,
            "chp_electric_mw": chp_electric,
            "heat_pump_heat_mw_th": heat_pump_heat,
            "battery_charge_mw": battery_charge,
            "battery_discharge_mw": battery_discharge,
            "battery_soc_mwh": next_battery_soc,
            "thermal_charge_mw_th": thermal_charge,
            "thermal_discharge_mw_th": thermal_discharge,
            "thermal_soc_mwh_th": next_thermal_soc,
            "heat_shedding_mw_th": heat_shedding,
            "heat_dump_mw_th": heat_dump,
            "electricity_import_price_eur_per_mwh": float(self.import_prices[self._absolute_index()]),
        }
        return finalize_dispatch_frame(
            pd.DataFrame([payload], index=[row.name]),
            self.system_config,
            self.cost_config,
        )

    @staticmethod
    def _signed_storage_power(action_value: float, charge_power: float, discharge_power: float) -> tuple[float, float]:
        if action_value >= 0.0:
            return action_value * charge_power, 0.0
        return 0.0, -action_value * discharge_power

    def _absolute_index(self) -> int:
        return self.start_index + self.current_step

    def _current_row(self) -> pd.Series:
        return self.frame.iloc[self._absolute_index()]

    def _observation(self) -> np.ndarray:
        row = self._current_row()
        hour = row.name.hour
        battery = self.system_config["battery"]
        thermal = self.system_config["thermal_storage"]
        observation = np.asarray(
            [
                float(row["electric_load_mw"]) / float(self.system_config["data_scaling"]["electricity"]["target_peak_mw"]),
                float(row["heat_load_mw_th"]) / float(self.system_config["data_scaling"]["heat"]["target_peak_mw_th"]),
                float(row["pv_available_mw"]) / max(float(self.system_config["renewables"]["photovoltaic"]["capacity_mw"]), 1e-9),
                float(row["wind_available_mw"]) / max(float(self.system_config["renewables"]["wind"]["capacity_mw"]), 1e-9),
                float(row["cop_ashp_radiator"]) / 5.0,
                float(self.import_prices[self._absolute_index()]) / 200.0,
                self.battery_soc_mwh / float(battery["energy_capacity_mwh"]),
                self.thermal_soc_mwh_th / float(thermal["energy_capacity_mwh_th"]),
                np.sin(2.0 * np.pi * hour / 24.0),
                np.cos(2.0 * np.pi * hour / 24.0),
            ],
            dtype=np.float32,
        )
        return np.clip(observation, self.observation_space.low, self.observation_space.high).astype(np.float32)

    def _terminal_observation(self) -> np.ndarray:
        return np.zeros(self.observation_space.shape, dtype=np.float32)

    def _info_base(self) -> dict[str, Any]:
        index = min(self._absolute_index(), len(self.frame) - 1)
        return {
            "step": self.current_step,
            "utc_timestamp": self.frame.index[index].isoformat(),
            "observation_names": OBSERVATION_NAMES,
            "action_names": ACTION_NAMES,
        }
