from __future__ import annotations

import time

import pandas as pd

from src.optimization.deterministic_dispatch import solve_dispatch_day
from src.policies.common import finalize_dispatch_frame, initial_storage
from src.policies.forecasts import apply_forecast_error


def _rebalance_first_action(
    planned: pd.Series,
    actual: pd.Series,
    system_config: dict,
    policy_config: dict,
) -> pd.DataFrame:
    row = planned.copy()
    for column in [
        "electric_load_mw",
        "heat_load_mw_th",
        "pv_available_mw",
        "wind_available_mw",
        "cop_ashp_radiator",
        "temperature_c",
    ]:
        row[column] = actual[column]

    hp_electric = row["heat_pump_heat_mw_th"] / max(float(row["cop_ashp_radiator"]), 1.0)
    supply = (
        row["chp_electric_mw"]
        + row["battery_discharge_mw"]
        + row["pv_available_mw"]
        + row["wind_available_mw"]
    )
    demand = row["electric_load_mw"] + hp_electric + row["battery_charge_mw"]
    net_demand = demand - supply
    row["pv_curtailment_mw"] = 0.0
    row["wind_curtailment_mw"] = 0.0
    row["electric_shedding_mw"] = 0.0
    if net_demand >= 0.0:
        row["grid_import_mw"] = min(float(system_config["grid"]["import_capacity_mw"]), net_demand)
        row["grid_export_mw"] = 0.0
        row["electric_shedding_mw"] = max(net_demand - row["grid_import_mw"], 0.0)
    else:
        surplus = -net_demand
        row["grid_import_mw"] = 0.0
        row["grid_export_mw"] = min(float(system_config["grid"]["export_capacity_mw"]), surplus)
        curtail = max(surplus - row["grid_export_mw"], 0.0)
        row["pv_curtailment_mw"] = min(curtail, row["pv_available_mw"])
        row["wind_curtailment_mw"] = min(curtail - row["pv_curtailment_mw"], row["wind_available_mw"])

    heat_supply = (
        row["chp_electric_mw"] * float(system_config["chp"]["heat_to_power_ratio"])
        + row["heat_pump_heat_mw_th"]
        + row["thermal_discharge_mw_th"]
        - row["thermal_charge_mw_th"]
    )
    heat_gap = row["heat_load_mw_th"] - heat_supply
    row["heat_shedding_mw_th"] = max(heat_gap, 0.0)
    row["heat_dump_mw_th"] = max(-heat_gap, 0.0)
    return finalize_dispatch_frame(pd.DataFrame([row], index=[actual.name]), system_config, policy_config)


def run_rolling_mpc(
    frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    *,
    evaluation_hours: int,
    noisy: bool = False,
    seed: int = 0,
) -> pd.DataFrame:
    """Run 24 h look-ahead MPC and execute only the first action each hour."""

    horizon = int(system_config["system"]["scheduling_horizon_hours"])
    if len(frame) < evaluation_hours + horizon - 1:
        raise ValueError("frame must include evaluation hours plus 23 look-ahead hours")

    battery_soc, thermal_soc = initial_storage(system_config)
    terminal_battery_soc, terminal_thermal_soc = initial_storage(system_config)
    executed: list[pd.DataFrame] = []
    solve_times: list[float] = []
    for t in range(evaluation_hours):
        lookahead = frame.iloc[t : t + horizon].copy()
        if noisy:
            lookahead = apply_forecast_error(lookahead, policy_config, seed=seed + t)
        start = time.perf_counter()
        result = solve_dispatch_day(
            lookahead,
            system_config,
            policy_config,
            initial_battery_soc_mwh=battery_soc,
            initial_thermal_soc_mwh_th=thermal_soc,
            terminal_battery_soc_mwh=terminal_battery_soc,
            terminal_thermal_soc_mwh_th=terminal_thermal_soc,
        )
        solve_times.append(time.perf_counter() - start)
        first = _rebalance_first_action(
            result.frame.iloc[0],
            frame.iloc[t],
            system_config,
            policy_config,
        )
        first["mpc_solve_time_s"] = solve_times[-1]
        executed.append(first)
        battery_soc = float(first["battery_soc_mwh"].iloc[0])
        thermal_soc = float(first["thermal_soc_mwh_th"].iloc[0])

    dispatch = pd.concat(executed).sort_index()
    dispatch["objective_eur"] = 0.0
    return dispatch
