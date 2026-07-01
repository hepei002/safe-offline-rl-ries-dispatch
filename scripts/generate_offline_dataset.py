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

from src.offline.dataset import generate_offline_datasets, summarize_dataset_quality
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs


POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
DATASET_CONFIG_PATH = ROOT / "configs" / "offline_dataset.yaml"
FIGURE_DIR = ROOT / "results" / "figures" / "offline_dataset"

PALETTE = {
    "expert": "#335C81",
    "mixed": "#E3A62F",
    "poor": "#B23A48",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def select_source_frame(frame: pd.DataFrame, dataset_config: dict) -> pd.DataFrame:
    source = dataset_config["dataset"]["source_period"]
    start = pd.Timestamp(source["start_utc"])
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    else:
        start = start.tz_convert("UTC")
    episodes = int(source["episodes"])
    episode_hours = int(source["episode_hours"])
    lookahead_hours = int(source["lookahead_hours"])
    needed_hours = episodes * episode_hours + lookahead_hours
    return frame.loc[start : start + pd.Timedelta(hours=needed_hours - 1)].copy()


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


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.10, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")


def plot_dataset_coverage(datasets: dict[str, pd.DataFrame], summary: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    qualities = list(datasets.keys())
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))

    ax = axes[0, 0]
    action_column = "action_chp_electric_fraction"
    ax.boxplot(
        [datasets[q][action_column].to_numpy() for q in qualities],
        labels=qualities,
        patch_artist=True,
        boxprops={"facecolor": "#D9E4EC", "color": "#4A4A4A"},
        medianprops={"color": "#252525"},
    )
    ax.set_ylabel("CHP action")
    ax.set_title("Action support differs by quality")
    panel_label(ax, "a")

    ax = axes[0, 1]
    returns = [datasets[q].groupby("episode_id")["reward"].sum().to_numpy() for q in qualities]
    ax.boxplot(
        returns,
        labels=qualities,
        patch_artist=True,
        boxprops={"facecolor": "#F3DFA2", "color": "#4A4A4A"},
        medianprops={"color": "#252525"},
    )
    ax.set_ylabel("Episode return")
    ax.set_title("Return quality separates expert/mixed/poor")
    panel_label(ax, "b")

    ax = axes[1, 0]
    for quality in qualities:
        safety = datasets[quality].groupby("episode_id")["safety_cost"].sum()
        ax.hist(
            safety,
            bins=20,
            alpha=0.55,
            color=PALETTE.get(quality),
            label=quality,
        )
    ax.set_xlabel("Episode safety cost")
    ax.set_ylabel("Episodes")
    ax.legend()
    panel_label(ax, "c")

    ax = axes[1, 1]
    x = np.arange(len(qualities))
    summary = summary.set_index("quality").loc[qualities]
    ax.bar(
        x - 0.18,
        summary["state_coverage_score"],
        width=0.36,
        color="#8FB3C8",
        label="State coverage",
    )
    ax.bar(
        x + 0.18,
        summary["action_coverage_score"],
        width=0.36,
        color="#C95D4B",
        label="Action coverage",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(qualities)
    ax.set_ylabel("Mean normalized std.")
    ax.legend()
    panel_label(ax, "d")

    for ax in axes.flat:
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    fig.suptitle("Offline dataset quality is separated by action coverage, return and safety cost", fontsize=9, y=1.01)
    fig.tight_layout()
    save_figure(fig, FIGURE_DIR / "offline_dataset_coverage")
    plt.close(fig)


def write_metadata(output_dir: Path, dataset_config: dict, summary: pd.DataFrame) -> None:
    metadata = {
        "name": dataset_config["dataset"]["name"],
        "format": dataset_config["dataset"]["format"],
        "source_period": dataset_config["dataset"]["source_period"],
        "files": {
            quality: f"{quality}.parquet"
            for quality in summary["quality"].tolist()
        },
        "summary": summary.to_dict(orient="records"),
    }
    (output_dir / "metadata.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def main() -> None:
    configure_style()
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    raw_dataset_config = load_yaml(DATASET_CONFIG_PATH)
    dataset_config = raw_dataset_config["dataset"]
    output_dir = ROOT / dataset_config["output_dir"]
    source_frame = select_source_frame(frame, raw_dataset_config)
    datasets = generate_offline_datasets(
        source_frame,
        system_config,
        policy_config,
        dataset_config,
        output_dir,
    )
    summary = summarize_dataset_quality(datasets)
    summary.to_csv(output_dir / "dataset_quality_summary.csv", index=False)
    plot_dataset_coverage(datasets, summary)
    write_metadata(output_dir, raw_dataset_config, summary)
    print(summary.to_string(index=False))
    print(f"output_dir={output_dir}")
    print(f"figure_dir={FIGURE_DIR}")


if __name__ == "__main__":
    main()

