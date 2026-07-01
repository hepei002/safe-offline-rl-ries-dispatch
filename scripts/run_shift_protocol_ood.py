from __future__ import annotations

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ood.ensemble import DynamicsEnsembleRiskEstimator, evaluate_ensemble_risk_by_scenario
from src.offline.dataset import build_transition_frame
from src.optimization.deterministic_dispatch import CONFIG_PATH, load_dispatch_inputs
from src.policies.rule_based import run_rule_based_policy
from src.shift.protocols import apply_shift_protocol, load_shift_protocol, summarize_shift_protocol


PROTOCOL_PATH = ROOT / "configs" / "shift_protocol.yaml"
POLICY_CONFIG_PATH = ROOT / "configs" / "behavior_policies.yaml"
RESULT_DIR = ROOT / "results" / "shift_protocol_ood"
FIGURE_DIR = ROOT / "results" / "figures" / "shift_protocol_ood"
DOC_PATH = ROOT / "docs" / "shift_and_ood_protocol.md"


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


def select_evaluation_frame(frame: pd.DataFrame, evaluation: dict) -> tuple[pd.DataFrame, list[int]]:
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
    if len(selected) < needed:
        raise ValueError("not enough evaluation data for configured shift protocol period")
    return selected, [i * stride for i in range(episodes)]


def generate_shift_transitions(
    frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    protocol,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eval_frame, starts = select_evaluation_frame(frame, protocol.evaluation)
    episode_hours = int(protocol.evaluation["episode_hours"])
    shift_summary = summarize_shift_protocol(eval_frame, protocol.scenarios)
    transitions = []
    for scenario in protocol.scenarios:
        shifted_frame, _ = apply_shift_protocol(eval_frame, scenario)
        for episode, start in enumerate(starts):
            episode_frame = shifted_frame.iloc[start : start + episode_hours].copy()
            dispatch = run_rule_based_policy(episode_frame, system_config, policy_config)
            transition = build_transition_frame(
                episode_frame,
                dispatch,
                system_config,
                policy_config,
                quality="shift_eval",
                policy_name=str(protocol.evaluation.get("policy", "rule_based")),
                episode_id=f"{scenario.name}_{episode:03d}",
                start_index=0,
            )
            transition["scenario"] = scenario.name
            transition["shift_family"] = scenario.family
            transitions.append(transition)
    return pd.concat(transitions, ignore_index=True), shift_summary


def load_reference_frame(protocol) -> pd.DataFrame:
    frames = [pd.read_parquet(ROOT / path) for path in protocol.reference_distribution["dataset_paths"]]
    reference = pd.concat(frames, ignore_index=True)
    if bool(protocol.reference_distribution.get("fit_only_safe_transitions", True)) and "hard_safety_cost" in reference.columns:
        safe = reference.loc[reference["hard_safety_cost"] <= 1e-9].copy()
        if len(safe) >= 200:
            reference = safe
    return reference


def plot_results(shift_summary: pd.DataFrame, risk_summary: pd.DataFrame, scored: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(9.0, 2.9))
    plot_shift = shift_summary.copy()
    plot_shift = plot_shift.sort_values("mean_absolute_relative_change")
    axes[0].barh(plot_shift["scenario"], plot_shift["mean_absolute_relative_change"], color="#6C9A8B")
    axes[0].set_xlabel("Mean absolute relative change")
    axes[0].set_title("Shift intensity")
    scenario_summary = risk_summary.loc[risk_summary["scenario"] != "all"].copy()
    scenario_summary = scenario_summary.sort_values("mean_ood_score")
    axes[1].barh(scenario_summary["scenario"], scenario_summary["mean_ood_score"], color="#335C81")
    axes[1].set_xlabel("Mean ensemble OOD score")
    axes[1].set_title("Risk score by scenario")
    global_row = risk_summary.loc[risk_summary["scenario"] == "all"].iloc[0]
    axes[2].bar(["AUROC", "AUPRC"], [global_row["auroc"], global_row["auprc"]], color=["#B23A48", "#E3A62F"])
    axes[2].set_ylim(0.0, 1.0)
    axes[2].axhline(0.65, color="#7A7A7A", lw=0.8, ls="--")
    axes[2].set_title("Global hard-safety risk detection")
    for ax, label in zip(axes, ["a", "b", "c"]):
        ax.grid(axis="x" if label in {"a", "b"} else "y", color="#D9D9D9", lw=0.5)
        ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")
    fig.tight_layout()
    save_figure(fig, FIGURE_DIR / "shift_protocol_ood_summary")
    plt.close(fig)


def write_document(protocol, shift_summary: pd.DataFrame, risk_summary: pd.DataFrame) -> None:
    global_row = risk_summary.loc[risk_summary["scenario"] == "all"].iloc[0]
    scenario_table = risk_summary.loc[risk_summary["scenario"] != "all", [
        "scenario",
        "transitions",
        "mean_ood_score",
        "p90_ood_score",
        "mean_hard_safety_cost",
        "unsafe_rate",
        "auroc",
        "auprc",
    ]].copy()
    shift_table = shift_summary[[
        "scenario",
        "family",
        "mean_absolute_relative_change",
        "electric_load_mw_relative_change",
        "heat_load_mw_th_relative_change",
        "pv_available_mw_relative_change",
        "wind_available_mw_relative_change",
        "cop_ashp_radiator_relative_change",
    ]].copy()
    text = f"""# 分布漂移协议与 OOD 风险估计

本文档对应第 9 周任务：正式定义分布漂移协议，并实现 OOD 风险估计。协议配置见 `configs/shift_protocol.yaml`，结果文件位于 `results/shift_protocol_ood/`。

## 1. 分布漂移协议

协议名称：`{protocol.name}`。

参考分布使用 Expert 离线数据中的安全 transition；评估期从 `{protocol.evaluation['start_utc']}` 开始，按 {protocol.evaluation['episode_hours']} 小时 episode、{protocol.evaluation['stride_hours']} 小时间隔抽取 {protocol.evaluation['episodes']} 个 episode。评估控制器为 `{protocol.evaluation.get('policy', 'rule_based')}`。

漂移场景覆盖四类机制：负荷上升、可再生出力下降、天气/COP 异常、设备退化，以及一个复合压力场景。

{dataframe_to_markdown(shift_table)}

## 2. OOD 风险估计方法

本次使用 dynamics ensemble risk estimator。每个模型输入 state-action，预测下一状态增量；OOD 分数由三部分组成。hard safety 风险标签定义为 `hard_safety_cost > 1e-6`，避免将数值求解残差误判为失负荷。

\\[
R_{{ood}} = R_{{disagreement}} + R_{{prediction\\ error}} + 0.05 R_{{novelty}}
\\]

其中 `disagreement` 表示模型集成预测分歧，`prediction error` 表示平均模型的下一状态预测误差，`novelty` 表示 state-action 相对 Expert 安全样本的分布新颖度。最终用训练集 90 分位原始风险作尺度归一化。

## 3. 结果

全局 hard safety 风险识别结果：

- AUROC：{float(global_row['auroc']):.3f}
- AUPRC：{float(global_row['auprc']):.3f}
- Spearman：{float(global_row['spearman_corr']):.3f}
- unsafe transition rate：{float(global_row['unsafe_rate']):.3f}

分场景结果：

{dataframe_to_markdown(scenario_table)}

## 4. 阶段判断

若全局 AUROC 稳定高于 0.65，说明 ensemble OOD 分数已经具备继续进入安全约束/投影联动实验的价值；若低于 0.65，则 OOD 模块仍只能作为辅助诊断，不宜作为论文主创新点。

本轮图件：

- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.png`
- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.pdf`
- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.svg`
- `results/figures/shift_protocol_ood/shift_protocol_ood_summary.tiff`
"""
    DOC_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    configure_style()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    protocol = load_shift_protocol(PROTOCOL_PATH)
    policy_config = load_yaml(POLICY_CONFIG_PATH)
    frame, system_config = load_dispatch_inputs(system_config_path=CONFIG_PATH)
    transitions_path = RESULT_DIR / "shift_eval_transitions.parquet"
    shift_summary_path = RESULT_DIR / "shift_protocol_summary.csv"
    transitions, shift_summary = generate_shift_transitions(frame, system_config, policy_config, protocol)
    transitions.to_parquet(transitions_path, index=False)
    shift_summary.to_csv(shift_summary_path, index=False)

    reference = load_reference_frame(protocol)
    ood_cfg = protocol.ood
    estimator = DynamicsEnsembleRiskEstimator(
        n_models=int(ood_cfg.get("n_models", 5)),
        hidden_dim=int(ood_cfg.get("hidden_dim", 64)),
        epochs=int(ood_cfg.get("epochs", 45)),
        learning_rate=float(ood_cfg.get("learning_rate", 1e-3)),
        batch_size=int(ood_cfg.get("batch_size", 256)),
        seed=int(ood_cfg.get("seed", 29)),
    )
    estimator.fit(reference)
    scored, risk_summary = evaluate_ensemble_risk_by_scenario(estimator, transitions, scenario_column="scenario")
    scored.to_parquet(RESULT_DIR / "ood_scored_shift_transitions.parquet", index=False)
    risk_summary.to_csv(RESULT_DIR / "ood_risk_summary.csv", index=False)
    plot_results(shift_summary, risk_summary, scored)
    write_document(protocol, shift_summary, risk_summary)
    print(risk_summary.to_string(index=False))
    print(f"result_dir={RESULT_DIR}")
    print(f"figure_dir={FIGURE_DIR}")
    print(f"doc={DOC_PATH}")


if __name__ == "__main__":
    main()
