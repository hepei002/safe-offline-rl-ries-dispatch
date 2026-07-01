from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats


def make_generalization_scenarios() -> list[dict[str, object]]:
    """Define week-15 generalization and stress scenarios."""

    return [
        {"name": "year_2017_winter", "family": "cross_year", "start_utc": "2017-01-16 00:00:00+00:00", "parameters": {}},
        {"name": "year_2018_winter", "family": "cross_year", "start_utc": "2018-01-15 00:00:00+00:00", "parameters": {}},
        {"name": "year_2019_winter", "family": "cross_year", "start_utc": "2019-01-14 00:00:00+00:00", "parameters": {}},
        {"name": "summer_peak", "family": "cross_season", "start_utc": "2018-08-13 00:00:00+00:00", "parameters": {"heat_load_multiplier": 0.75, "electric_load_multiplier": 1.10}},
        {"name": "shoulder_season", "family": "cross_season", "start_utc": "2018-10-15 00:00:00+00:00", "parameters": {"heat_load_multiplier": 0.90}},
        {"name": "cold_climate_zone", "family": "climate_zone", "start_utc": "2019-01-14 00:00:00+00:00", "parameters": {"heat_load_multiplier": 1.35, "cop_multiplier": 0.80, "temperature_delta_c": -10.0}},
        {"name": "warm_low_solar_zone", "family": "climate_zone", "start_utc": "2018-08-13 00:00:00+00:00", "parameters": {"electric_load_multiplier": 1.15, "pv_multiplier": 0.65, "temperature_delta_c": 6.0}},
        {"name": "price_spike_low_renewable", "family": "compound_stress", "start_utc": "2019-01-14 00:00:00+00:00", "parameters": {"pv_multiplier": 0.45, "wind_multiplier": 0.55, "price_multiplier": 2.2}},
        {"name": "cold_wave_device_fault", "family": "compound_stress", "start_utc": "2019-01-14 00:00:00+00:00", "parameters": {"heat_load_multiplier": 1.65, "electric_load_multiplier": 1.25, "cop_multiplier": 0.70, "temperature_delta_c": -14.0}},
        {"name": "three_day_low_renewable", "family": "compound_stress", "start_utc": "2018-02-05 00:00:00+00:00", "parameters": {"pv_multiplier": 0.30, "wind_multiplier": 0.35}},
    ]


def apply_generalization_parameters(frame: pd.DataFrame, parameters: dict[str, float]) -> pd.DataFrame:
    result = frame.copy()
    multipliers = {
        "electric_load_mw": float(parameters.get("electric_load_multiplier", 1.0)),
        "heat_load_mw_th": float(parameters.get("heat_load_multiplier", 1.0)),
        "pv_available_mw": float(parameters.get("pv_multiplier", 1.0)),
        "wind_available_mw": float(parameters.get("wind_multiplier", 1.0)),
        "cop_ashp_radiator": float(parameters.get("cop_multiplier", 1.0)),
    }
    for column, multiplier in multipliers.items():
        if column in result.columns:
            result[column] = result[column].astype(float) * multiplier
    if "temperature_c" in result.columns:
        result["temperature_c"] = result["temperature_c"].astype(float) + float(parameters.get("temperature_delta_c", 0.0))
    if "cop_ashp_radiator" in result.columns:
        result["cop_ashp_radiator"] = result["cop_ashp_radiator"].clip(lower=1.0)
    for column in ["pv_available_mw", "wind_available_mw"]:
        if column in result.columns:
            result[column] = result[column].clip(lower=0.0)
    if "price_multiplier" in parameters:
        result["price_multiplier"] = float(parameters["price_multiplier"])
    return result


def compute_confidence_intervals(
    frame: pd.DataFrame,
    metrics: Iterable[str],
    *,
    group_columns: tuple[str, ...] = ("method", "scenario"),
    confidence: float = 0.95,
) -> pd.DataFrame:
    rows = []
    for keys, group in frame.groupby(list(group_columns)):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_payload = dict(zip(group_columns, keys))
        for metric in metrics:
            values = group[metric].dropna().to_numpy(dtype=float)
            n = len(values)
            mean = float(np.mean(values)) if n else 0.0
            std = float(np.std(values, ddof=1)) if n > 1 else 0.0
            if n > 1:
                half = float(stats.t.ppf((1.0 + confidence) / 2.0, n - 1) * std / np.sqrt(n))
            else:
                half = 0.0
            rows.append(
                {
                    **key_payload,
                    "metric": metric,
                    "n": int(n),
                    "mean": mean,
                    "std": std,
                    "ci95_half_width": half,
                    "ci95_low": mean - half,
                    "ci95_high": mean + half,
                }
            )
    return pd.DataFrame(rows)


def compute_pairwise_tests(
    frame: pd.DataFrame,
    *,
    pairs: list[tuple[str, str]],
    metric: str,
    scenario_column: str = "scenario",
) -> pd.DataFrame:
    rows = []
    for scenario, scenario_group in frame.groupby(scenario_column):
        for baseline, treatment in pairs:
            base = scenario_group.loc[scenario_group["method"] == baseline, ["seed", metric]]
            treat = scenario_group.loc[scenario_group["method"] == treatment, ["seed", metric]]
            paired = base.merge(treat, on="seed", suffixes=("_baseline", "_treatment"))
            if len(paired) >= 2:
                delta = paired[f"{metric}_treatment"] - paired[f"{metric}_baseline"]
                test = stats.ttest_rel(paired[f"{metric}_treatment"], paired[f"{metric}_baseline"])
                p_value = float(test.pvalue) if np.isfinite(test.pvalue) else 1.0
                statistic = float(test.statistic) if np.isfinite(test.statistic) else 0.0
                mean_delta = float(delta.mean())
            elif len(paired) == 1:
                p_value = 1.0
                statistic = 0.0
                mean_delta = float((paired[f"{metric}_treatment"] - paired[f"{metric}_baseline"]).iloc[0])
            else:
                p_value = 1.0
                statistic = 0.0
                mean_delta = 0.0
            rows.append(
                {
                    "scenario": scenario,
                    "baseline": baseline,
                    "treatment": treatment,
                    "metric": metric,
                    "n_pairs": int(len(paired)),
                    "mean_delta": mean_delta,
                    "t_statistic": statistic,
                    "p_value": p_value,
                }
            )
    return pd.DataFrame(rows)


def compute_tail_risk(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, scenario), group in frame.groupby(["method", "scenario"]):
        hard = group["mean_episode_hard_safety_cost"].to_numpy(dtype=float)
        cost = group["mean_episode_cost_eur"].to_numpy(dtype=float)
        rows.append(
            {
                "method": method,
                "scenario": scenario,
                "max_hard_safety_cost": float(np.max(hard)) if len(hard) else 0.0,
                "cvar90_hard_safety_cost": _cvar(hard, 0.90),
                "cvar90_episode_cost_eur": _cvar(cost, 0.90),
                "infeasible_episode_rate": float(np.mean(hard > 1e-6)) if len(hard) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _cvar(values: np.ndarray, alpha: float) -> float:
    if len(values) == 0:
        return 0.0
    threshold = np.quantile(values, alpha)
    tail = values[values >= threshold]
    return float(tail.mean()) if len(tail) else float(values.max())


def summarize_failure_modes(frame: pd.DataFrame, *, hard_safety_threshold: float = 1e-6) -> pd.DataFrame:
    failures = frame.loc[
        (frame["mean_episode_hard_safety_cost"] > hard_safety_threshold)
        | (frame["unsafe_episode_rate"] > 0.0)
    ].copy()
    if failures.empty:
        return pd.DataFrame(
            columns=[
                "method",
                "scenario",
                "mean_episode_hard_safety_cost",
                "unsafe_episode_rate",
                "mean_episode_cost_eur",
                "failure_mode",
            ]
        )
    failures["failure_mode"] = np.where(
        failures["mean_episode_hard_safety_cost"] > hard_safety_threshold,
        "residual_hard_safety_violation",
        "unsafe_episode_indicator_only",
    )
    return failures[
        [
            "method",
            "scenario",
            "mean_episode_hard_safety_cost",
            "unsafe_episode_rate",
            "mean_episode_cost_eur",
            "failure_mode",
        ]
    ].sort_values(["mean_episode_hard_safety_cost", "unsafe_episode_rate"], ascending=False)


def write_experiment_registry(
    path: Path,
    *,
    commands: list[str],
    result_files: list[str],
    figure_files: list[str],
    config_files: list[str],
) -> None:
    lines = [
        "# Experiment Registry",
        "",
        "## Reproducible commands",
        "",
        *[f"- `{command}`" for command in commands],
        "",
        "## Configuration files",
        "",
        *[f"- `{item}`" for item in config_files],
        "",
        "## Result files",
        "",
        *[f"- `{item}`" for item in result_files],
        "",
        "## Figure files",
        "",
        *[f"- `{item}`" for item in figure_files],
        "",
        "## Rebuild audit",
        "",
        "All listed figures are generated by the corresponding scripts from CSV/parquet result logs in `results/`.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
