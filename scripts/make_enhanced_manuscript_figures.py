from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.path import Path as MplPath
from matplotlib.patches import FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "figures" / "enhanced_manuscript"
OUT.mkdir(parents=True, exist_ok=True)


COLORS = {
    "classical": "#6C757D",
    "rule": "#8C8C8C",
    "raw": "#D95F02",
    "fixed": "#7570B3",
    "adaptive": "#1B9E77",
    "risk": "#1F4E79",
    "safety": "#C0392B",
    "cost": "#2C7FB8",
    "neutral": "#F7F7F7",
    "border": "#2B3A42",
}

METHOD_LABEL = {
    "perfect_information_lp": "Perfect\nLP",
    "rolling_mpc": "Rolling\nMPC",
    "rule_based": "Rule\nbased",
    "bc": "BC",
    "td3_bc": "TD3+BC",
    "cql": "CQL",
    "iql": "IQL",
    "cql_fixed_safety": "CQL\nfixed",
    "iql_fixed_safety": "IQL\nfixed",
    "cql_adaptive_safety": "CQL\nadaptive",
    "iql_adaptive_safety": "IQL\nadaptive",
}

SCENARIO_LABEL = {
    "in_distribution": "In-dist.",
    "load_up_20": "Load +20%",
    "cold_wave_extreme": "Cold wave",
    "compound_extreme": "Compound",
    "year_2017_winter": "2017 winter",
    "year_2018_winter": "2018 winter",
    "year_2019_winter": "2019 winter",
    "cold_climate_zone": "Cold climate",
    "price_spike_low_renewable": "Price spike\nlow RES",
    "cold_wave_device_fault": "Cold + fault",
    "three_day_low_renewable": "3-day low RES",
}


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "figure.titlesize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#E6E6E6",
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_all(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.tiff", dpi=300, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.08, 1.05, label, transform=ax.transAxes, weight="bold", fontsize=10, va="bottom")


def draw_box(ax, xy, wh, text, fc="#F7FBFF", ec=COLORS["border"], lw=1.2, fontsize=8, rounding=0.025):
    x, y = xy
    w, h = wh
    box = patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.015,rounding_size={rounding}",
        fc=fc,
        ec=ec,
        lw=lw,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, linespacing=1.25)
    return box


def arrow(ax, start, end, color=COLORS["border"], lw=1.2, rad=0.0):
    arr = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=10,
        lw=lw,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arr)
    return arr


def fig1_framework() -> None:
    fig, ax = plt.subplots(figsize=(10.2, 5.7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.02,
        0.96,
        "Distribution-shift-aware safe offline RL dispatch",
        fontsize=13,
        weight="bold",
        ha="left",
    )
    ax.text(
        0.02,
        0.91,
        "Offline policy proposes an action; OOD risk decides how much physics-based correction is needed.",
        fontsize=9,
        color="#4A4A4A",
        ha="left",
    )

    # Data and training lane
    draw_box(ax, (0.03, 0.70), (0.15, 0.12), "Public data\nOPSD + When2Heat\nweather", fc="#E8F1FA")
    draw_box(ax, (0.23, 0.70), (0.16, 0.12), "Aggregate RIES\nsimulator\nbalances + storage", fc="#E8F1FA")
    draw_box(ax, (0.44, 0.70), (0.17, 0.12), "Offline datasets\nexpert / mixed / poor\nfixed trajectories", fc="#E8F1FA")
    draw_box(ax, (0.67, 0.70), (0.16, 0.12), "Offline policy\nBC / TD3+BC\nCQL / IQL", fc="#E8F1FA")
    arrow(ax, (0.18, 0.76), (0.23, 0.76))
    arrow(ax, (0.39, 0.76), (0.44, 0.76))
    arrow(ax, (0.61, 0.76), (0.67, 0.76))

    # Deployment lane
    draw_box(ax, (0.04, 0.43), (0.18, 0.13), "Shifted deployment\nload, cold wave,\nrenewables, faults", fc="#FFF7E6")
    draw_box(ax, (0.29, 0.43), (0.16, 0.13), "State $s_t$\nSOC, load, COP,\ntime, price signal", fc="#FFF7E6")
    draw_box(ax, (0.52, 0.43), (0.14, 0.13), "Raw action\n$a_t$", fc="#FFF7E6")
    draw_box(ax, (0.74, 0.43), (0.18, 0.13), "Safe action\n$a_t^{safe}$\nphysical dispatch", fc="#EAF6EF")
    arrow(ax, (0.22, 0.495), (0.29, 0.495))
    arrow(ax, (0.45, 0.495), (0.52, 0.495))
    arrow(ax, (0.66, 0.495), (0.74, 0.495))
    arrow(ax, (0.75, 0.70), (0.59, 0.56), rad=-0.12)

    # OOD and safety layer lane
    draw_box(ax, (0.29, 0.18), (0.18, 0.13), "Dynamics ensemble\nOOD risk $R_{OOD}$\ndisagreement + error", fc="#EDF2FF")
    draw_box(ax, (0.53, 0.18), (0.18, 0.13), "Adaptive gate\nrisk weight $\\rho$\npass / blend / project", fc="#EDF2FF")
    draw_box(ax, (0.76, 0.18), (0.18, 0.13), "Physics projection\nmin correction to\nfeasible set $\\mathcal{F}$", fc="#EDF2FF")
    arrow(ax, (0.37, 0.43), (0.37, 0.31))
    arrow(ax, (0.47, 0.245), (0.53, 0.245))
    arrow(ax, (0.71, 0.245), (0.76, 0.245))
    arrow(ax, (0.85, 0.31), (0.84, 0.43))
    arrow(ax, (0.59, 0.43), (0.62, 0.31))

    # Evaluation lane
    draw_box(ax, (0.06, 0.05), (0.20, 0.10), "Evaluation metrics\ncost, hard safety,\nCVaR, time", fc="#F6F6F6", fontsize=7.5)
    draw_box(ax, (0.40, 0.05), (0.20, 0.10), "Mechanism evidence\nintervention rate\nprojection distance", fc="#F6F6F6", fontsize=7.5)
    draw_box(ax, (0.73, 0.05), (0.20, 0.10), "Claim boundary\naggregate model\npredefined shifts", fc="#F6F6F6", fontsize=7.5)
    arrow(ax, (0.83, 0.43), (0.83, 0.15), color="#6B6B6B", rad=0.15)
    arrow(ax, (0.37, 0.18), (0.50, 0.15), color="#6B6B6B", rad=-0.15)
    arrow(ax, (0.83, 0.18), (0.83, 0.15), color="#6B6B6B")

    # Visual legend
    ax.add_patch(patches.Rectangle((0.035, 0.875), 0.025, 0.018, fc="#E8F1FA", ec=COLORS["border"], lw=0.6))
    ax.text(0.065, 0.884, "offline preparation", va="center", fontsize=7, color="#333333")
    ax.add_patch(patches.Rectangle((0.205, 0.875), 0.025, 0.018, fc="#FFF7E6", ec=COLORS["border"], lw=0.6))
    ax.text(0.235, 0.884, "deployment", va="center", fontsize=7, color="#333333")
    ax.add_patch(patches.Rectangle((0.335, 0.875), 0.025, 0.018, fc="#EDF2FF", ec=COLORS["border"], lw=0.6))
    ax.text(0.365, 0.884, "risk and safety", va="center", fontsize=7, color="#333333")

    save_all(fig, "fig1_enhanced_framework")


def fig3_ood_polar() -> None:
    df = pd.read_csv(ROOT / "results" / "shift_protocol_ood" / "ood_risk_summary.csv")
    df = df[df["scenario"] != "all"].copy()
    keep = [
        "in_distribution",
        "renewable_down_20",
        "load_up_20",
        "load_up_35",
        "cold_wave_extreme",
        "compound_extreme",
        "compound_stress",
        "equipment_degradation",
    ]
    df = df[df["scenario"].isin(keep)]
    df["label"] = df["scenario"].map(lambda x: SCENARIO_LABEL.get(x, x.replace("_", "\n")))
    df = df.sort_values("mean_ood_score")

    fig = plt.figure(figsize=(10, 4.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.95], wspace=0.35)
    ax0 = fig.add_subplot(gs[0, 0], polar=True)
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])

    theta = np.linspace(0, 2 * np.pi, len(df), endpoint=False)
    width = 2 * np.pi / len(df) * 0.78
    vals = df["mean_ood_score"].to_numpy()
    colors = plt.cm.YlOrRd((df["unsafe_rate"].to_numpy() - df["unsafe_rate"].min()) / (df["unsafe_rate"].max() - df["unsafe_rate"].min() + 1e-9))
    ax0.bar(theta, vals, width=width, bottom=0, color=colors, edgecolor="white", linewidth=1.0)
    ax0.set_xticks(theta)
    ax0.set_xticklabels(df["label"], fontsize=7)
    ax0.set_title("a  OOD risk by shift family\n(color = unsafe rate)", loc="left", pad=18, weight="bold")
    ax0.set_ylim(0, max(vals) * 1.18)
    ax0.grid(color="#DDDDDD")

    ax1.scatter(df["mean_ood_score"], df["unsafe_rate"], s=55, c=df["mean_hard_safety_cost"], cmap="Reds", edgecolor="#333333", linewidth=0.5)
    for _, r in df.iterrows():
        if r["unsafe_rate"] > 0.02 or r["scenario"] in ["in_distribution", "load_up_20"]:
            ax1.text(r["mean_ood_score"] + 0.015, r["unsafe_rate"] + 0.002, SCENARIO_LABEL.get(r["scenario"], r["scenario"]), fontsize=6.5)
    ax1.set_xlabel("Mean ensemble OOD score")
    ax1.set_ylabel("Unsafe transition rate")
    ax1.set_title("b  Risk is useful but imperfect", loc="left", weight="bold")

    all_row = pd.read_csv(ROOT / "results" / "shift_protocol_ood" / "ood_risk_summary.csv").query("scenario == 'all'").iloc[0]
    metrics = ["AUROC", "AUPRC"]
    values = [all_row["auroc"], all_row["auprc"]]
    ax2.bar(metrics, values, color=[COLORS["risk"], "#F2A900"], width=0.55)
    ax2.axhline(0.5, color="#999999", ls="--", lw=1)
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("Score")
    ax2.set_title("c  Global hard-safety detection", loc="left", weight="bold")
    for i, v in enumerate(values):
        ax2.text(i, v + 0.035, f"{v:.3f}", ha="center", fontsize=8)

    fig.suptitle("OOD risk rises under safety-relevant distribution shifts, but is not a safety certificate", y=1.02, weight="bold")
    save_all(fig, "fig3_enhanced_ood_polar")


def method_group(method: str) -> str:
    if method in ["perfect_information_lp", "rolling_mpc"]:
        return "Optimization"
    if method == "rule_based":
        return "Rule-based"
    if method in ["bc", "td3_bc", "cql", "iql"]:
        return "Raw offline RL"
    if "fixed" in method:
        return "Fixed safety"
    if "adaptive" in method:
        return "Adaptive safety"
    return "Other"


def group_color(method: str) -> str:
    g = method_group(method)
    return {
        "Optimization": COLORS["classical"],
        "Rule-based": COLORS["rule"],
        "Raw offline RL": COLORS["raw"],
        "Fixed safety": COLORS["fixed"],
        "Adaptive safety": COLORS["adaptive"],
    }.get(g, "#555555")


def fig4_main_violin_box() -> None:
    raw = pd.read_csv(ROOT / "results" / "week13_14_experiments" / "week13_raw_results.csv")
    raw = raw[raw["scenario"].isin(["in_distribution", "load_up_20", "cold_wave_extreme", "compound_extreme"])]
    methods = ["rolling_mpc", "rule_based", "cql", "iql", "cql_fixed_safety", "iql_fixed_safety", "cql_adaptive_safety", "iql_adaptive_safety"]
    raw = raw[raw["method"].isin(methods)]
    raw["method_label"] = raw["method"].map(METHOD_LABEL)
    raw["scenario_label"] = raw["scenario"].map(SCENARIO_LABEL)

    fig = plt.figure(figsize=(11, 6.3))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.0], hspace=0.38, wspace=0.28)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    order = methods
    positions = np.arange(len(order))
    safety_data = [raw.loc[raw["method"] == m, "mean_episode_hard_safety_cost"].to_numpy() for m in order]
    vio = ax0.violinplot(safety_data, positions=positions, widths=0.75, showmeans=False, showextrema=False)
    for body, m in zip(vio["bodies"], order):
        body.set_facecolor(group_color(m))
        body.set_edgecolor("#333333")
        body.set_alpha(0.55)
    bp = ax0.boxplot(safety_data, positions=positions, widths=0.28, patch_artist=True, showfliers=False)
    for patch, m in zip(bp["boxes"], order):
        patch.set_facecolor("white")
        patch.set_edgecolor(group_color(m))
        patch.set_linewidth(1.2)
    ax0.set_xticks(positions)
    ax0.set_xticklabels([METHOD_LABEL[m] for m in order], rotation=0)
    ax0.set_ylabel("Hard-safety index")
    ax0.set_title("a  Raw offline RL has high violation distributions", loc="left", weight="bold")

    # Cost distribution on log axis as box plot
    cost_data = [raw.loc[raw["method"] == m, "mean_episode_cost_eur"].to_numpy() for m in order]
    bp2 = ax1.boxplot(cost_data, positions=positions, widths=0.55, patch_artist=True, showfliers=True)
    for patch, m in zip(bp2["boxes"], order):
        patch.set_facecolor(group_color(m))
        patch.set_alpha(0.45)
        patch.set_edgecolor("#333333")
    ax1.set_yscale("log")
    ax1.set_xticks(positions)
    ax1.set_xticklabels([METHOD_LABEL[m] for m in order], rotation=0)
    ax1.set_ylabel("Episode cost (EUR, log)")
    ax1.set_title("b  Safety correction collapses extreme cost tails", loc="left", weight="bold")

    summary = pd.read_csv(ROOT / "results" / "week13_14_experiments" / "week13_main_summary.csv")
    pivot = summary[summary["method"].isin(["cql_adaptive_safety", "iql_adaptive_safety"])].pivot(index="scenario", columns="method", values="intervention_rate")
    pivot = pivot.loc[["in_distribution", "load_up_20", "cold_wave_extreme", "compound_extreme"]]
    im = ax2.imshow(pivot.values, cmap="Greens", vmin=0, vmax=1, aspect="auto")
    ax2.set_xticks(np.arange(pivot.shape[1]))
    ax2.set_xticklabels(["CQL adaptive", "IQL adaptive"])
    ax2.set_yticks(np.arange(pivot.shape[0]))
    ax2.set_yticklabels([SCENARIO_LABEL[x] for x in pivot.index])
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax2.text(j, i, f"{pivot.iloc[i, j]:.2f}", ha="center", va="center", color="#111111", fontsize=8)
    ax2.set_title("c  Intervention increases with shift severity", loc="left", weight="bold")
    plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.03, label="Intervention rate")

    # Polar/Radar for trade-off under compound scenario
    radar_methods = ["rolling_mpc", "rule_based", "cql", "iql", "cql_adaptive_safety", "iql_adaptive_safety"]
    compound = summary[(summary["scenario"] == "compound_extreme") & (summary["method"].isin(radar_methods))].copy()
    metrics = ["mean_episode_cost_eur", "mean_hard_safety_cost", "intervention_rate", "mean_decision_time_ms"]
    labels = ["Cost", "Hard\nsafety", "Interv.", "Time"]
    # Normalize smaller is better except intervention, still report burden.
    vals = []
    for _, r in compound.iterrows():
        vals.append([float(r[m]) for m in metrics])
    arr = np.array(vals, dtype=float)
    arr = arr / (arr.max(axis=0) + 1e-9)
    theta = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False)
    theta = np.r_[theta, theta[0]]
    ax3.remove()
    ax3 = fig.add_subplot(gs[1, 1], polar=True)
    for row, method in zip(arr, compound["method"]):
        data = np.r_[row, row[0]]
        lw = 1.8 if "adaptive" in method else 1.0
        ax3.plot(theta, data, color=group_color(method), lw=lw, label=METHOD_LABEL[method].replace("\n", " "))
        if "adaptive" in method:
            ax3.fill(theta, data, color=group_color(method), alpha=0.10)
    ax3.set_xticks(theta[:-1])
    ax3.set_xticklabels(labels)
    ax3.set_yticklabels([])
    ax3.set_ylim(0, 1.05)
    ax3.set_title("d  Compound-stress trade-off profile\n(normalized burden, lower is better)", loc="left", weight="bold", pad=18)
    ax3.legend(loc="upper left", bbox_to_anchor=(1.05, 1.05), frameon=False)

    fig.suptitle("Main result: adaptive safety converts unsafe offline policies into physically filtered dispatch", y=0.995, weight="bold")
    save_all(fig, "fig4_enhanced_main_violin")


def fig5_ablation_heatmap() -> None:
    sens = pd.read_csv(ROOT / "results" / "week13_14_experiments" / "week14_sensitivity_results.csv")
    dq = pd.read_csv(ROOT / "results" / "week13_14_experiments" / "week14_data_quality_results.csv")
    ds = pd.read_csv(ROOT / "results" / "week13_14_experiments" / "week14_data_size_results.csv")

    fig = plt.figure(figsize=(10.5, 5.3))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 1.15], hspace=0.48, wspace=0.42)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1:])

    thr = sens[sens["sensitivity"] == "ood_threshold"].copy()
    ax0.plot(thr["level"], thr["mean_projection_distance_l2"], marker="o", color=COLORS["adaptive"], lw=1.8, label="Projection distance")
    ax0.plot(thr["level"], thr["intervention_rate"], marker="s", color=COLORS["risk"], lw=1.6, label="Intervention rate")
    ax0.set_ylim(0, 1.05)
    ax0.set_ylabel("Rate / distance")
    ax0.set_title("a  OOD-threshold sensitivity", loc="left", weight="bold")
    ax0.tick_params(axis="x", rotation=20)
    ax0.legend(frameon=False, loc="lower right")

    dist = sens[sens["sensitivity"] == "distance_weight"].copy()
    sizes = 40 + 1.6 * dist["mean_decision_time_ms"].to_numpy()
    sc = ax1.scatter(
        dist["level"].astype(float),
        dist["mean_weighted_projection_distance"],
        s=sizes,
        c=dist["mean_episode_safety_cost"],
        cmap="PuRd",
        edgecolor="#333333",
        linewidth=0.6,
        alpha=0.85,
    )
    ax1.plot(dist["level"].astype(float), dist["mean_weighted_projection_distance"], color="#777777", lw=1)
    ax1.set_xlabel("Distance weight")
    ax1.set_ylabel("Weighted projection distance")
    ax1.set_title("b  Distance-weight bubble plot\n(size = decision time)", loc="left", weight="bold")
    plt.colorbar(sc, ax=ax1, fraction=0.046, pad=0.03, label="Safety cost")

    load = sens[sens["sensitivity"] == "load_multiplier"].copy()
    xload = load["level"].astype(float)
    ax2.plot(xload, load["mean_episode_hard_safety_cost"], marker="o", color=COLORS["safety"], lw=1.8, label="Hard safety")
    ax2.fill_between(xload, load["mean_episode_hard_safety_cost"], color=COLORS["safety"], alpha=0.10)
    ax2.set_xlabel("Load multiplier")
    ax2.set_ylabel("Hard-safety index", color=COLORS["safety"])
    ax2.tick_params(axis="y", labelcolor=COLORS["safety"])
    ax2b = ax2.twinx()
    ax2b.plot(xload, load["mean_episode_cost_eur"], marker="s", color=COLORS["cost"], lw=1.6, label="Cost")
    ax2b.set_ylabel("Cost (EUR)", color=COLORS["cost"])
    ax2b.tick_params(axis="y", labelcolor=COLORS["cost"])
    ax2.set_title("c  Load stress exposes boundary", loc="left", weight="bold")

    # Data quality as bubble/bar diagnostic.
    metric_col = "mean_episode_cost_eur" if "mean_episode_cost_eur" in dq.columns else dq.select_dtypes(include=[np.number]).columns[-1]
    label_col = "dataset_quality" if "dataset_quality" in dq.columns else dq.columns[0]
    labels = dq[label_col].astype(str).tolist()
    vals = dq[metric_col].astype(float).to_numpy()
    unsafe = dq["unsafe_episode_rate"].astype(float).to_numpy() if "unsafe_episode_rate" in dq.columns else np.ones(len(vals))
    ax3.scatter(np.arange(len(labels)), vals, s=120 + 220 * unsafe, color="#80B1D3", edgecolor="#333333", alpha=0.85)
    ax3.vlines(np.arange(len(labels)), 0, vals, color="#80B1D3", lw=2, alpha=0.55)
    ax3.set_xticks(np.arange(len(labels)))
    ax3.set_xticklabels(labels, rotation=20)
    ax3.set_ylabel("Episode cost (EUR)")
    ax3.set_title("d  Dataset-quality bubble plot\n(size = unsafe rate)", loc="left", weight="bold")

    # Burden decomposition from fixed/adaptive safety variants.
    summary = pd.read_csv(ROOT / "results" / "week13_14_experiments" / "week13_main_summary.csv")
    fixed_adapt = summary[summary["method"].isin(["cql_fixed_safety", "cql_adaptive_safety", "iql_fixed_safety", "iql_adaptive_safety"])]
    comp = fixed_adapt.groupby("method")[["mean_episode_cost_eur", "mean_projection_distance_l2", "intervention_rate", "mean_decision_time_ms"]].mean()
    comp = comp.loc[["cql_fixed_safety", "cql_adaptive_safety", "iql_fixed_safety", "iql_adaptive_safety"]]
    comp_norm = comp / (comp.max(axis=0) + 1e-9)
    x = np.arange(comp_norm.shape[1])
    width = 0.18
    for k, (m, row) in enumerate(comp_norm.iterrows()):
        ax4.bar(x + (k - 1.5) * width, row.values, width=width, color=group_color(m), alpha=0.78, label=METHOD_LABEL[m].replace("\n", " "))
    ax4.set_xticks(x)
    ax4.set_xticklabels(["Cost", "Projection\ndistance", "Intervention", "Decision\ntime"])
    ax4.set_ylim(0, 1.15)
    ax4.set_ylabel("Normalized burden")
    ax4.set_title("e  Safety-layer burden decomposition", loc="left", weight="bold")
    ax4.legend(ncol=2, frameon=False, loc="upper right")

    fig.suptitle("Ablation: safety behavior depends on data support and correction design", y=1.02, weight="bold")
    save_all(fig, "fig5_enhanced_ablation_heatmap")


def fig6_stress_heatmap() -> None:
    stress = pd.read_csv(ROOT / "results" / "week15_16_experiments" / "week15_generalization_stress_results.csv")
    methods = ["rolling_mpc", "rule_based", "cql", "cql_adaptive_safety", "iql", "iql_adaptive_safety"]
    scenarios = [
        "year_2017_winter",
        "year_2018_winter",
        "year_2019_winter",
        "cold_climate_zone",
        "price_spike_low_renewable",
        "cold_wave_device_fault",
        "three_day_low_renewable",
    ]
    sub = stress[stress["method"].isin(methods) & stress["scenario"].isin(scenarios)].copy()
    fig = plt.figure(figsize=(11, 5.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.15, 0.95], wspace=0.35)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2], polar=True)

    mat = sub.pivot_table(index="scenario", columns="method", values="mean_episode_hard_safety_cost", aggfunc="mean").loc[scenarios, methods]
    im = ax0.imshow(mat.values, cmap="Reds", aspect="auto")
    ax0.set_xticks(range(len(methods)))
    ax0.set_xticklabels([METHOD_LABEL[m].replace("\n", " ") for m in methods], rotation=35, ha="right")
    ax0.set_yticks(range(len(scenarios)))
    ax0.set_yticklabels([SCENARIO_LABEL.get(s, s) for s in scenarios])
    ax0.set_title("a  Stress-test hard-safety heatmap", loc="left", weight="bold")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.iloc[i, j]
            ax0.text(j, i, f"{v:.0f}" if v >= 1 else "0", ha="center", va="center", fontsize=7)
    plt.colorbar(im, ax=ax0, fraction=0.046, pad=0.03, label="Hard-safety index")

    cost = sub.pivot_table(index="scenario", columns="method", values="mean_episode_cost_eur", aggfunc="mean").loc[scenarios, methods]
    rel = cost.div(cost["rolling_mpc"], axis=0)
    im2 = ax1.imshow(np.clip(rel.values, 0, 8), cmap="YlOrBr", aspect="auto", vmin=0, vmax=8)
    ax1.set_xticks(range(len(methods)))
    ax1.set_xticklabels([METHOD_LABEL[m].replace("\n", " ") for m in methods], rotation=35, ha="right")
    ax1.set_yticks(range(len(scenarios)))
    ax1.set_yticklabels([])
    ax1.set_title("b  Cost relative to rolling MPC", loc="left", weight="bold")
    for i in range(rel.shape[0]):
        for j in range(rel.shape[1]):
            ax1.text(j, i, f"{rel.iloc[i,j]:.1f}", ha="center", va="center", fontsize=7)
    plt.colorbar(im2, ax=ax1, fraction=0.046, pad=0.03, label="Cost ratio")

    # Polar burden for adaptive interventions across stress scenarios
    adapt = sub[sub["method"].isin(["cql_adaptive_safety", "iql_adaptive_safety"])]
    pol = adapt.groupby("scenario")["intervention_rate"].mean().reindex(scenarios)
    theta = np.linspace(0, 2 * np.pi, len(pol), endpoint=False)
    ax2.bar(theta, pol.values, width=2 * np.pi / len(pol) * 0.75, color=COLORS["adaptive"], alpha=0.7, edgecolor="white")
    ax2.set_xticks(theta)
    ax2.set_xticklabels([SCENARIO_LABEL.get(s, s).replace("\n", " ") for s in pol.index], fontsize=6.5)
    ax2.set_ylim(0, 1.0)
    ax2.set_title("c  Adaptive intervention under stress", loc="left", weight="bold", pad=18)

    fig.suptitle("Stress tests reveal where raw offline RL fails and where physical filtering intervenes", y=1.02, weight="bold")
    save_all(fig, "fig6_enhanced_stress_heatmap")


def fig8_stats_forest() -> None:
    ci = pd.read_csv(ROOT / "results" / "week15_16_experiments" / "week16_confidence_intervals.csv")
    tests = pd.read_csv(ROOT / "results" / "week15_16_experiments" / "week16_pairwise_tests.csv")
    tail = pd.read_csv(ROOT / "results" / "week15_16_experiments" / "week16_tail_risk_metrics.csv")

    main_scenarios = ["load_up_20", "cold_wave_extreme", "compound_extreme"]
    rows = tests[
        tests["scenario"].isin(main_scenarios)
        & tests["baseline"].isin(["cql", "iql"])
        & tests["treatment"].str.contains("adaptive")
        & (tests["metric"] == "mean_episode_hard_safety_cost")
    ].copy()
    rows["label"] = rows["scenario"].map(SCENARIO_LABEL) + "\n" + rows["baseline"].str.upper()
    rows = rows.sort_values(["scenario", "baseline"])

    fig = plt.figure(figsize=(10.5, 5.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 0.95, 0.95], wspace=0.42)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])

    y = np.arange(len(rows))
    ax0.axvline(0, color="#555555", lw=1)
    ax0.scatter(rows["mean_delta"], y, s=55, color=COLORS["adaptive"], zorder=3)
    for i, r in enumerate(rows.itertuples()):
        ax0.plot([r.mean_delta, 0], [i, i], color=COLORS["adaptive"], lw=1.8, alpha=0.75)
        ax0.text(r.mean_delta - 2, i, f"{r.mean_delta:.1f}", ha="right", va="center", fontsize=7)
    ax0.set_yticks(y)
    ax0.set_yticklabels(rows["label"])
    ax0.set_xlabel("Mean hard-safety reduction\n(adaptive - raw)")
    ax0.set_title("a  Paired effect sizes", loc="left", weight="bold")
    ax0.invert_yaxis()

    pvals = rows["p_value"].to_numpy()
    ax1.scatter(-np.log10(pvals), y, s=50, color=COLORS["risk"])
    ax1.axvline(-np.log10(0.05), color="#C0392B", ls="--", lw=1)
    ax1.set_yticks(y)
    ax1.set_yticklabels([])
    ax1.set_xlabel(r"$-\log_{10}(p)$")
    ax1.set_title("b  Paired-test evidence", loc="left", weight="bold")
    ax1.invert_yaxis()

    subset = tail[tail["scenario"].isin(main_scenarios) & tail["method"].isin(["cql", "iql", "cql_adaptive_safety", "iql_adaptive_safety"])]
    pivot = subset.pivot_table(index="scenario", columns="method", values="cvar90_hard_safety_cost", aggfunc="mean").loc[main_scenarios]
    im = ax2.imshow(pivot.values, cmap="OrRd", aspect="auto")
    ax2.set_xticks(range(pivot.shape[1]))
    ax2.set_xticklabels([METHOD_LABEL[m].replace("\n", " ") for m in pivot.columns], rotation=35, ha="right")
    ax2.set_yticks(range(pivot.shape[0]))
    ax2.set_yticklabels([SCENARIO_LABEL[s] for s in pivot.index])
    ax2.set_title("c  Tail hard-safety risk", loc="left", weight="bold")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.iloc[i, j]
            ax2.text(j, i, f"{v:.0f}" if v >= 1 else "0", ha="center", va="center", fontsize=7)
    plt.colorbar(im, ax=ax2, fraction=0.046, pad=0.03)

    fig.suptitle("Statistical evidence is strongest for five-seed shifted scenarios", y=1.02, weight="bold")
    save_all(fig, "fig8_enhanced_statistics_forest")


def main() -> None:
    set_style()
    fig1_framework()
    fig3_ood_polar()
    fig4_main_violin_box()
    fig5_ablation_heatmap()
    fig6_stress_heatmap()
    fig8_stats_forest()
    print(f"Wrote enhanced figures to {OUT}")


if __name__ == "__main__":
    main()
