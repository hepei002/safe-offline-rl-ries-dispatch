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

from src.offline_rl.baselines import (
    apply_shift_scenario,
    load_transition_parquets,
    train_offline_algorithm,
)
from src.offline_rl.evaluation import evaluate_policy_on_frame, evaluate_rule_policy_on_frame
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs


CONFIG_PATH_RL = ROOT / "configs" / "offline_rl.yaml"
POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"

PALETTE = {
    "bc": "#335C81",
    "td3_bc": "#6C9A8B",
    "cql": "#E3A62F",
    "iql": "#B23A48",
    "rule_based": "#7A7A7A",
}


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
    needed = (episodes - 1) * stride + episode_hours
    selected = frame.loc[start : start + pd.Timedelta(hours=needed - 1)].copy()
    starts = [i * stride for i in range(episodes)]
    return selected, starts


def summarize_results(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(["algorithm", "scenario"], as_index=False)
    return grouped.agg(
        mean_episode_cost_eur=("mean_episode_cost_eur", "mean"),
        std_episode_cost_eur=("mean_episode_cost_eur", "std"),
        cvar90_episode_cost_eur=("cvar90_episode_cost_eur", "mean"),
        mean_episode_safety_cost=("mean_episode_safety_cost", "mean"),
        mean_episode_hard_safety_cost=("mean_episode_hard_safety_cost", "mean"),
        unsafe_episode_rate=("unsafe_episode_rate", "mean"),
        mean_decision_time_ms=("mean_decision_time_ms", "mean"),
    )


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.10, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")


def plot_learning_curves(curves: pd.DataFrame, figure_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for algorithm, group in curves.groupby("algorithm"):
        plotted = group.groupby("step", as_index=False)["actor_loss"].mean()
        axes[0].plot(plotted["step"], plotted["actor_loss"], label=algorithm, color=PALETTE.get(algorithm), lw=1.5)
        critic = group.groupby("step", as_index=False)["critic_loss"].mean()
        axes[1].plot(critic["step"], critic["critic_loss"], label=algorithm, color=PALETTE.get(algorithm), lw=1.5)
    axes[0].set_title("Actor / policy loss")
    axes[1].set_title("Critic / value loss")
    axes[0].set_xlabel("Gradient step")
    axes[1].set_xlabel("Gradient step")
    axes[0].set_ylabel("Loss")
    axes[1].set_ylabel("Loss")
    for ax, label in zip(axes, ["a", "b"]):
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
        ax.legend()
        panel_label(ax, label)
    fig.suptitle("Offline RL baseline training curves across three seeds", fontsize=9, y=1.02)
    fig.tight_layout()
    save_figure(fig, figure_dir / "learning_curves")
    plt.close(fig)


def plot_seed_stability(results: pd.DataFrame, figure_dir: Path) -> None:
    subset = results.loc[results["scenario"] == "in_distribution"].copy()
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    algorithms = sorted(subset["algorithm"].unique())
    values = [subset.loc[subset["algorithm"] == alg, "mean_episode_cost_eur"].to_numpy() for alg in algorithms]
    ax.boxplot(values, labels=algorithms, patch_artist=True, boxprops={"facecolor": "#D9E4EC"})
    ax.set_ylabel("Mean episode cost (€)")
    ax.set_title("Seed stability under in-distribution evaluation")
    ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.tight_layout()
    save_figure(fig, figure_dir / "seed_stability")
    plt.close(fig)


def plot_shift_comparison(summary: pd.DataFrame, figure_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    pivot_cost = summary.pivot(index="scenario", columns="algorithm", values="mean_episode_cost_eur")
    pivot_safety = summary.pivot(index="scenario", columns="algorithm", values="mean_episode_safety_cost")
    pivot_cost.plot(kind="bar", ax=axes[0], color=[PALETTE.get(col) for col in pivot_cost.columns])
    pivot_safety.plot(kind="bar", ax=axes[1], color=[PALETTE.get(col) for col in pivot_safety.columns])
    axes[0].set_ylabel("Mean episode cost (€)")
    axes[1].set_ylabel("Mean episode safety cost")
    axes[0].set_title("Cost under ID and shift scenarios")
    axes[1].set_title("Safety degradation under shifts")
    for ax, label in zip(axes, ["a", "b"]):
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=25)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
        panel_label(ax, label)
    fig.tight_layout()
    save_figure(fig, figure_dir / "id_vs_shift_comparison")
    plt.close(fig)


def go_no_go(summary: pd.DataFrame) -> str:
    id_summary = summary.loc[summary["scenario"] == "in_distribution"].set_index("algorithm")
    bc_cost = float(id_summary.loc["bc", "mean_episode_cost_eur"])
    best_algorithm = id_summary["mean_episode_cost_eur"].idxmin()
    best_cost = float(id_summary.loc[best_algorithm, "mean_episode_cost_eur"])
    shift_summary = summary.loc[summary["scenario"] != "in_distribution"].copy()
    id_safety = id_summary["mean_episode_safety_cost"]
    safety_degradation = False
    for _, row in shift_summary.iterrows():
        base = float(id_safety.loc[row["algorithm"]])
        if float(row["mean_episode_safety_cost"]) > base * 1.10 + 1e-6:
            safety_degradation = True
            break
    if "rule_based" in id_summary.index and best_algorithm != "rule_based":
        rule_cost = float(id_summary.loc["rule_based", "mean_episode_cost_eur"])
        if best_cost < min(bc_cost, rule_cost) * 0.98 and safety_degradation:
            return "Go: at least one offline RL method improves over BC/rule in-distribution, and shift scenarios measurably worsen safety."
    if best_algorithm != "bc" and best_cost < bc_cost * 0.98 and safety_degradation:
        return "Conditional Go: offline RL improves over BC and shifts measurably worsen safety, but it has not yet beaten the rule controller; continue OOD work while treating rule control as a strong baseline."
    if safety_degradation:
        return "Pivot B: shifts create measurable degradation, but offline RL has not yet clearly beaten BC; emphasize fast policy approximation or tune algorithms/data."
    return "Pivot A/No-Go: current shifts do not yet create meaningful safety degradation; strengthen drift protocol before adding OOD modules."


def main() -> None:
    configure_style()
    rl_config = load_yaml(CONFIG_PATH_RL)
    cost_config = load_yaml(POLICY_CONFIG_PATH)
    result_dir = ROOT / rl_config["outputs"]["result_dir"]
    figure_dir = ROOT / rl_config["outputs"]["figure_dir"]
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    result_path = result_dir / "offline_rl_seed_results.csv"
    curve_path = result_dir / "offline_rl_learning_curves.csv"
    summary_path = result_dir / "offline_rl_baseline_summary.csv"
    if result_path.exists() and curve_path.exists() and summary_path.exists():
        result_frame = pd.read_csv(result_path)
        curve_frame = pd.read_csv(curve_path)
        summary = pd.read_csv(summary_path)
        decision = go_no_go(summary)
        (result_dir / "go_no_go.txt").write_text(decision, encoding="utf-8")
        plot_learning_curves(curve_frame, figure_dir)
        plot_seed_stability(result_frame, figure_dir)
        plot_shift_comparison(summary, figure_dir)
        print(summary.to_string(index=False))
        print(decision)
        print(f"result_dir={result_dir}")
        print(f"figure_dir={figure_dir}")
        return

    dataset_paths = [str(ROOT / path) for path in rl_config["experiment"]["dataset_paths"]]
    transitions = load_transition_parquets(dataset_paths)
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    eval_frame, starts = select_evaluation_frame(frame, rl_config)

    results: list[dict[str, float | str | int]] = []
    curves: list[dict[str, float | str | int]] = []
    for algorithm in rl_config["experiment"]["algorithms"]:
        for seed in rl_config["experiment"]["seeds"]:
            training = train_offline_algorithm(
                algorithm,
                transitions,
                rl_config["training"],
                seed=int(seed),
            )
            for step, (actor_loss, critic_loss) in enumerate(
                zip(training.learning_curve["actor_loss"], training.learning_curve["critic_loss"])
            ):
                curves.append(
                    {
                        "algorithm": algorithm,
                        "seed": int(seed),
                        "step": step,
                        "actor_loss": actor_loss,
                        "critic_loss": critic_loss,
                    }
                )
            for scenario_name, scenario in rl_config["evaluation"]["scenarios"].items():
                shifted_frame, shifted_cost = apply_shift_scenario(eval_frame, cost_config, scenario)
                metrics = evaluate_policy_on_frame(
                    training.policy,
                    shifted_frame,
                    system_config,
                    shifted_cost,
                    episode_starts=starts,
                    episode_hours=int(rl_config["evaluation"]["episode_hours"]),
                )
                results.append(
                    {
                        "algorithm": algorithm,
                        "seed": int(seed),
                        "scenario": scenario_name,
                        **metrics,
                    }
                )

    for scenario_name, scenario in rl_config["evaluation"]["scenarios"].items():
        shifted_frame, shifted_cost = apply_shift_scenario(eval_frame, cost_config, scenario)
        metrics = evaluate_rule_policy_on_frame(
            shifted_frame,
            system_config,
            shifted_cost,
            episode_starts=starts,
            episode_hours=int(rl_config["evaluation"]["episode_hours"]),
        )
        results.append(
            {
                "algorithm": "rule_based",
                "seed": -1,
                "scenario": scenario_name,
                **metrics,
            }
        )

    result_frame = pd.DataFrame(results)
    curve_frame = pd.DataFrame(curves)
    summary = summarize_results(result_frame)
    result_frame.to_csv(result_path, index=False)
    curve_frame.to_csv(curve_path, index=False)
    summary.to_csv(summary_path, index=False)
    decision = go_no_go(summary)
    (result_dir / "go_no_go.txt").write_text(decision, encoding="utf-8")
    plot_learning_curves(curve_frame, figure_dir)
    plot_seed_stability(result_frame, figure_dir)
    plot_shift_comparison(summary, figure_dir)
    print(summary.to_string(index=False))
    print(decision)
    print(f"result_dir={result_dir}")
    print(f"figure_dir={figure_dir}")


if __name__ == "__main__":
    main()
