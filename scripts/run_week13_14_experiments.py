from __future__ import annotations

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
from src.offline_rl.baselines import load_transition_parquets, train_offline_algorithm
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs, solve_dispatch_day
from src.policies.common import policy_cost
from src.policies.rolling_mpc import run_rolling_mpc
from src.safety.adaptive_layer import AdaptiveSafetyConfig, AdaptiveSafetyLayer
from src.safety.fixed_projection import FixedProjectionConfig, FixedSafetyProjectionLayer
from src.shift.protocols import apply_shift_protocol, load_shift_protocol


CONFIG_PATH_WEEK = ROOT / "configs" / "week13_14_experiments.yaml"
POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
SHIFT_PROTOCOL_PATH = ROOT / "configs" / "shift_protocol.yaml"
OOD_RISK_PATH = ROOT / "results" / "shift_protocol_ood" / "ood_risk_summary.csv"


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


def select_evaluation_frame(frame: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, list[int]]:
    evaluation = config["evaluation"]
    start = pd.Timestamp(evaluation["start_utc"])
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    episode_hours = int(evaluation["episode_hours"])
    episodes = int(evaluation["episodes"])
    stride = int(evaluation["stride_hours"])
    lookahead = 24
    needed = (episodes - 1) * stride + episode_hours + lookahead - 1
    selected = frame.loc[start : start + pd.Timedelta(hours=needed - 1)].copy()
    if len(selected) < needed:
        raise ValueError("not enough evaluation data for week 13/14 experiment")
    return selected, [i * stride for i in range(episodes)]


def risk_scores_by_scenario() -> dict[str, float]:
    if not OOD_RISK_PATH.exists():
        return {}
    risk = pd.read_csv(OOD_RISK_PATH)
    return {
        str(row["scenario"]): float(row["mean_ood_score"])
        for _, row in risk.loc[risk["scenario"] != "all"].iterrows()
    }


def fixed_config(scale: float = 1.0) -> FixedProjectionConfig:
    return FixedProjectionConfig(
        prefer_fast_fallback=True,
        distance_weights=(1.0 * scale, 1.0 * scale, 0.5 * scale, 0.5 * scale),
    )


def adaptive_config(config: dict, low: float | None = None, high: float | None = None) -> AdaptiveSafetyConfig:
    payload = config["adaptive_safety"]
    return AdaptiveSafetyConfig(
        low_risk_threshold=float(payload["low_risk_threshold"] if low is None else low),
        high_risk_threshold=float(payload["high_risk_threshold"] if high is None else high),
        blend_grid_size=int(payload["blend_grid_size"]),
        hard_safety_tolerance=float(payload["hard_safety_tolerance"]),
        force_project_if_hard_violation=bool(payload["force_project_if_hard_violation"]),
    )


def scenario_frames(base_frame: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]:
    protocol = load_shift_protocol(SHIFT_PROTOCOL_PATH)
    scenario_map = {scenario.name: scenario for scenario in protocol.scenarios}
    frames = {}
    for name in config["evaluation"]["scenarios"]:
        shifted, _ = apply_shift_protocol(base_frame, scenario_map[name])
        frames[name] = shifted
    return frames


def evaluate_dispatch_episode_metrics(dispatches: list[pd.DataFrame], solve_times_ms: list[float], system_config: dict, cost_config: dict) -> dict[str, float | int]:
    costs = []
    hard = []
    safety = []
    for dispatch in dispatches:
        costs.append(policy_cost(dispatch, system_config, cost_config))
        h = float((dispatch["electric_shedding_mw"] + dispatch["heat_shedding_mw_th"]).sum())
        hard.append(h)
        safety.append(
            float(
                (
                    dispatch["electric_shedding_mw"]
                    + dispatch["heat_shedding_mw_th"]
                    + dispatch.get("heat_dump_mw_th", 0.0)
                    + dispatch["pv_curtailment_mw"]
                    + dispatch["wind_curtailment_mw"]
                ).sum()
            )
        )
    return {
        "episodes": len(costs),
        "raw_mean_episode_hard_safety_cost": float(np.mean(hard)),
        "mean_episode_cost_eur": float(np.mean(costs)),
        "cvar90_episode_cost_eur": float(np.mean([np.max(costs)])),
        "mean_episode_safety_cost": float(np.mean(safety)),
        "mean_episode_hard_safety_cost": float(np.mean(hard)),
        "unsafe_episode_rate": float(np.mean(np.asarray(hard) > 1e-6)),
        "mean_projection_distance_l2": 0.0,
        "mean_weighted_projection_distance": 0.0,
        "mean_decision_time_ms": float(np.mean(solve_times_ms)) if solve_times_ms else 0.0,
        "intervention_rate": 0.0,
        "pass_through_rate": 1.0,
        "partial_projection_rate": 0.0,
        "full_projection_rate": 0.0,
    }


def evaluate_perfect_information(frame: pd.DataFrame, system_config: dict, cost_config: dict, starts: list[int], episode_hours: int) -> dict[str, float | int]:
    dispatches = []
    times = []
    for start in starts:
        episode = frame.iloc[start : start + episode_hours].copy()
        tic = time.perf_counter()
        result = solve_dispatch_day(episode, system_config, cost_config, enforce_terminal_soc=False)
        times.extend([((time.perf_counter() - tic) * 1000.0) / max(episode_hours, 1)] * episode_hours)
        dispatches.append(result.frame)
    return evaluate_dispatch_episode_metrics(dispatches, times, system_config, cost_config)


def evaluate_rolling_mpc(frame: pd.DataFrame, system_config: dict, cost_config: dict, starts: list[int], episode_hours: int) -> dict[str, float | int]:
    dispatches = []
    times = []
    lookahead = int(system_config["system"]["scheduling_horizon_hours"])
    for start in starts:
        window = frame.iloc[start : start + episode_hours + lookahead - 1].copy()
        dispatch = run_rolling_mpc(window, system_config, cost_config, evaluation_hours=episode_hours)
        dispatches.append(dispatch)
        if "mpc_solve_time_s" in dispatch.columns:
            times.extend((dispatch["mpc_solve_time_s"].to_numpy(dtype=float) * 1000.0).tolist())
    return evaluate_dispatch_episode_metrics(dispatches, times, system_config, cost_config)


def run_main_experiment(config: dict, result_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, int], object]]:
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    eval_frame, starts = select_evaluation_frame(frame, config)
    frames = scenario_frames(eval_frame, config)
    episode_hours = int(config["evaluation"]["episode_hours"])
    risks = risk_scores_by_scenario()
    fixed_layer = FixedSafetyProjectionLayer(fixed_config())
    adaptive_layer = AdaptiveSafetyLayer(fixed_layer, adaptive_config(config))
    all_transitions = load_transition_parquets([str(ROOT / p) for p in config["experiment"]["dataset_paths"]["all"]])
    trained: dict[tuple[str, int], object] = {}
    rows: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []

    for scenario, shifted in frames.items():
        for method, metrics in [
            ("perfect_information_lp", evaluate_perfect_information(shifted, system_config, policy_config, starts, episode_hours)),
            ("rolling_mpc", evaluate_rolling_mpc(shifted, system_config, policy_config, starts, episode_hours)),
            ("rule_based", evaluate_rule_dispatch(shifted, system_config, policy_config, episode_starts=starts, episode_hours=episode_hours)),
        ]:
            rows.append({"method": method, "algorithm": method, "seed": -1, "scenario": scenario, "safety_mode": "classical", **metrics})

    for algorithm in config["experiment"]["algorithms"]:
        for seed in config["experiment"]["seeds"]:
            tic = time.perf_counter()
            training = train_offline_algorithm(algorithm, all_transitions, config["training"], seed=int(seed))
            trained[(algorithm, int(seed))] = training.policy
            train_time = time.perf_counter() - tic
            manifest.append({"algorithm": algorithm, "seed": int(seed), "dataset": "all", "train_time_s": train_time, "steps": int(config["training"]["steps"])})
            for scenario, shifted in frames.items():
                risk_list = build_repeated_risk_scores([risks.get(scenario, 3.5)] * len(starts), episode_hours)
                base = evaluate_policy_with_safety_mode(
                    training.policy,
                    shifted,
                    system_config,
                    policy_config,
                    episode_starts=starts,
                    episode_hours=episode_hours,
                    safety_mode="none",
                )
                rows.append({"method": algorithm, "algorithm": algorithm, "seed": int(seed), "scenario": scenario, "safety_mode": "none", **base})
                if algorithm in config["experiment"]["safety_algorithms"]:
                    ood = evaluate_policy_with_safety_mode(
                        training.policy,
                        shifted,
                        system_config,
                        policy_config,
                        episode_starts=starts,
                        episode_hours=episode_hours,
                        safety_mode="ood_warning",
                        risk_scores=risk_list,
                    )
                    rows.append({"method": f"{algorithm}_ood_warning", "algorithm": algorithm, "seed": int(seed), "scenario": scenario, "safety_mode": "ood_warning", **ood})
                    fixed = evaluate_policy_with_safety_mode(
                        training.policy,
                        shifted,
                        system_config,
                        policy_config,
                        episode_starts=starts,
                        episode_hours=episode_hours,
                        safety_mode="fixed",
                        fixed_layer=fixed_layer,
                    )
                    rows.append({"method": f"{algorithm}_fixed_safety", "algorithm": algorithm, "seed": int(seed), "scenario": scenario, "safety_mode": "fixed", **fixed})
                    adaptive = evaluate_policy_with_safety_mode(
                        training.policy,
                        shifted,
                        system_config,
                        policy_config,
                        episode_starts=starts,
                        episode_hours=episode_hours,
                        safety_mode="adaptive",
                        adaptive_layer=adaptive_layer,
                        risk_scores=risk_list,
                    )
                    rows.append({"method": f"{algorithm}_adaptive_safety", "algorithm": algorithm, "seed": int(seed), "scenario": scenario, "safety_mode": "adaptive", **adaptive})
    results = pd.DataFrame(rows)
    manifest_frame = pd.DataFrame(manifest)
    results.to_csv(result_dir / "week13_raw_results.csv", index=False)
    manifest_frame.to_csv(result_dir / "week13_experiment_manifest.csv", index=False)
    return results, manifest_frame, trained


def run_week14_experiments(config: dict, trained: dict[tuple[str, int], object], result_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    eval_frame, starts = select_evaluation_frame(frame, config)
    frames = scenario_frames(eval_frame, config)
    episode_hours = int(config["evaluation"]["episode_hours"])
    risks = risk_scores_by_scenario()
    scenario = "compound_extreme"
    shifted = frames[scenario]
    seed = int(config["sensitivity"]["seeds"][0])
    policy = trained.get(("iql", seed)) or next(iter(trained.values()))

    threshold_rows = []
    for pair in config["sensitivity"]["ood_thresholds"]:
        fixed_layer = FixedSafetyProjectionLayer(fixed_config())
        adaptive_layer = AdaptiveSafetyLayer(fixed_layer, adaptive_config(config, low=float(pair["low"]), high=float(pair["high"])))
        metrics = evaluate_policy_with_safety_mode(
            policy,
            shifted,
            system_config,
            policy_config,
            episode_starts=starts,
            episode_hours=episode_hours,
            safety_mode="adaptive",
            adaptive_layer=adaptive_layer,
            risk_scores=build_repeated_risk_scores([risks.get(scenario, 3.5)] * len(starts), episode_hours),
        )
        threshold_rows.append({"sensitivity": "ood_threshold", "level": f"{pair['low']}-{pair['high']}", **metrics})

    for scale in config["sensitivity"]["distance_weight_scales"]:
        fixed_layer = FixedSafetyProjectionLayer(fixed_config(float(scale)))
        metrics = evaluate_policy_with_safety_mode(
            policy,
            shifted,
            system_config,
            policy_config,
            episode_starts=starts,
            episode_hours=episode_hours,
            safety_mode="fixed",
            fixed_layer=fixed_layer,
        )
        threshold_rows.append({"sensitivity": "distance_weight", "level": str(scale), **metrics})

    for multiplier in config["sensitivity"]["stress_load_multipliers"]:
        stressed = shifted.copy()
        stressed["electric_load_mw"] *= float(multiplier)
        stressed["heat_load_mw_th"] *= float(multiplier)
        metrics = evaluate_policy_with_safety_mode(
            policy,
            stressed,
            system_config,
            policy_config,
            episode_starts=starts,
            episode_hours=episode_hours,
            safety_mode="fixed",
            fixed_layer=FixedSafetyProjectionLayer(fixed_config()),
        )
        threshold_rows.append({"sensitivity": "load_multiplier", "level": str(multiplier), **metrics})
    sensitivity = pd.DataFrame(threshold_rows)
    sensitivity.to_csv(result_dir / "week14_sensitivity_results.csv", index=False)

    quality_rows = []
    for quality in ["expert", "mixed", "poor"]:
        transitions = load_transition_parquets([str(ROOT / p) for p in config["experiment"]["dataset_paths"][quality]])
        for seed_value in config["sensitivity"]["seeds"]:
            training = train_offline_algorithm(
                config["sensitivity"]["data_quality_algorithm"],
                transitions,
                config["training"],
                seed=int(seed_value),
            )
            metrics = evaluate_policy_with_safety_mode(
                training.policy,
                frames["in_distribution"],
                system_config,
                policy_config,
                episode_starts=starts,
                episode_hours=episode_hours,
                safety_mode="none",
            )
            quality_rows.append({"quality": quality, "seed": int(seed_value), "algorithm": config["sensitivity"]["data_quality_algorithm"], **metrics})
    quality = pd.DataFrame(quality_rows)
    quality.to_csv(result_dir / "week14_data_quality_results.csv", index=False)

    size_rows = []
    mixed_frame = pd.read_parquet(ROOT / config["experiment"]["dataset_paths"]["mixed"][0])
    for fraction in config["sensitivity"]["data_size_fractions"]:
        sampled = mixed_frame.sample(frac=float(fraction), random_state=17).reset_index(drop=True)
        transitions = load_transition_parquets([]) if False else None
        from src.offline_rl.baselines import load_transition_arrays

        training = train_offline_algorithm(
            config["sensitivity"]["data_size_algorithm"],
            load_transition_arrays(sampled),
            config["training"],
            seed=seed,
        )
        metrics = evaluate_policy_with_safety_mode(
            training.policy,
            frames["in_distribution"],
            system_config,
            policy_config,
            episode_starts=starts,
            episode_hours=episode_hours,
            safety_mode="none",
        )
        size_rows.append({"fraction": float(fraction), "algorithm": config["sensitivity"]["data_size_algorithm"], **metrics})
    size = pd.DataFrame(size_rows)
    size.to_csv(result_dir / "week14_data_size_results.csv", index=False)
    return sensitivity, quality, size


def plot_week13(summary: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    subset = summary.loc[summary["scenario"].isin(["in_distribution", "compound_extreme"])].copy()
    top_methods = [
        "perfect_information_lp",
        "rolling_mpc",
        "rule_based",
        "iql",
        "cql",
        "iql_fixed_safety",
        "iql_adaptive_safety",
        "cql_adaptive_safety",
    ]
    subset = subset.loc[subset["method"].isin(top_methods)]
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.1))
    for ax, value, title in [
        (axes[0], "mean_episode_cost_eur", "Cost"),
        (axes[1], "mean_hard_safety_cost", "Hard safety"),
        (axes[2], "mean_decision_time_ms", "Decision time"),
    ]:
        pivot = subset.pivot(index="method", columns="scenario", values=value).reindex(top_methods).dropna(how="all")
        pivot.plot(kind="bar", ax=ax)
        ax.set_title(title)
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=65)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.tight_layout()
    save_figure(fig, figure_dir / "week13_main_results")
    plt.close(fig)


def plot_week14(sensitivity: pd.DataFrame, quality: pd.DataFrame, size: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.0))
    threshold = sensitivity.loc[sensitivity["sensitivity"] == "ood_threshold"]
    axes[0].plot(threshold["level"], threshold["mean_projection_distance_l2"], marker="o", color="#335C81")
    axes[0].set_title("OOD threshold sensitivity")
    axes[0].set_ylabel("Mean L2 correction")
    q = quality.groupby("quality", as_index=False)["mean_episode_cost_eur"].mean()
    axes[1].bar(q["quality"], q["mean_episode_cost_eur"], color="#6C9A8B")
    axes[1].set_title("Dataset quality")
    axes[1].set_ylabel("Episode cost")
    axes[2].plot(size["fraction"], size["mean_episode_cost_eur"], marker="o", color="#B23A48")
    axes[2].set_title("Offline data size")
    axes[2].set_xlabel("Fraction")
    for ax in axes:
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.tight_layout()
    save_figure(fig, figure_dir / "week14_ablation_sensitivity")
    plt.close(fig)


def write_docs(summary: pd.DataFrame, manifest: pd.DataFrame, sensitivity: pd.DataFrame, quality: pd.DataFrame, size: pd.DataFrame, result_dir: Path, figure_dir: Path) -> None:
    main_table = summary.loc[
        summary["method"].isin(["perfect_information_lp", "rolling_mpc", "rule_based", "iql", "cql", "iql_fixed_safety", "iql_adaptive_safety", "cql_adaptive_safety"]),
        [
            "method",
            "scenario",
            "seeds",
            "mean_episode_cost_eur",
            "mean_hard_safety_cost",
            "mean_projection_distance_l2",
            "intervention_rate",
            "mean_decision_time_ms",
        ],
    ].copy()
    efficiency = summary.groupby("method", as_index=False).agg(
        mean_decision_time_ms=("mean_decision_time_ms", "mean"),
        mean_projection_distance_l2=("mean_projection_distance_l2", "mean"),
        intervention_rate=("intervention_rate", "mean"),
    )
    doc13 = f"""# 第13周：完整基线实验

本周运行统一预算下的主基线实验。训练预算为 {int(load_yaml(CONFIG_PATH_WEEK)['training']['steps'])} gradient steps，RL 方法使用 5 个随机种子，评估场景为 in-distribution、load-up、cold-wave extreme 和 compound extreme。

## 主结果表

{dataframe_to_markdown(main_table)}

## 计算效率表

{dataframe_to_markdown(efficiency)}

## 原始实验清单

{dataframe_to_markdown(manifest)}

结果文件：

- `{result_dir / 'week13_raw_results.csv'}`
- `{result_dir / 'week13_main_summary.csv'}`
- `{result_dir / 'week13_efficiency_table.csv'}`
- `{result_dir / 'week13_experiment_manifest.csv'}`
- `{figure_dir / 'week13_main_results.png'}`
"""
    (ROOT / "docs" / "week13_main_baselines.md").write_text(doc13, encoding="utf-8")

    ablation = summary.loc[summary["method"].str.contains("iql|cql", regex=True), [
        "method",
        "scenario",
        "mean_hard_safety_cost",
        "mean_projection_distance_l2",
        "intervention_rate",
        "mean_decision_time_ms",
    ]].copy()
    doc14 = f"""# 第14周：消融、数据质量和敏感性实验

本周围绕完整方法进行初步消融和敏感性分析：去掉 OOD 检测、去掉物理投影、固定投影替代自适应投影、OOD 只报警不控制、Expert/Mixed/Poor 数据质量比较，以及 OOD 阈值、投影权重、数据规模和压力强度敏感性。

## 消融表

{dataframe_to_markdown(ablation)}

## 敏感性结果

{dataframe_to_markdown(sensitivity[["sensitivity", "level", "mean_episode_cost_eur", "mean_episode_hard_safety_cost", "mean_projection_distance_l2", "mean_decision_time_ms"]])}

## 数据质量结果

{dataframe_to_markdown(quality[["quality", "seed", "algorithm", "mean_episode_cost_eur", "mean_episode_hard_safety_cost"]])}

## 数据规模结果

{dataframe_to_markdown(size[["fraction", "algorithm", "mean_episode_cost_eur", "mean_episode_hard_safety_cost"]])}

结果文件：

- `{result_dir / 'week14_sensitivity_results.csv'}`
- `{result_dir / 'week14_data_quality_results.csv'}`
- `{result_dir / 'week14_data_size_results.csv'}`
- `{figure_dir / 'week14_ablation_sensitivity.png'}`
"""
    (ROOT / "docs" / "week14_ablation_sensitivity.md").write_text(doc14, encoding="utf-8")
    efficiency.to_csv(result_dir / "week13_efficiency_table.csv", index=False)


def main() -> None:
    configure_style()
    config = load_yaml(CONFIG_PATH_WEEK)
    result_dir = ROOT / config["outputs"]["result_dir"]
    figure_dir = ROOT / config["outputs"]["figure_dir"]
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    results, manifest, trained = run_main_experiment(config, result_dir)
    summary = summarize_main_results(results)
    summary.to_csv(result_dir / "week13_main_summary.csv", index=False)
    plot_week13(summary, figure_dir)
    sensitivity, quality, size = run_week14_experiments(config, trained, result_dir)
    plot_week14(sensitivity, quality, size, figure_dir)
    write_docs(summary, manifest, sensitivity, quality, size, result_dir, figure_dir)
    print(summary.to_string(index=False))
    print(f"result_dir={result_dir}")
    print(f"figure_dir={figure_dir}")


if __name__ == "__main__":
    main()
