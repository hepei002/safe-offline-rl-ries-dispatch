from __future__ import annotations

import numpy as np
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


def run_safe_random_policy(
    frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    *,
    seed: int | None = None,
) -> pd.DataFrame:
    """Sample bounded actions and use grid/shedding/dump variables as safety fallback."""

    rng = np.random.default_rng(policy_config.get("safe_random", {}).get("seed", 0) if seed is None else seed)
    rows: list[dict[str, float]] = []
    battery_soc, thermal_soc = initial_storage(system_config)
    (battery_min, battery_max), (thermal_min, thermal_max) = storage_bounds(system_config)
    prices = import_price_series(frame.index, policy_config)
    random_cfg = policy_config.get("safe_random", {})
    chp_min = float(random_cfg.get("chp_min_fraction", 0.0))
    chp_max = float(random_cfg.get("chp_max_fraction", 1.0))
    hp_min = float(random_cfg.get("heat_pump_min_fraction", 0.0))
    hp_max = float(random_cfg.get("heat_pump_max_fraction", 1.0))

    for t, (_, row) in enumerate(frame.iterrows()):
        chp_electric = rng.uniform(chp_min, chp_max) * float(system_config["chp"]["electric_capacity_mw"])
        heat_pump_heat = rng.uniform(hp_min, hp_max) * float(system_config["heat_pump"]["heat_capacity_mw_th"])

        battery_charge = rng.uniform(0.0, float(system_config["battery"]["charge_power_mw"]))
        battery_discharge = rng.uniform(0.0, float(system_config["battery"]["discharge_power_mw"]))
        if battery_charge > 0.0 and battery_discharge > 0.0:
            if rng.random() < 0.5:
                battery_discharge = 0.0
            else:
                battery_charge = 0.0
        battery_charge = min(
            battery_charge,
            max((battery_max - battery_soc) / float(system_config["battery"]["charge_efficiency"]), 0.0),
        )
        battery_discharge = min(
            battery_discharge,
            max((battery_soc - battery_min) * float(system_config["battery"]["discharge_efficiency"]), 0.0),
        )
        battery_soc = update_battery_soc(battery_soc, battery_charge, battery_discharge, system_config)
        battery_soc = min(max(battery_soc, battery_min), battery_max)

        thermal_charge = rng.uniform(0.0, float(system_config["thermal_storage"]["charge_power_mw_th"]))
        thermal_discharge = rng.uniform(0.0, float(system_config["thermal_storage"]["discharge_power_mw_th"]))
        if thermal_charge > 0.0 and thermal_discharge > 0.0:
            if rng.random() < 0.5:
                thermal_discharge = 0.0
            else:
                thermal_charge = 0.0
        thermal_charge = min(
            thermal_charge,
            max((thermal_max - thermal_soc) / float(system_config["thermal_storage"]["charge_efficiency"]), 0.0),
        )
        thermal_discharge = min(
            thermal_discharge,
            max((thermal_soc - thermal_min) * float(system_config["thermal_storage"]["discharge_efficiency"]), 0.0),
        )
        thermal_soc = update_thermal_soc(thermal_soc, thermal_charge, thermal_discharge, system_config)
        thermal_soc = min(max(thermal_soc, thermal_min), thermal_max)

        heat_supply = (
            chp_electric * float(system_config["chp"]["heat_to_power_ratio"])
            + heat_pump_heat
            + thermal_discharge
            - thermal_charge
        )
        heat_gap = float(row["heat_load_mw_th"]) - heat_supply
        heat_shedding = max(heat_gap, 0.0)
        heat_dump = max(-heat_gap, 0.0)

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
                "heat_shedding_mw_th": heat_shedding,
                "heat_dump_mw_th": heat_dump,
                "electricity_import_price_eur_per_mwh": prices[t],
            }
        )

    return finalize_dispatch_frame(pd.DataFrame(rows, index=frame.index), system_config, policy_config)

