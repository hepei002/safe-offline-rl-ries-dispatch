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
from src.ood.risk import OodRiskScorer, evaluate_ood_scores
from src.offline_rl.baselines import apply_shift_scenario
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs
from src.safety.projection import evaluate_projected_actions, project_action


POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
RL_CONFIG_PATH = ROOT / "configs" / "offline_rl.yaml"
OFFLINE_DIR = ROOT / "data" / "processed" / "offline"
OUTPUT_DIR = ROOT / "results" / "risk_and_projection"
FIGURE_DIR = ROOT / "results" / "figures" / "risk_and_projection"


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
            "axes.spines.right": False,
            "axes.spines.top": False,
            "legend.frameon": False,
        }
    )


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in frame.columns
        if column.startswith("obs_") or column.startswith("action_")
    ]


def shifted_transition_copy(frame: pd.DataFrame, scenario_name: str, multiplier: float = 1.15) -> pd.DataFrame:
    shifted = frame.copy()
    shifted["scenario"] = scenario_name
    if scenario_name == "load_up":
        for column in ["obs_electric_load_norm", "obs_heat_load_norm", "next_obs_electric_load_norm", "next_obs_heat_load_norm"]:
            if column in shifted.columns:
                shifted[column] = shifted[column] * multiplier
        shifted["hard_safety_cost"] = shifted["hard_safety_cost"] * multiplier + (
            shifted["obs_electric_load_norm"].clip(lower=1.0) - 1.0
        ) * 5.0
    elif scenario_name == "efficiency_drop":
        for column in ["obs_cop_norm", "next_obs_cop_norm"]:
            if column in shifted.columns:
                shifted[column] = shifted[column] * 0.85
        shifted["hard_safety_cost"] = shifted["hard_safety_cost"] * 1.25
    elif scenario_name == "price_spike":
        shifted["hard_safety_cost"] = shifted["hard_safety_cost"]
    return shifted


def run_ood_check() -> pd.DataFrame:
    expert = pd.read_parquet(OFFLINE_DIR / "expert.parquet")
    mixed = pd.read_parquet(OFFLINE_DIR / "mixed.parquet")
    poor = pd.read_parquet(OFFLINE_DIR / "poor.parquet")
    for name, frame in [("expert", expert), ("mixed", mixed), ("poor", poor)]:
        frame["scenario"] = name
    reference = expert.loc[expert["hard_safety_cost"] <= 1e-9, feature_columns(expert)]
    if reference.empty:
        reference = expert[feature_columns(expert)]
    evaluation = pd.concat(
        [
            expert,
            mixed,
            poor,
            shifted_transition_copy(mixed, "load_up"),
            shifted_transition_copy(mixed, "efficiency_drop"),
        ],
        ignore_index=True,
    )
    rows = []
    for method in ["mahalanobis", "knn"]:
        scorer = OodRiskScorer(method=method, n_neighbors=10).fit(reference.to_numpy())
        scores = scorer.score(evaluation[feature_columns(evaluation)].to_numpy())
        evaluation[f"{method}_score"] = scores
        for scenario, group in evaluation.groupby("scenario"):
            metrics = evaluate_ood_scores(
                group[f"{method}_score"].to_numpy(),
                group["hard_safety_cost"].to_numpy(),
            )
            rows.append({"method": method, "scenario": scenario, **metrics})
    evaluation.to_parquet(OUTPUT_DIR / "ood_scored_transitions.parquet", index=False)
    return pd.DataFrame(rows)


def run_projection_check() -> pd.DataFrame:
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    rl_config = load_yaml(RL_CONFIG_PATH)
    eval_config = rl_config["evaluation"]
    start = pd.Timestamp(eval_config["start_utc"]).tz_convert("UTC")
    episode_hours = int(eval_config["episode_hours"])
    episodes = 6
    stride = int(eval_config["stride_hours"])
    base_frame = frame.loc[start : start + pd.Timedelta(hours=(episodes - 1) * stride + episode_hours - 1)].copy()
    scenarios = {
        "in_distribution": {"type": "in_distribution"},
        "load_up": {"type": "load_up", "multiplier": 1.15},
        "efficiency_drop": {"type": "efficiency_drop", "cop_multiplier": 0.85, "chp_efficiency_multiplier": 0.90},
    }
    rows = []
    unsafe_action = np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32)
    for scenario_name, scenario in scenarios.items():
        shifted_frame, shifted_cost = apply_shift_scenario(base_frame, policy_config, scenario)
        for episode in range(episodes):
            start_index = episode * stride
            env = IntegratedEnergyEnv(
                shifted_frame,
                system_config,
                shifted_cost,
                episode_hours=episode_hours,
                start_index=start_index,
            )
            metrics = evaluate_projected_actions(env, [unsafe_action] * episode_hours)
            rows.append({"scenario": scenario_name, "episode": episode, **metrics})
    return pd.DataFrame(rows)


def plot_outputs(ood: pd.DataFrame, projection: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    subset = ood.loc[ood["method"] == "mahalanobis"]
    axes[0].bar(subset["scenario"], subset["auroc"], color="#335C81")
    axes[0].set_ylim(0.0, 1.0)
    axes[0].set_ylabel("AUROC for hard safety risk")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].set_title("OOD score predicts hard-safety risk")
    projection_summary = projection.groupby("scenario", as_index=False)[
        ["raw_hard_safety_cost", "projected_hard_safety_cost"]
    ].mean()
    x = np.arange(len(projection_summary))
    axes[1].bar(x - 0.18, projection_summary["raw_hard_safety_cost"], width=0.36, label="Raw", color="#B23A48")
    axes[1].bar(x + 0.18, projection_summary["projected_hard_safety_cost"], width=0.36, label="Projected", color="#6C9A8B")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(projection_summary["scenario"], rotation=25)
    axes[1].set_ylabel("Episode hard safety cost")
    axes[1].set_title("Projection reduces hard violations")
    axes[1].legend()
    for ax in axes:
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.tight_layout()
    save_figure(fig, FIGURE_DIR / "ood_projection_summary")
    plt.close(fig)


def main() -> None:
    configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ood = run_ood_check()
    projection = run_projection_check()
    ood.to_csv(OUTPUT_DIR / "ood_risk_summary.csv", index=False)
    projection.to_csv(OUTPUT_DIR / "projection_summary.csv", index=False)
    plot_outputs(ood, projection)
    print(ood.to_string(index=False))
    print(projection.groupby("scenario")[["raw_hard_safety_cost", "projected_hard_safety_cost", "mean_projection_distance_l2"]].mean().to_string())
    print(f"output_dir={OUTPUT_DIR}")
    print(f"figure_dir={FIGURE_DIR}")


if __name__ == "__main__":
    main()
