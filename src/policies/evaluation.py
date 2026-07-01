from __future__ import annotations

import pandas as pd

from src.policies.common import finalize_dispatch_frame, policy_cost


ACTION_COLUMNS = [
    "grid_import_mw",
    "grid_export_mw",
    "chp_electric_mw",
    "heat_pump_heat_mw_th",
    "battery_charge_mw",
    "battery_discharge_mw",
    "thermal_charge_mw_th",
    "thermal_discharge_mw_th",
]


def ensure_evaluation_columns(
    dispatch: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
) -> pd.DataFrame:
    result = dispatch.copy()
    if "heat_dump_mw_th" not in result.columns:
        result["heat_dump_mw_th"] = 0.0
    required = {
        "battery_charge_mw": 0.0,
        "battery_discharge_mw": 0.0,
        "thermal_charge_mw_th": 0.0,
        "thermal_discharge_mw_th": 0.0,
        "electric_shedding_mw": 0.0,
        "heat_shedding_mw_th": 0.0,
        "pv_curtailment_mw": 0.0,
        "wind_curtailment_mw": 0.0,
    }
    for column, default in required.items():
        if column not in result.columns:
            result[column] = default
    return finalize_dispatch_frame(result, system_config, policy_config)


def summarize_policy(
    policy_name: str,
    dispatch: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
) -> dict[str, float | str | int]:
    evaluated = ensure_evaluation_columns(dispatch, system_config, policy_config)
    action_std = evaluated[ACTION_COLUMNS].std(ddof=0).fillna(0.0)
    capacities = pd.Series(
        {
            "grid_import_mw": system_config["grid"]["import_capacity_mw"],
            "grid_export_mw": system_config["grid"]["export_capacity_mw"],
            "chp_electric_mw": system_config["chp"]["electric_capacity_mw"],
            "heat_pump_heat_mw_th": system_config["heat_pump"]["heat_capacity_mw_th"],
            "battery_charge_mw": system_config["battery"]["charge_power_mw"],
            "battery_discharge_mw": system_config["battery"]["discharge_power_mw"],
            "thermal_charge_mw_th": system_config["thermal_storage"]["charge_power_mw_th"],
            "thermal_discharge_mw_th": system_config["thermal_storage"]["discharge_power_mw_th"],
        },
        dtype=float,
    ).replace(0.0, 1.0)
    normalized_coverage = (action_std / capacities).clip(lower=0.0)

    return {
        "policy": policy_name,
        "hours": int(len(evaluated)),
        "total_cost_eur": policy_cost(evaluated, system_config, policy_config),
        "electric_shedding_mwh": float(evaluated["electric_shedding_mw"].sum()),
        "heat_shedding_mwh_th": float(evaluated["heat_shedding_mw_th"].sum()),
        "renewable_curtailment_mwh": float(
            evaluated["pv_curtailment_mw"].sum() + evaluated["wind_curtailment_mw"].sum()
        ),
        "grid_import_mwh": float(evaluated["grid_import_mw"].sum()),
        "grid_export_mwh": float(evaluated["grid_export_mw"].sum()),
        "chp_electric_mwh": float(evaluated["chp_electric_mw"].sum()),
        "heat_pump_heat_mwh_th": float(evaluated["heat_pump_heat_mw_th"].sum()),
        "battery_throughput_mwh": float(
            evaluated["battery_charge_mw"].sum() + evaluated["battery_discharge_mw"].sum()
        ),
        "thermal_throughput_mwh_th": float(
            evaluated["thermal_charge_mw_th"].sum()
            + evaluated["thermal_discharge_mw_th"].sum()
        ),
        "mean_abs_electric_residual_mw": float(evaluated["electric_balance_residual_mw"].abs().mean()),
        "mean_abs_heat_residual_mw_th": float(evaluated["heat_balance_residual_mw_th"].abs().mean()),
        "max_abs_electric_residual_mw": float(evaluated["electric_balance_residual_mw"].abs().max()),
        "max_abs_heat_residual_mw_th": float(evaluated["heat_balance_residual_mw_th"].abs().max()),
        "mean_solve_time_s": float(evaluated.get("mpc_solve_time_s", pd.Series([0.0])).mean()),
        "action_coverage_score": float(normalized_coverage.mean()),
    }


def summarize_many(
    dispatches: dict[str, pd.DataFrame],
    system_config: dict,
    policy_config: dict,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            summarize_policy(name, dispatch, system_config, policy_config)
            for name, dispatch in dispatches.items()
        ]
    )


def dataframe_to_markdown_table(frame: pd.DataFrame) -> str:
    """Render a compact GitHub-flavored Markdown table without optional deps."""

    def fmt(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in frame.columns) + " |")
    return "\n".join(lines) + "\n"
