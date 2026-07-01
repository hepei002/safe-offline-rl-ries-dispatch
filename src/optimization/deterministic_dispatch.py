from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import linprog

from src.data.system_profiles import choose_representative_day


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "system.yaml"
DISPATCH_CONFIG_PATH = ROOT / "configs" / "deterministic_dispatch.yaml"
JOINT_PATH = ROOT / "data" / "processed" / "exogenous" / "germany_joint_hourly_2017_2019.csv"
OPSD_PATH = ROOT / "data" / "raw" / "opsd" / "time_series_60min_singleindex.csv"


VARIABLES = [
    "grid_import_mw",
    "grid_export_mw",
    "chp_electric_mw",
    "heat_pump_heat_mw_th",
    "battery_charge_mw",
    "battery_discharge_mw",
    "battery_soc_mwh",
    "thermal_charge_mw_th",
    "thermal_discharge_mw_th",
    "thermal_soc_mwh_th",
    "electric_shedding_mw",
    "heat_shedding_mw_th",
    "pv_curtailment_mw",
    "wind_curtailment_mw",
]
VAR = {name: i for i, name in enumerate(VARIABLES)}


@dataclass(frozen=True)
class DispatchResult:
    """Solved deterministic dispatch for one continuous horizon."""

    status: str
    objective_eur: float
    frame: pd.DataFrame


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_dispatch_inputs(
    system_config_path: Path = CONFIG_PATH,
    joint_path: Path = JOINT_PATH,
    opsd_path: Path = OPSD_PATH,
) -> tuple[pd.DataFrame, dict]:
    """Load and scale exogenous hourly data to the configured park size."""

    config = load_yaml(system_config_path)
    frame = pd.read_csv(joint_path)
    frame["utc_timestamp"] = pd.to_datetime(frame["utc_timestamp"], utc=True)
    frame = frame.set_index("utc_timestamp").sort_index()

    frame["electric_load_mw"] = (
        frame[config["data_scaling"]["electricity"]["source_column"]]
        * config["data_scaling"]["electricity"]["scale_factor"]
    )
    frame["heat_load_mw_th"] = (
        frame[config["data_scaling"]["heat"]["source_column"]]
        * config["data_scaling"]["heat"]["scale_factor"]
    )

    renewable_columns = [
        "utc_timestamp",
        "DE_solar_capacity",
        "DE_solar_generation_actual",
        "DE_wind_capacity",
        "DE_wind_generation_actual",
    ]
    renewable = pd.read_csv(opsd_path, usecols=renewable_columns, low_memory=False)
    renewable["utc_timestamp"] = pd.to_datetime(renewable["utc_timestamp"], utc=True)
    renewable = renewable.set_index("utc_timestamp").sort_index().reindex(frame.index)
    capacities = renewable[["DE_solar_capacity", "DE_wind_capacity"]].ffill().bfill()
    frame["pv_available_mw"] = (
        renewable["DE_solar_generation_actual"] / capacities["DE_solar_capacity"]
    ).clip(0.0, 1.0) * config["renewables"]["photovoltaic"]["capacity_mw"]
    frame["wind_available_mw"] = (
        renewable["DE_wind_generation_actual"] / capacities["DE_wind_capacity"]
    ).clip(0.0, 1.0) * config["renewables"]["wind"]["capacity_mw"]

    return frame, config


def choose_typical_days(frame: pd.DataFrame) -> dict[str, pd.Timestamp]:
    """Select winter, summer and shoulder representative days."""

    features = ["electric_load_mw", "heat_load_mw_th", "temperature_c"]
    return {
        "winter": choose_representative_day(
            frame,
            months=[12, 1, 2],
            feature_columns=features,
        ),
        "summer": choose_representative_day(
            frame,
            months=[6, 7, 8],
            feature_columns=features,
        ),
        "shoulder": choose_representative_day(
            frame,
            months=[3, 4, 5, 9, 10, 11],
            feature_columns=features,
        ),
    }


def make_import_price(index: pd.DatetimeIndex, dispatch_config: dict) -> np.ndarray:
    """Deterministic time-of-use price profile used by the baseline LP."""

    price = dispatch_config["costs"]["electricity_import_eur_per_mwh"]
    base = float(price["base"])
    day_adder = float(price["daytime_adder"])
    evening_adder = float(price["evening_peak_adder"])
    night_discount = float(price["night_discount"])

    hours = index.hour.to_numpy()
    values = np.full(len(index), base, dtype=float)
    values += np.where((hours >= 8) & (hours <= 16), day_adder, 0.0)
    values += np.where((hours >= 17) & (hours <= 21), evening_adder, 0.0)
    values += np.where((hours <= 5), night_discount, 0.0)
    return values


def solve_dispatch_day(
    day_frame: pd.DataFrame,
    system_config: dict,
    dispatch_config: dict,
    *,
    initial_battery_soc_mwh: float | None = None,
    initial_thermal_soc_mwh_th: float | None = None,
    terminal_battery_soc_mwh: float | None = None,
    terminal_thermal_soc_mwh_th: float | None = None,
    enforce_terminal_soc: bool = True,
) -> DispatchResult:
    """Solve a deterministic LP dispatch model for one day."""

    horizon = len(day_frame)
    if horizon <= 0:
        raise ValueError("dispatch horizon must contain at least one hourly row")

    n_vars = len(VARIABLES)
    n = horizon * n_vars

    def ix(t: int, name: str) -> int:
        return t * n_vars + VAR[name]

    costs = dispatch_config["costs"]
    if "electricity_import_price_eur_per_mwh" in day_frame.columns:
        import_price = day_frame["electricity_import_price_eur_per_mwh"].to_numpy(dtype=float)
    else:
        import_price = make_import_price(day_frame.index, dispatch_config)
    c = np.zeros(n, dtype=float)
    gas_price = float(costs["natural_gas_eur_per_mwh_lhv"])
    chp_fuel_cost = gas_price / float(system_config["chp"]["electric_efficiency_lhv"])
    export_price = float(costs["electricity_export_eur_per_mwh"])
    curtail_penalty = float(costs["renewable_curtailment_penalty_eur_per_mwh"])
    electric_shed_penalty = float(
        system_config["reliability"]["electricity_shedding_penalty_eur_per_mwh"]
    )
    heat_shed_penalty = float(
        system_config["reliability"]["heat_shedding_penalty_eur_per_mwh_th"]
    )
    for t in range(horizon):
        c[ix(t, "grid_import_mw")] = import_price[t]
        c[ix(t, "grid_export_mw")] = -export_price
        c[ix(t, "chp_electric_mw")] = chp_fuel_cost
        c[ix(t, "electric_shedding_mw")] = electric_shed_penalty
        c[ix(t, "heat_shedding_mw_th")] = heat_shed_penalty
        c[ix(t, "pv_curtailment_mw")] = curtail_penalty
        c[ix(t, "wind_curtailment_mw")] = curtail_penalty

    bounds: list[tuple[float, float]] = []
    for t in range(horizon):
        row = day_frame.iloc[t]
        bounds.extend(
            [
                (0.0, float(system_config["grid"]["import_capacity_mw"])),
                (0.0, float(system_config["grid"]["export_capacity_mw"])),
                (float(system_config["chp"]["minimum_electric_output_mw"]), float(system_config["chp"]["electric_capacity_mw"])),
                (float(system_config["heat_pump"]["minimum_heat_output_mw_th"]), float(system_config["heat_pump"]["heat_capacity_mw_th"])),
                (0.0, float(system_config["battery"]["charge_power_mw"])),
                (0.0, float(system_config["battery"]["discharge_power_mw"])),
                (
                    float(system_config["battery"]["soc_min"]) * float(system_config["battery"]["energy_capacity_mwh"]),
                    float(system_config["battery"]["soc_max"]) * float(system_config["battery"]["energy_capacity_mwh"]),
                ),
                (0.0, float(system_config["thermal_storage"]["charge_power_mw_th"])),
                (0.0, float(system_config["thermal_storage"]["discharge_power_mw_th"])),
                (
                    float(system_config["thermal_storage"]["soc_min"]) * float(system_config["thermal_storage"]["energy_capacity_mwh_th"]),
                    float(system_config["thermal_storage"]["soc_max"]) * float(system_config["thermal_storage"]["energy_capacity_mwh_th"]),
                ),
                (0.0, None),
                (0.0, None),
                (0.0, float(row["pv_available_mw"])),
                (0.0, float(row["wind_available_mw"])),
            ]
        )

    a_eq: list[np.ndarray] = []
    b_eq: list[float] = []
    ratio = float(system_config["chp"]["heat_to_power_ratio"])
    for t in range(horizon):
        row = day_frame.iloc[t]
        electric = np.zeros(n, dtype=float)
        electric[ix(t, "grid_import_mw")] = 1.0
        electric[ix(t, "grid_export_mw")] = -1.0
        electric[ix(t, "chp_electric_mw")] = 1.0
        electric[ix(t, "heat_pump_heat_mw_th")] = -1.0 / float(row["cop_ashp_radiator"])
        electric[ix(t, "battery_charge_mw")] = -1.0
        electric[ix(t, "battery_discharge_mw")] = 1.0
        electric[ix(t, "electric_shedding_mw")] = 1.0
        electric[ix(t, "pv_curtailment_mw")] = -1.0
        electric[ix(t, "wind_curtailment_mw")] = -1.0
        a_eq.append(electric)
        b_eq.append(float(row["electric_load_mw"] - row["pv_available_mw"] - row["wind_available_mw"]))

        heat = np.zeros(n, dtype=float)
        heat[ix(t, "chp_electric_mw")] = ratio
        heat[ix(t, "heat_pump_heat_mw_th")] = 1.0
        heat[ix(t, "thermal_charge_mw_th")] = -1.0
        heat[ix(t, "thermal_discharge_mw_th")] = 1.0
        heat[ix(t, "heat_shedding_mw_th")] = 1.0
        a_eq.append(heat)
        b_eq.append(float(row["heat_load_mw_th"]))

    battery = system_config["battery"]
    battery_initial = (
        float(initial_battery_soc_mwh)
        if initial_battery_soc_mwh is not None
        else float(battery["soc_initial"]) * float(battery["energy_capacity_mwh"])
    )
    for t in range(horizon):
        row = np.zeros(n, dtype=float)
        row[ix(t, "battery_soc_mwh")] = 1.0
        row[ix(t, "battery_charge_mw")] = -float(battery["charge_efficiency"])
        row[ix(t, "battery_discharge_mw")] = 1.0 / float(battery["discharge_efficiency"])
        if t == 0:
            b = battery_initial * (1.0 - float(battery["hourly_self_discharge"]))
        else:
            row[ix(t - 1, "battery_soc_mwh")] = -(1.0 - float(battery["hourly_self_discharge"]))
            b = 0.0
        a_eq.append(row)
        b_eq.append(b)
    if enforce_terminal_soc:
        row = np.zeros(n, dtype=float)
        row[ix(horizon - 1, "battery_soc_mwh")] = 1.0
        a_eq.append(row)
        b_eq.append(
            battery_initial
            if terminal_battery_soc_mwh is None
            else float(terminal_battery_soc_mwh)
        )

    thermal = system_config["thermal_storage"]
    thermal_initial = (
        float(initial_thermal_soc_mwh_th)
        if initial_thermal_soc_mwh_th is not None
        else float(thermal["soc_initial"]) * float(thermal["energy_capacity_mwh_th"])
    )
    for t in range(horizon):
        row = np.zeros(n, dtype=float)
        row[ix(t, "thermal_soc_mwh_th")] = 1.0
        row[ix(t, "thermal_charge_mw_th")] = -float(thermal["charge_efficiency"])
        row[ix(t, "thermal_discharge_mw_th")] = 1.0 / float(thermal["discharge_efficiency"])
        if t == 0:
            b = thermal_initial * (1.0 - float(thermal["hourly_heat_loss"]))
        else:
            row[ix(t - 1, "thermal_soc_mwh_th")] = -(1.0 - float(thermal["hourly_heat_loss"]))
            b = 0.0
        a_eq.append(row)
        b_eq.append(b)
    if enforce_terminal_soc:
        row = np.zeros(n, dtype=float)
        row[ix(horizon - 1, "thermal_soc_mwh_th")] = 1.0
        a_eq.append(row)
        b_eq.append(
            thermal_initial
            if terminal_thermal_soc_mwh_th is None
            else float(terminal_thermal_soc_mwh_th)
        )

    a_ub: list[np.ndarray] = []
    b_ub: list[float] = []
    for t in range(1, horizon):
        row = np.zeros(n, dtype=float)
        row[ix(t, "chp_electric_mw")] = 1.0
        row[ix(t - 1, "chp_electric_mw")] = -1.0
        a_ub.append(row)
        b_ub.append(float(system_config["chp"]["ramp_up_mw_per_hour"]))

        row = np.zeros(n, dtype=float)
        row[ix(t, "chp_electric_mw")] = -1.0
        row[ix(t - 1, "chp_electric_mw")] = 1.0
        a_ub.append(row)
        b_ub.append(float(system_config["chp"]["ramp_down_mw_per_hour"]))

        row = np.zeros(n, dtype=float)
        row[ix(t, "heat_pump_heat_mw_th")] = 1.0
        row[ix(t - 1, "heat_pump_heat_mw_th")] = -1.0
        a_ub.append(row)
        b_ub.append(float(system_config["heat_pump"]["ramp_up_mw_th_per_hour"]))

        row = np.zeros(n, dtype=float)
        row[ix(t, "heat_pump_heat_mw_th")] = -1.0
        row[ix(t - 1, "heat_pump_heat_mw_th")] = 1.0
        a_ub.append(row)
        b_ub.append(float(system_config["heat_pump"]["ramp_down_mw_th_per_hour"]))

    result = linprog(
        c,
        A_ub=np.vstack(a_ub) if a_ub else None,
        b_ub=np.asarray(b_ub) if b_ub else None,
        A_eq=np.vstack(a_eq),
        b_eq=np.asarray(b_eq),
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Dispatch optimization failed: {result.message}")

    values = result.x.reshape((horizon, n_vars))
    dispatch = pd.DataFrame(values, index=day_frame.index, columns=VARIABLES)
    dispatch = pd.concat(
        [
            day_frame[
                [
                    "electric_load_mw",
                    "heat_load_mw_th",
                    "pv_available_mw",
                    "wind_available_mw",
                    "cop_ashp_radiator",
                    "temperature_c",
                ]
            ],
            dispatch,
        ],
        axis=1,
    )
    dispatch["chp_heat_mw_th"] = dispatch["chp_electric_mw"] * ratio
    dispatch["heat_pump_electric_mw"] = dispatch["heat_pump_heat_mw_th"] / dispatch["cop_ashp_radiator"]
    dispatch["pv_used_mw"] = dispatch["pv_available_mw"] - dispatch["pv_curtailment_mw"]
    dispatch["wind_used_mw"] = dispatch["wind_available_mw"] - dispatch["wind_curtailment_mw"]
    dispatch["electricity_import_price_eur_per_mwh"] = import_price
    dispatch["objective_eur"] = result.fun

    return DispatchResult(status="optimal", objective_eur=float(result.fun), frame=dispatch)


def day_slice(frame: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    start = pd.Timestamp(day).tz_convert("UTC") if pd.Timestamp(day).tzinfo else pd.Timestamp(day, tz="UTC")
    return frame.loc[start : start + pd.Timedelta(hours=23)].copy()


def solve_typical_days(
    labels: Iterable[str] | None = None,
    system_config_path: Path = CONFIG_PATH,
    dispatch_config_path: Path = DISPATCH_CONFIG_PATH,
) -> dict[str, DispatchResult]:
    frame, system_config = load_dispatch_inputs(system_config_path=system_config_path)
    dispatch_config = load_yaml(dispatch_config_path)
    typical_days = choose_typical_days(frame)
    selected = typical_days if labels is None else {label: typical_days[label] for label in labels}
    return {
        label: solve_dispatch_day(day_slice(frame, day), system_config, dispatch_config)
        for label, day in selected.items()
    }
