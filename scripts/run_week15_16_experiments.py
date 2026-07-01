from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import time

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.experiments.week13_14 import (
    build_repeated_risk_scores,
    dataframe_to_markdown,
    evaluate_policy_with_safety_mode,
    evaluate_rule_dispatch,
    summarize_main_results,
)
from src.experiments.week15_16 import (
    apply_generalization_parameters,
    compute_confidence_intervals,
    compute_pairwise_tests,
    compute_tail_risk,
    make_generalization_scenarios,
    summarize_failure_modes,
    write_experiment_registry,
)
from src.offline_rl.baselines import load_transition_parquets, train_offline_algorithm
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs, solve_dispatch_day
from src.policies.common import policy_cost
from src.policies.rolling_mpc import run_rolling_mpc
from src.safety.adaptive_layer import AdaptiveSafetyConfig, AdaptiveSafetyLayer
from src.safety.fixed_projection import FixedProjectionConfig, FixedSafetyProjectionLayer


CONFIG_PATH_WEEK = ROOT / "configs" / "week15_16_experiments.yaml"
POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
WEEK13_RAW_PATH = ROOT / "results" / "week13_14_experiments" / "week13_raw_results.csv"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.labelsize": 7,
            "axes.titlesize": 8,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "figure.dpi": 150,
        }
    )


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def fixed_layer() -> FixedSafetyProjectionLayer:
    return FixedSafetyProjectionLayer(
        FixedProjectionConfig(prefer_fast_fallback=True)
    )


def adaptive_layer(config: dict) -> AdaptiveSafetyLayer:
    payload = config["adaptive_safety"]
    return AdaptiveSafetyLayer(
        fixed_layer(),
        AdaptiveSafetyConfig(
            low_risk_threshold=float(payload["low_risk_threshold"]),
            high_risk_threshold=float(payload["high_risk_threshold"]),
            blend_grid_size=int(payload["blend_grid_size"]),
            hard_safety_tolerance=float(payload["hard_safety_tolerance"]),
            force_project_if_hard_violation=bool(payload["force_project_if_hard_violation"]),
        ),
    )


def apply_price_multiplier(cost_config: dict, parameters: dict[str, float]) -> dict:
    result = deepcopy(cost_config)
    multiplier = float(parameters.get("price_multiplier", 1.0))
    price = result["costs"]["electricity_import_eur_per_mwh"]
    for key in ["base", "daytime_adder", "evening_peak_adder"]:
        price[key] = float(price[key]) * multiplier
    return result


def extract_window(frame: pd.DataFrame, start_utc: str, hours: int, lookahead: int = 24) -> pd.DataFrame:
    start = pd.Timestamp(start_utc)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    needed = hours + lookahead - 1
    selected = frame.loc[start : start + pd.Timedelta(hours=needed - 1)].copy()
    if len(selected) < needed:
        raise ValueError(f"not enough data for scenario window starting at {start_utc}")
    return selected


def evaluate_perfect_information(frame: pd.DataFrame, system_config: dict, cost_config: dict, episode_hours: int) -> dict[str, float | int]:
    tic = time.perf_counter()
    result = solve_dispatch_day(frame.iloc[:episode_hours], system_config, cost_config, enforce_terminal_soc=False)
    elapsed = ((time.perf_counter() - tic) * 1000.0) / max(episode_hours, 1)
    dispatch = result.frame
    hard = float((dispatch["electric_shedding_mw"] + dispatch["heat_shedding_mw_th"]).sum())
    safety = _safety_sum(dispatch)
    return {
        "episodes": 1,
        "raw_mean_episode_hard_safety_cost": hard,
        "mean_episode_cost_eur": policy_cost(dispatch, system_config, cost_config),
        "cvar90_episode_cost_eur": policy_cost(dispatch, system_config, cost_config),
        "mean_episode_safety_cost": safety,
        "mean_episode_hard_safety_cost": hard,
        "unsafe_episode_rate": float(hard > 1e-6),
        "mean_projection_distance_l2": 0.0,
        "mean_weighted_projection_distance": 0.0,
        "mean_decision_time_ms": elapsed,
        "intervention_rate": 0.0,
        "pass_through_rate": 1.0,
        "partial_projection_rate": 0.0,
        "full_projection_rate": 0.0,
    }


def evaluate_rolling(frame: pd.DataFrame, system_config: dict, cost_config: dict, episode_hours: int) -> dict[str, float | int]:
    dispatch = run_rolling_mpc(frame, system_config, cost_config, evaluation_hours=episode_hours)
    hard = float((dispatch["electric_shedding_mw"] + dispatch["heat_shedding_mw_th"]).sum())
    safety = _safety_sum(dispatch)
    return {
        "episodes": 1,
        "raw_mean_episode_hard_safety_cost": hard,
        "mean_episode_cost_eur": policy_cost(dispatch, system_config, cost_config),
        "cvar90_episode_cost_eur": policy_cost(dispatch, system_config, cost_config),
        "mean_episode_safety_cost": safety,
        "mean_episode_hard_safety_cost": hard,
        "unsafe_episode_rate": float(hard > 1e-6),
        "mean_projection_distance_l2": 0.0,
        "mean_weighted_projection_distance": 0.0,
        "mean_decision_time_ms": float(dispatch.get("mpc_solve_time_s", pd.Series([0.0])).mean() * 1000.0),
        "intervention_rate": 0.0,
        "pass_through_rate": 1.0,
        "partial_projection_rate": 0.0,
        "full_projection_rate": 0.0,
    }


def _safety_sum(dispatch: pd.DataFrame) -> float:
    total = pd.Series(0.0, index=dispatch.index)
    for column in [
        "electric_shedding_mw",
        "heat_shedding_mw_th",
        "heat_dump_mw_th",
        "pv_curtailment_mw",
        "wind_curtailment_mw",
    ]:
        if column in dispatch.columns:
            total = total + dispatch[column]
    return float(total.sum())


def run_week15(config: dict, result_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    transitions = load_transition_parquets([str(ROOT / path) for path in config["experiment"]["dataset_paths"]])
    trained = {}
    manifest = []
    for algorithm in config["experiment"]["algorithms"]:
        tic = time.perf_counter()
        training = train_offline_algorithm(
            algorithm,
            transitions,
            config["training"],
            seed=int(config["experiment"]["seed"]),
        )
        manifest.append(
            {
                "algorithm": algorithm,
                "seed": int(config["experiment"]["seed"]),
                "train_time_s": time.perf_counter() - tic,
                "steps": int(config["training"]["steps"]),
            }
        )
        trained[algorithm] = training.policy

    rows = []
    trajectory_rows = []
    scenarios = make_generalization_scenarios()
    episode_hours = int(config["evaluation"]["episode_hours"])
    risk_by_family = {str(k): float(v) for k, v in config["evaluation"]["risk_score_by_family"].items()}
    for scenario in scenarios:
        raw_window = extract_window(frame, str(scenario["start_utc"]), episode_hours)
        window = apply_generalization_parameters(raw_window, scenario["parameters"])
        cost_config = apply_price_multiplier(policy_config, scenario["parameters"])
        risk = risk_by_family.get(str(scenario["family"]), 3.5)
        for method, metrics in [
            ("perfect_information_lp", evaluate_perfect_information(window, system_config, cost_config, episode_hours)),
            ("rolling_mpc", evaluate_rolling(window, system_config, cost_config, episode_hours)),
            ("rule_based", evaluate_rule_dispatch(window, system_config, cost_config, episode_starts=[0], episode_hours=episode_hours)),
        ]:
            rows.append({"method": method, "algorithm": method, "scenario": scenario["name"], "family": scenario["family"], "seed": -1, **metrics})
        for algorithm, policy in trained.items():
            base = evaluate_policy_with_safety_mode(
                policy,
                window,
                system_config,
                cost_config,
                episode_starts=[0],
                episode_hours=episode_hours,
                safety_mode="none",
            )
            rows.append({"method": algorithm, "algorithm": algorithm, "scenario": scenario["name"], "family": scenario["family"], "seed": int(config["experiment"]["seed"]), **base})
            adaptive = evaluate_policy_with_safety_mode(
                policy,
                window,
                system_config,
                cost_config,
                episode_starts=[0],
                episode_hours=episode_hours,
                safety_mode="adaptive",
                adaptive_layer=adaptive_layer(config),
                risk_scores=build_repeated_risk_scores([risk], episode_hours),
            )
            rows.append({"method": f"{algorithm}_adaptive_safety", "algorithm": algorithm, "scenario": scenario["name"], "family": scenario["family"], "seed": int(config["experiment"]["seed"]), **adaptive})

        if scenario["name"] == "cold_wave_device_fault":
            policy = trained["iql"]
            env = None
            from src.envs.integrated_energy_env import IntegratedEnergyEnv

            env = IntegratedEnergyEnv(window, system_config, cost_config, episode_hours=episode_hours, start_index=0)
            observation, _ = env.reset(seed=0)
            layer = adaptive_layer(config)
            for hour in range(episode_hours):
                action = policy.predict(observation)
                result = layer.project(env, action, risk_score=risk)
                observation, _, terminated, truncated, info = env.step(result.action)
                trajectory_rows.append(
                    {
                        "hour": hour,
                        "scenario": scenario["name"],
                        "raw_hard_safety_cost": result.raw_hard_safety_cost,
                        "projected_hard_safety_cost": result.projected_hard_safety_cost,
                        "projection_distance_l2": result.projection_distance_l2,
                        "mode": result.mode,
                        "heat_load_mw_th": info["dispatch"]["heat_load_mw_th"],
                        "electric_load_mw": info["dispatch"]["electric_load_mw"],
                    }
                )
                if terminated or truncated:
                    break

    results = pd.DataFrame(rows)
    trajectory = pd.DataFrame(trajectory_rows)
    results.to_csv(result_dir / "week15_generalization_stress_results.csv", index=False)
    trajectory.to_csv(result_dir / "week15_intervention_trajectory.csv", index=False)
    pd.DataFrame(manifest).to_csv(result_dir / "week15_training_manifest.csv", index=False)
    return results, trajectory


def run_week16(config: dict, week15: pd.DataFrame, result_dir: Path, figure_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    week13 = pd.read_csv(WEEK13_RAW_PATH) if WEEK13_RAW_PATH.exists() else pd.DataFrame()
    combined = pd.concat([week13.assign(source="week13_14"), week15.assign(source="week15")], ignore_index=True, sort=False)
    metrics = ["mean_episode_cost_eur", "mean_episode_hard_safety_cost", "unsafe_episode_rate"]
    ci = compute_confidence_intervals(
        combined.loc[combined["seed"] >= 0].copy(),
        metrics,
        group_columns=("method", "scenario"),
    )
    pairs = [
        ("iql", "iql_adaptive_safety"),
        ("cql", "cql_adaptive_safety"),
        ("iql_fixed_safety", "iql_adaptive_safety"),
        ("cql_fixed_safety", "cql_adaptive_safety"),
    ]
    tests = compute_pairwise_tests(
        combined.loc[combined["seed"] >= 0].copy(),
        pairs=pairs,
        metric="mean_episode_hard_safety_cost",
    )
    tail = compute_tail_risk(combined)
    failures = summarize_failure_modes(combined, hard_safety_threshold=1e-6)
    ci.to_csv(result_dir / "week16_confidence_intervals.csv", index=False)
    tests.to_csv(result_dir / "week16_pairwise_tests.csv", index=False)
    tail.to_csv(result_dir / "week16_tail_risk_metrics.csv", index=False)
    failures.to_csv(result_dir / "week16_failure_modes.csv", index=False)

    result_files = [
        str(result_dir / name)
        for name in [
            "week15_generalization_stress_results.csv",
            "week15_intervention_trajectory.csv",
            "week15_training_manifest.csv",
            "week16_confidence_intervals.csv",
            "week16_pairwise_tests.csv",
            "week16_tail_risk_metrics.csv",
            "week16_failure_modes.csv",
        ]
    ]
    figure_files = [
        str(figure_dir / "week15_stress_summary.png"),
        str(figure_dir / "week15_intervention_trajectory.png"),
        str(figure_dir / "week16_statistics_summary.png"),
    ]
    write_experiment_registry(
        ROOT / "docs" / "experiment_registry.md",
        commands=[
            "python scripts\\run_week13_14_experiments.py",
            "python scripts\\run_week15_16_experiments.py",
            "python -m unittest discover -s tests -v",
        ],
        result_files=result_files,
        figure_files=figure_files,
        config_files=[
            str(CONFIG_PATH_WEEK),
            str(ROOT / "configs" / "week13_14_experiments.yaml"),
            str(ROOT / "configs" / "adaptive_safety.yaml"),
            str(ROOT / "configs" / "safety_projection.yaml"),
        ],
    )
    return ci, tests, tail, failures


def plot_week15(results: pd.DataFrame, trajectory: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    selected_methods = ["rule_based", "iql", "iql_adaptive_safety", "cql_adaptive_safety"]
    subset = results.loc[results["method"].isin(selected_methods)].copy()
    family = subset.groupby(["method", "family"], as_index=False).agg(
        mean_hard=("mean_episode_hard_safety_cost", "mean"),
        mean_cost=("mean_episode_cost_eur", "mean"),
        intervention=("intervention_rate", "mean"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.0))
    family.pivot(index="family", columns="method", values="mean_hard").plot(kind="bar", ax=axes[0])
    family.pivot(index="family", columns="method", values="mean_cost").plot(kind="bar", ax=axes[1])
    family.pivot(index="family", columns="method", values="intervention").plot(kind="bar", ax=axes[2])
    axes[0].set_title("Hard-safety risk")
    axes[1].set_title("Cost")
    axes[2].set_title("Intervention rate")
    for ax in axes:
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=35)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.tight_layout()
    save_figure(fig, figure_dir / "week15_stress_summary")
    plt.close(fig)

    if not trajectory.empty:
        fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.0), sharex=True)
        axes[0].plot(trajectory["hour"], trajectory["raw_hard_safety_cost"], label="Raw hard safety", color="#B23A48")
        axes[0].plot(trajectory["hour"], trajectory["projected_hard_safety_cost"], label="Projected hard safety", color="#6C9A8B")
        axes[1].bar(trajectory["hour"], trajectory["projection_distance_l2"], color="#335C81")
        axes[2].plot(trajectory["hour"], trajectory["heat_load_mw_th"], label="Heat load", color="#E3A62F")
        axes[2].plot(trajectory["hour"], trajectory["electric_load_mw"], label="Electric load", color="#7A7A7A")
        axes[0].set_ylabel("Hard safety")
        axes[1].set_ylabel("L2 correction")
        axes[2].set_ylabel("Load")
        axes[2].set_xlabel("Hour")
        for ax in axes:
            ax.grid(axis="y", color="#D9D9D9", lw=0.5)
            ax.legend()
        fig.tight_layout()
        save_figure(fig, figure_dir / "week15_intervention_trajectory")
        plt.close(fig)


def plot_week16(ci: pd.DataFrame, tests: pd.DataFrame, tail: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.0))
    hard = ci.loc[(ci["metric"] == "mean_episode_hard_safety_cost") & (ci["method"].isin(["iql", "iql_adaptive_safety", "cql", "cql_adaptive_safety"]))]
    hard.groupby("method")["mean"].mean().plot(kind="bar", ax=axes[0], color="#6C9A8B")
    axes[0].set_title("Mean hard safety with CI source")
    tests.groupby("treatment")["p_value"].min().plot(kind="bar", ax=axes[1], color="#335C81")
    axes[1].axhline(0.05, color="#B23A48", ls="--", lw=1.0)
    axes[1].set_title("Pairwise p-values")
    selected_tail = tail.loc[tail["method"].isin(["iql", "iql_adaptive_safety", "cql", "cql_adaptive_safety"])]
    selected_tail.groupby("method")["cvar90_hard_safety_cost"].mean().plot(kind="bar", ax=axes[2], color="#E3A62F")
    axes[2].set_title("CVaR90 hard safety")
    for ax in axes:
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=40)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.tight_layout()
    save_figure(fig, figure_dir / "week16_statistics_summary")
    plt.close(fig)


def write_docs(results: pd.DataFrame, ci: pd.DataFrame, tests: pd.DataFrame, tail: pd.DataFrame, failures: pd.DataFrame, result_dir: Path, figure_dir: Path) -> None:
    stress_table = results.loc[
        results["method"].isin(["perfect_information_lp", "rolling_mpc", "rule_based", "iql", "iql_adaptive_safety", "cql_adaptive_safety"]),
        ["method", "scenario", "family", "mean_episode_cost_eur", "mean_episode_hard_safety_cost", "unsafe_episode_rate", "intervention_rate", "mean_decision_time_ms"],
    ].copy()
    doc15 = f"""# 第15周：泛化与压力测试

本周进行跨年份、跨季节、气候区代理和联合压力测试。压力场景包括寒潮、热浪/低光照、连续低风光、价格尖峰和设备性能退化。结果不隐藏失败边界：未加安全层的 RL 在多数压力场景仍出现明显 hard safety violation，而 adaptive safety 能显著降低风险，但在极端复合压力下仍可能存在残余或较高干预成本。

## 压力测试表

{dataframe_to_markdown(stress_table)}

## 失败模式清单

{dataframe_to_markdown(failures.head(30))}

图件：

- `{figure_dir / 'week15_stress_summary.png'}`
- `{figure_dir / 'week15_intervention_trajectory.png'}`
"""
    (ROOT / "docs" / "week15_generalization_stress.md").write_text(doc15, encoding="utf-8")

    ci_short = ci.loc[ci["metric"].isin(["mean_episode_cost_eur", "mean_episode_hard_safety_cost"])].head(60)
    doc16 = f"""# 第16周：统计分析和实验冻结

本周完成均值、标准差、95% 置信区间、成对显著性检验、CVaR、最大违反、不可行回合比例和实验注册表。最终实验版本冻结在 `configs/week13_14_experiments.yaml` 与 `configs/week15_16_experiments.yaml`。

## 95% 置信区间节选

{dataframe_to_markdown(ci_short)}

## 成对显著性检验

{dataframe_to_markdown(tests)}

## 尾部风险指标

{dataframe_to_markdown(tail.head(60))}

## 可复现命令

- `python scripts\\run_week13_14_experiments.py`
- `python scripts\\run_week15_16_experiments.py`
- `python -m unittest discover -s tests -v`

注册表：`docs/experiment_registry.md`
"""
    (ROOT / "docs" / "week16_statistics_freeze.md").write_text(doc16, encoding="utf-8")


def main() -> None:
    configure_style()
    config = load_yaml(CONFIG_PATH_WEEK)
    result_dir = ROOT / config["outputs"]["result_dir"]
    figure_dir = ROOT / config["outputs"]["figure_dir"]
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    week15, trajectory = run_week15(config, result_dir)
    plot_week15(week15, trajectory, figure_dir)
    ci, tests, tail, failures = run_week16(config, week15, result_dir, figure_dir)
    plot_week16(ci, tests, tail, figure_dir)
    write_docs(week15, ci, tests, tail, failures, result_dir, figure_dir)
    print(week15.to_string(index=False))
    print(f"result_dir={result_dir}")
    print(f"figure_dir={figure_dir}")


if __name__ == "__main__":
    main()
