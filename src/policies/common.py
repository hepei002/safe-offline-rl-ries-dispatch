from __future__ import annotations

import numpy as np
import pandas as pd

from src.optimization.deterministic_dispatch import make_import_price


def initial_storage(system_config: dict) -> tuple[float, float]:
    battery = system_config["battery"]
    thermal = system_config["thermal_storage"]
    return (
        float(battery["soc_initial"]) * float(battery["energy_capacity_mwh"]),
        float(thermal["soc_initial"]) * float(thermal["energy_capacity_mwh_th"]),
    )


def storage_bounds(system_config: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    battery = system_config["battery"]
    thermal = system_config["thermal_storage"]
    return (
        (
            float(battery["soc_min"]) * float(battery["energy_capacity_mwh"]),
            float(battery["soc_max"]) * float(battery["energy_capacity_mwh"]),
        ),
        (
            float(thermal["soc_min"]) * float(thermal["energy_capacity_mwh_th"]),
            float(thermal["soc_max"]) * float(thermal["energy_capacity_mwh_th"]),
        ),
    )


def import_price_series(index: pd.DatetimeIndex, policy_config: dict) -> np.ndarray:
    return make_import_price(index, policy_config)


def update_battery_soc(
    previous_soc: float,
    charge_mw: float,
    discharge_mw: float,
    system_config: dict,
) -> float:
    battery = system_config["battery"]
    return (
        (1.0 - float(battery["hourly_self_discharge"])) * previous_soc
        + float(battery["charge_efficiency"]) * charge_mw
        - discharge_mw / float(battery["discharge_efficiency"])
    )


def update_thermal_soc(
    previous_soc: float,
    charge_mw_th: float,
    discharge_mw_th: float,
    system_config: dict,
) -> float:
    thermal = system_config["thermal_storage"]
    return (
        (1.0 - float(thermal["hourly_heat_loss"])) * previous_soc
        + float(thermal["charge_efficiency"]) * charge_mw_th
        - discharge_mw_th / float(thermal["discharge_efficiency"])
    )


def allocate_curtailment(total_curtailment: float, pv_available: float, wind_available: float) -> tuple[float, float]:
    pv_curtailment = min(max(total_curtailment, 0.0), max(pv_available, 0.0))
    wind_curtailment = min(
        max(total_curtailment - pv_curtailment, 0.0),
        max(wind_available, 0.0),
    )
    return pv_curtailment, wind_curtailment


def finalize_dispatch_frame(frame: pd.DataFrame, system_config: dict, policy_config: dict) -> pd.DataFrame:
    result = frame.copy()
    if "electricity_import_price_eur_per_mwh" not in result.columns:
        result["electricity_import_price_eur_per_mwh"] = import_price_series(result.index, policy_config)
    result["chp_heat_mw_th"] = (
        result["chp_electric_mw"] * float(system_config["chp"]["heat_to_power_ratio"])
    )
    result["heat_pump_electric_mw"] = (
        result["heat_pump_heat_mw_th"] / result["cop_ashp_radiator"].clip(lower=1.0)
    )
    result["pv_used_mw"] = result["pv_available_mw"] - result["pv_curtailment_mw"]
    result["wind_used_mw"] = result["wind_available_mw"] - result["wind_curtailment_mw"]
    result["electric_balance_residual_mw"] = (
        result["grid_import_mw"]
        - result["grid_export_mw"]
        + result["chp_electric_mw"]
        + result["pv_used_mw"]
        + result["wind_used_mw"]
        + result["battery_discharge_mw"]
        - result["battery_charge_mw"]
        - result["heat_pump_electric_mw"]
        + result["electric_shedding_mw"]
        - result["electric_load_mw"]
    )
    result["heat_balance_residual_mw_th"] = (
        result["chp_heat_mw_th"]
        + result["heat_pump_heat_mw_th"]
        + result["thermal_discharge_mw_th"]
        - result["thermal_charge_mw_th"]
        + result["heat_shedding_mw_th"]
        - result.get("heat_dump_mw_th", 0.0)
        - result["heat_load_mw_th"]
    )
    return result


def balance_electricity(
    row: pd.Series,
    system_config: dict,
    chp_electric_mw: float,
    heat_pump_heat_mw_th: float,
    battery_charge_mw: float,
    battery_discharge_mw: float,
) -> dict[str, float]:
    hp_electric = heat_pump_heat_mw_th / max(float(row["cop_ashp_radiator"]), 1.0)
    supply_before_grid = (
        float(row["pv_available_mw"])
        + float(row["wind_available_mw"])
        + chp_electric_mw
        + battery_discharge_mw
    )
    demand_before_grid = float(row["electric_load_mw"]) + hp_electric + battery_charge_mw
    net_demand = demand_before_grid - supply_before_grid
    if net_demand >= 0.0:
        grid_import = min(float(system_config["grid"]["import_capacity_mw"]), net_demand)
        return {
            "grid_import_mw": grid_import,
            "grid_export_mw": 0.0,
            "electric_shedding_mw": max(net_demand - grid_import, 0.0),
            "pv_curtailment_mw": 0.0,
            "wind_curtailment_mw": 0.0,
        }

    surplus = -net_demand
    grid_export = min(float(system_config["grid"]["export_capacity_mw"]), surplus)
    pv_curtailment, wind_curtailment = allocate_curtailment(
        surplus - grid_export,
        float(row["pv_available_mw"]),
        float(row["wind_available_mw"]),
    )
    return {
        "grid_import_mw": 0.0,
        "grid_export_mw": grid_export,
        "electric_shedding_mw": 0.0,
        "pv_curtailment_mw": pv_curtailment,
        "wind_curtailment_mw": wind_curtailment,
    }


def policy_cost(dispatch: pd.DataFrame, system_config: dict, policy_config: dict) -> float:
    costs = policy_config["costs"]
    gas_cost = (
        float(costs["natural_gas_eur_per_mwh_lhv"])
        / float(system_config["chp"]["electric_efficiency_lhv"])
    )
    return float(
        (
            dispatch["grid_import_mw"] * dispatch["electricity_import_price_eur_per_mwh"]
            - dispatch["grid_export_mw"] * float(costs["electricity_export_eur_per_mwh"])
            + dispatch["chp_electric_mw"] * gas_cost
            + (dispatch["pv_curtailment_mw"] + dispatch["wind_curtailment_mw"])
            * float(costs["renewable_curtailment_penalty_eur_per_mwh"])
            + dispatch["electric_shedding_mw"]
            * float(system_config["reliability"]["electricity_shedding_penalty_eur_per_mwh"])
            + dispatch["heat_shedding_mw_th"]
            * float(system_config["reliability"]["heat_shedding_penalty_eur_per_mwh_th"])
        ).sum()
    )

