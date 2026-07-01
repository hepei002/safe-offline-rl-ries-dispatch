from __future__ import annotations

import pandas as pd

from src.policies.common import (
    balance_electricity,
    finalize_dispatch_frame,
    import_price_series,
    initial_storage,
    storage_bounds,
    update_battery_soc,
    update_thermal_soc,
)


def run_rule_based_policy(
    frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
) -> pd.DataFrame:
    """Run a heat-priority rule controller with simple price/SOC battery logic."""

    rows: list[dict[str, float]] = []
    battery_soc, thermal_soc = initial_storage(system_config)
    (battery_min, battery_max), (thermal_min, thermal_max) = storage_bounds(system_config)
    prices = import_price_series(frame.index, policy_config)
    rule = policy_config.get("rule_based", {})
    low_price = float(rule.get("low_price_eur_per_mwh", 90.0))
    high_price = float(rule.get("high_price_eur_per_mwh", 130.0))
    battery_low = float(rule.get("battery_low_soc_fraction", 0.25)) * float(system_config["battery"]["energy_capacity_mwh"])
    battery_high = float(rule.get("battery_high_soc_fraction", 0.75)) * float(system_config["battery"]["energy_capacity_mwh"])
    chp_heat_fraction = float(rule.get("chp_heat_priority_fraction", 0.7))

    for t, (_, row) in enumerate(frame.iterrows()):
        heat_load = float(row["heat_load_mw_th"])
        target_chp_heat = min(
            heat_load * chp_heat_fraction,
            float(system_config["chp"]["heat_capacity_mw_th"]),
        )
        chp_electric = min(
            target_chp_heat / float(system_config["chp"]["heat_to_power_ratio"]),
            float(system_config["chp"]["electric_capacity_mw"]),
        )
        chp_heat = chp_electric * float(system_config["chp"]["heat_to_power_ratio"])
        heat_pump_heat = min(
            max(heat_load - chp_heat, 0.0),
            float(system_config["heat_pump"]["heat_capacity_mw_th"]),
        )
        heat_shortage = max(heat_load - chp_heat - heat_pump_heat, 0.0)

        price = prices[t]
        battery_charge = 0.0
        battery_discharge = 0.0
        if price <= low_price and battery_soc < battery_high:
            battery_charge = min(
                float(system_config["battery"]["charge_power_mw"]),
                max((battery_max - battery_soc) / float(system_config["battery"]["charge_efficiency"]), 0.0),
            )
        elif price >= high_price and battery_soc > battery_low:
            battery_discharge = min(
                float(system_config["battery"]["discharge_power_mw"]),
                max((battery_soc - battery_min) * float(system_config["battery"]["discharge_efficiency"]), 0.0),
            )
        battery_soc = update_battery_soc(
            battery_soc,
            battery_charge,
            battery_discharge,
            system_config,
        )
        battery_soc = min(max(battery_soc, battery_min), battery_max)

        thermal_charge = 0.0
        thermal_discharge = 0.0
        thermal_soc = update_thermal_soc(thermal_soc, thermal_charge, thermal_discharge, system_config)
        thermal_soc = min(max(thermal_soc, thermal_min), thermal_max)
        electric = balance_electricity(
            row,
            system_config,
            chp_electric,
            heat_pump_heat,
            battery_charge,
            battery_discharge,
        )
        rows.append(
            {
                **row.to_dict(),
                **electric,
                "chp_electric_mw": chp_electric,
                "heat_pump_heat_mw_th": heat_pump_heat,
                "battery_charge_mw": battery_charge,
                "battery_discharge_mw": battery_discharge,
                "battery_soc_mwh": battery_soc,
                "thermal_charge_mw_th": thermal_charge,
                "thermal_discharge_mw_th": thermal_discharge,
                "thermal_soc_mwh_th": thermal_soc,
                "heat_shedding_mw_th": heat_shortage,
                "heat_dump_mw_th": 0.0,
                "electricity_import_price_eur_per_mwh": price,
            }
        )

    return finalize_dispatch_frame(pd.DataFrame(rows, index=frame.index), system_config, policy_config)

