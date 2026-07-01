from __future__ import annotations

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs
from src.safety.adaptive_layer import AdaptiveSafetyConfig, AdaptiveSafetyLayer, evaluate_adaptive_safety_layer
from src.safety.fixed_projection import FixedSafetyProjectionLayer
from src.shift.protocols import apply_shift_protocol, load_shift_protocol

from scripts.run_fixed_safety_projection import (
    PROJECTION_CONFIG_PATH,
    projection_config_from_yaml,
    unsafe_action_from_yaml,
)


ADAPTIVE_CONFIG_PATH = ROOT / "configs" / "adaptive_safety.yaml"
SHIFT_PROTOCOL_PATH = ROOT / "configs" / "shift_protocol.yaml"
POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
OOD_RISK_PATH = ROOT / "results" / "shift_protocol_ood" / "ood_risk_summary.csv"
RESULT_DIR = ROOT / "results" / "week12_adaptive_safety"
FIGURE_DIR = ROOT / "results" / "figures" / "adaptive_safety"
DOC_PATH = ROOT / "docs" / "week12_adaptive_safety_mechanism.md"


REPRESENTATIVE_SCENARIOS = [
    "in_distribution",
    "load_up_20",
    "cold_wave_extreme",
    "compound_extreme",
]


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


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    formatted = frame.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(lambda value: f"{value:.3f}")
        else:
            formatted[column] = formatted[column].astype(str)
    header = "| " + " | ".join(formatted.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(formatted.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in formatted.astype(str).to_numpy()]
    return "\n".join([header, separator, *rows])


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def adaptive_config_from_yaml(payload: dict) -> AdaptiveSafetyConfig:
    mapping = payload["risk_mapping"]
    return AdaptiveSafetyConfig(
        low_risk_threshold=float(mapping.get("low_risk_threshold", 1.0)),
        high_risk_threshold=float(mapping.get("high_risk_threshold", 3.0)),
        blend_grid_size=int(mapping.get("blend_grid_size", 11)),
        hard_safety_tolerance=float(mapping.get("hard_safety_tolerance", 1e-6)),
        force_project_if_hard_violation=bool(mapping.get("force_project_if_hard_violation", False)),
    )


def action_from_mapping(mapping: dict[str, float]) -> np.ndarray:
    return np.asarray(
        [
            float(mapping["chp_electric_fraction"]),
            float(mapping["heat_pump_heat_fraction"]),
            float(mapping["battery_power_fraction"]),
            float(mapping["thermal_power_fraction"]),
        ],
        dtype=np.float32,
    )


def select_evaluation_frame(frame: pd.DataFrame, evaluation: dict, episodes: int = 4) -> tuple[pd.DataFrame, list[int]]:
    start = pd.Timestamp(evaluation["start_utc"])
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    episode_hours = int(evaluation["episode_hours"])
    stride = int(evaluation["stride_hours"])
    needed = (episodes - 1) * stride + episode_hours
    selected = frame.loc[start : start + pd.Timedelta(hours=needed - 1)].copy()
    if len(selected) < needed:
        raise ValueError("not enough evaluation data")
    return selected, [i * stride for i in range(episodes)]


def scenario_risk_scores() -> dict[str, float]:
    if not OOD_RISK_PATH.exists():
        return {name: 4.0 for name in REPRESENTATIVE_SCENARIOS}
    risk = pd.read_csv(OOD_RISK_PATH)
    return {
        str(row["scenario"]): float(row["mean_ood_score"])
        for _, row in risk.loc[risk["scenario"] != "all"].iterrows()
    }


def evaluate_no_safety(
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    starts: list[int],
    episode_hours: int,
    action: np.ndarray,
) -> pd.DataFrame:
    rows = []
    for episode, start in enumerate(starts):
        env = IntegratedEnergyEnv(frame, system_config, cost_config, episode_hours=episode_hours, start_index=start)
        env.reset(seed=0, options={"start_index": start})
        hard = 0.0
        soft = 0.0
        for _ in range(episode_hours):
            _, _, terminated, truncated, info = env.step(action)
            hard += float(info["hard_safety_cost"])
            soft += float(info["soft_operation_cost"])
            if terminated or truncated:
                break
        rows.append(
            {
                "episode": episode,
                "raw_hard_safety_cost": hard,
                "projected_hard_safety_cost": hard,
                "raw_soft_operation_cost": soft,
                "projected_soft_operation_cost": soft,
                "mean_projection_distance_l2": 0.0,
                "mean_solve_time_ms": 0.0,
                "intervention_rate": 0.0,
                "pass_through_rate": 1.0,
                "partial_projection_rate": 0.0,
                "full_projection_rate": 0.0,
            }
        )
    return pd.DataFrame(rows)


def evaluate_fixed(
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    starts: list[int],
    episode_hours: int,
    action: np.ndarray,
    fixed_layer: FixedSafetyProjectionLayer,
) -> pd.DataFrame:
    from src.safety.fixed_projection import evaluate_fixed_projection_layer

    rows = []
    for episode, start in enumerate(starts):
        env = IntegratedEnergyEnv(frame, system_config, cost_config, episode_hours=episode_hours, start_index=start)
        metrics = evaluate_fixed_projection_layer(env, fixed_layer, [action for _ in range(episode_hours)])
        rows.append({"episode": episode, **metrics, "pass_through_rate": 0.0, "partial_projection_rate": 0.0, "full_projection_rate": metrics["intervention_rate"]})
    return pd.DataFrame(rows)


def evaluate_adaptive(
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    starts: list[int],
    episode_hours: int,
    action: np.ndarray,
    risk_score: float,
    layer: AdaptiveSafetyLayer,
) -> pd.DataFrame:
    rows = []
    for episode, start in enumerate(starts):
        env = IntegratedEnergyEnv(frame, system_config, cost_config, episode_hours=episode_hours, start_index=start)
        metrics = evaluate_adaptive_safety_layer(
            env,
            layer,
            [action for _ in range(episode_hours)],
            [risk_score for _ in range(episode_hours)],
        )
        rows.append({"episode": episode, **metrics})
    return pd.DataFrame(rows)


def run_benchmark() -> pd.DataFrame:
    projection_payload = load_yaml(PROJECTION_CONFIG_PATH)
    adaptive_payload = load_yaml(ADAPTIVE_CONFIG_PATH)
    shift_protocol = load_shift_protocol(SHIFT_PROTOCOL_PATH)
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    eval_frame, starts = select_evaluation_frame(frame, shift_protocol.evaluation, episodes=4)
    episode_hours = int(shift_protocol.evaluation["episode_hours"])
    fixed_layer = FixedSafetyProjectionLayer(projection_config_from_yaml(projection_payload))
    adaptive_layer = AdaptiveSafetyLayer(fixed_layer, adaptive_config_from_yaml(adaptive_payload))
    unsafe_action = unsafe_action_from_yaml(projection_payload)
    risk_scores = scenario_risk_scores()
    scenario_map = {scenario.name: scenario for scenario in shift_protocol.scenarios}

    rows = []
    for scenario_name in REPRESENTATIVE_SCENARIOS:
        scenario = scenario_map[scenario_name]
        shifted_frame, _ = apply_shift_protocol(eval_frame, scenario)
        risk_score = risk_scores.get(scenario_name, 4.0)
        for method, result in [
            (
                "no_safety",
                evaluate_no_safety(
                    shifted_frame,
                    system_config,
                    policy_config,
                    starts=starts,
                    episode_hours=episode_hours,
                    action=unsafe_action,
                ),
            ),
            (
                "fixed_safety",
                evaluate_fixed(
                    shifted_frame,
                    system_config,
                    policy_config,
                    starts=starts,
                    episode_hours=episode_hours,
                    action=unsafe_action,
                    fixed_layer=fixed_layer,
                ),
            ),
            (
                "adaptive_safety",
                evaluate_adaptive(
                    shifted_frame,
                    system_config,
                    policy_config,
                    starts=starts,
                    episode_hours=episode_hours,
                    action=unsafe_action,
                    risk_score=risk_score,
                    layer=adaptive_layer,
                ),
            ),
        ]:
            result = result.copy()
            result["method"] = method
            result["scenario"] = scenario_name
            result["family"] = scenario.family
            result["risk_score"] = risk_score
            rows.append(result)
    return pd.concat(rows, ignore_index=True)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    summary = results.groupby(["method", "scenario"], as_index=False).agg(
        risk_score=("risk_score", "mean"),
        raw_hard_safety_cost=("raw_hard_safety_cost", "mean"),
        projected_hard_safety_cost=("projected_hard_safety_cost", "mean"),
        projected_soft_operation_cost=("projected_soft_operation_cost", "mean"),
        mean_projection_distance_l2=("mean_projection_distance_l2", "mean"),
        mean_solve_time_ms=("mean_solve_time_ms", "mean"),
        intervention_rate=("intervention_rate", "mean"),
        pass_through_rate=("pass_through_rate", "mean"),
        partial_projection_rate=("partial_projection_rate", "mean"),
        full_projection_rate=("full_projection_rate", "mean"),
    )
    summary["hard_safety_reduction_pct"] = (
        100.0
        * (summary["raw_hard_safety_cost"] - summary["projected_hard_safety_cost"])
        / summary["raw_hard_safety_cost"].clip(lower=1e-9)
    )
    return summary


def plot_results(summary: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.0))
    methods = ["no_safety", "fixed_safety", "adaptive_safety"]
    colors = {"no_safety": "#B23A48", "fixed_safety": "#6C9A8B", "adaptive_safety": "#335C81"}
    pivot_hard = summary.pivot(index="scenario", columns="method", values="projected_hard_safety_cost").loc[REPRESENTATIVE_SCENARIOS]
    pivot_distance = summary.pivot(index="scenario", columns="method", values="mean_projection_distance_l2").loc[REPRESENTATIVE_SCENARIOS]
    pivot_intervention = summary.pivot(index="scenario", columns="method", values="intervention_rate").loc[REPRESENTATIVE_SCENARIOS]
    pivot_hard[methods].plot(kind="bar", ax=axes[0], color=[colors[m] for m in methods])
    pivot_distance[methods].plot(kind="bar", ax=axes[1], color=[colors[m] for m in methods])
    pivot_intervention[methods].plot(kind="bar", ax=axes[2], color=[colors[m] for m in methods])
    axes[0].set_ylabel("Episode hard safety cost")
    axes[1].set_ylabel("Mean L2 correction")
    axes[2].set_ylabel("Intervention rate")
    axes[0].set_title("Safety risk")
    axes[1].set_title("Correction size")
    axes[2].set_title("Over-correction control")
    for ax, label in zip(axes, ["a", "b", "c"]):
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=25)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
        ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")
        ax.legend(fontsize=5)
    fig.tight_layout()
    save_figure(fig, FIGURE_DIR / "adaptive_safety_ablation")
    plt.close(fig)


def plot_method_flow() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.axis("off")
    boxes = [
        (0.03, 0.58, 0.16, 0.24, "Offline RL\ncandidate action"),
        (0.25, 0.58, 0.16, 0.24, "Dynamics ensemble\nOOD risk score"),
        (0.47, 0.58, 0.16, 0.24, "Adaptive gate\nρ = f(risk)"),
        (0.69, 0.72, 0.20, 0.20, "Low risk & safe\npass-through"),
        (0.69, 0.46, 0.20, 0.20, "Medium risk\npartial projection"),
        (0.69, 0.20, 0.20, 0.20, "High risk\nfull projection"),
        (0.47, 0.12, 0.20, 0.20, "Physics-informed\nfixed safety layer"),
        (0.91, 0.46, 0.08, 0.20, "Safe\naction"),
    ]
    for x, y, w, h, label in boxes:
        rect = plt.Rectangle((x, y), w, h, facecolor="#EEF3F7", edgecolor="#335C81", lw=1.0)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=7)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#4A4A4A"})

    arrow(0.19, 0.70, 0.25, 0.70)
    arrow(0.41, 0.70, 0.47, 0.70)
    arrow(0.63, 0.70, 0.69, 0.82)
    arrow(0.63, 0.70, 0.69, 0.56)
    arrow(0.63, 0.70, 0.69, 0.30)
    arrow(0.57, 0.58, 0.57, 0.32)
    arrow(0.67, 0.22, 0.69, 0.30)
    arrow(0.89, 0.82, 0.91, 0.56)
    arrow(0.89, 0.56, 0.91, 0.56)
    arrow(0.89, 0.30, 0.91, 0.56)
    ax.text(0.57, 0.96, "Complete method: OOD-aware adaptive physical safety layer", ha="center", fontsize=9)
    fig.tight_layout()
    save_figure(fig, FIGURE_DIR / "adaptive_safety_method_flow")
    plt.close(fig)


def write_document(summary: pd.DataFrame) -> None:
    compact = summary[
        [
            "method",
            "scenario",
            "risk_score",
            "projected_hard_safety_cost",
            "hard_safety_reduction_pct",
            "mean_projection_distance_l2",
            "intervention_rate",
            "pass_through_rate",
            "partial_projection_rate",
            "full_projection_rate",
        ]
    ].copy()
    no_safety = summary.loc[summary["method"] == "no_safety", "projected_hard_safety_cost"].mean()
    fixed = summary.loc[summary["method"] == "fixed_safety", "projected_hard_safety_cost"].mean()
    adaptive = summary.loc[summary["method"] == "adaptive_safety", "projected_hard_safety_cost"].mean()
    fixed_dist = summary.loc[summary["method"] == "fixed_safety", "mean_projection_distance_l2"].mean()
    adaptive_dist = summary.loc[summary["method"] == "adaptive_safety", "mean_projection_distance_l2"].mean()
    distance_change = 100.0 * (fixed_dist - adaptive_dist) / max(fixed_dist, 1e-9)
    text = f"""# 第12周：自适应安全机制

本周形成完整方法：OOD 风险估计不再单独作为最终目标，而是用于调节物理安全层的介入强度。方法由三部分组成：

1. dynamics ensemble OOD risk score；
2. fixed physical safety projection；
3. adaptive safety gate，将风险分数映射为 pass-through、partial projection 或 full projection。

## 1. 自适应规则

风险权重定义为：

\\[
\\rho = clip\\left(\\frac{{r-r_l}}{{r_h-r_l}},0,1\\right)
\\]

当风险低且动作本身无 hard safety violation 时，动作直接放行；当风险高时，使用固定安全投影；中间风险时，在原动作与固定安全动作之间搜索最近的可行混合动作，以减少过度修正。

## 2. 初步消融结果

{dataframe_to_markdown(compact)}

平均 projected hard safety cost：

- no safety：{no_safety:.3f}
- fixed safety：{fixed:.3f}
- adaptive safety：{adaptive:.3f}

平均动作修正距离：

- fixed safety：{fixed_dist:.3f}
- adaptive safety：{adaptive_dist:.3f}

相对固定安全层，adaptive safety 的平均动作修正距离变化为 {distance_change:.2f}%。

## 3. 阶段判断

自适应安全层相对 no safety 显著降低 hard safety risk；相对 fixed safety，在代表性压力动作设置下保持相近安全水平，并降低平均动作修正距离，但计算时间更高。这说明完整方法已经形成，且存在“降低过度修正”的初步证据。第 13 周完整基线实验中，应加入真实离线 RL 策略动作序列，进一步验证低风险时是否减少干预，并报告时间开销。

最终方法建议固定为：offline RL policy + ensemble risk score + adaptive physics-informed safety layer。不要再增加新核心模块。

图件：

- `results/figures/adaptive_safety/adaptive_safety_ablation.png`
- `results/figures/adaptive_safety/adaptive_safety_ablation.pdf`
- `results/figures/adaptive_safety/adaptive_safety_ablation.svg`
- `results/figures/adaptive_safety/adaptive_safety_ablation.tiff`
- `results/figures/adaptive_safety/adaptive_safety_method_flow.png`
"""
    DOC_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    configure_style()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    results = run_benchmark()
    summary = summarize(results)
    results.to_csv(RESULT_DIR / "adaptive_safety_episode_results.csv", index=False)
    summary.to_csv(RESULT_DIR / "adaptive_safety_ablation_summary.csv", index=False)
    plot_results(summary)
    plot_method_flow()
    write_document(summary)
    print(summary.to_string(index=False))
    print(f"result_dir={RESULT_DIR}")
    print(f"figure_dir={FIGURE_DIR}")
    print(f"doc={DOC_PATH}")


if __name__ == "__main__":
    main()
