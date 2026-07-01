"""Generate editable LaTeX tables for the Applied Energy manuscript package.

The script reads existing result CSVs and writes compact tabular files under
``manuscript/latex/tables``. It intentionally keeps the tables small enough for
the main text; full CSV outputs remain the source data.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "latex" / "tables"
OUT.mkdir(parents=True, exist_ok=True)


def fmt(x, digits: int = 2) -> str:
    if pd.isna(x):
        return "--"
    if abs(float(x)) < 5e-7:
        return "0.00"
    return f"{float(x):.{digits}f}"


def write(path: str, text: str) -> None:
    """Write a compact, editable LaTeX table.

    Main-text tables are wrapped in resizebox to avoid overfull hbox warnings in
    the Elsevier preprint layout while keeping the table content editable.
    """
    compact_size = "scriptsize" if path in {"table_main_results.tex", "table_figure_plan.tex"} else "small"
    if "\\begin{tabular}" in text and "\\resizebox{\\textwidth}{!}{%" not in text:
        text = text.replace(
            "\\begin{tabular}",
            f"\\{compact_size}\n\\resizebox{{\\textwidth}}{{!}}{{%\n\\begin{{tabular}}",
            1,
        )
        text = text.replace("\\end{tabular}\n\\end{table}", "\\end{tabular}\n}\n\\end{table}", 1)
    (OUT / path).write_text(text, encoding="utf-8")


def latex_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


def make_system_table() -> None:
    rows = [
        ("Electric load peak", "10 MW", "Scaled from German electricity load"),
        ("Heat load peak", "18 MWth", "Scaled from When2Heat heat demand"),
        ("Grid import/export", "12 MW / 6 MW", "Constrained interconnection"),
        ("Photovoltaic", "6 MWp", "Capacity-factor time series"),
        ("Wind", "4 MW", "Capacity-factor time series"),
        ("CHP", "6 MWe / 7.2 MWth", "Fixed heat-to-electric ratio 1.2"),
        ("Air-source heat pump", "10 MWth", "Hourly COP from When2Heat"),
        ("Battery", "4 MW / 8 MWh", "SOC range 10--90\\%"),
        ("Thermal storage", "5 MW / 20 MWhth", "SOC range 10--90\\%"),
    ]
    body = "\n".join(f"{a} & {b} & {c} \\\\" for a, b, c in rows)
    write(
        "table_system_parameters.tex",
        "\\begin{table}[t]\n"
        "\\centering\n"
        "\\caption{Main system scale and device parameters.}\n"
        "\\label{tab:system_parameters}\n"
        "\\begin{tabular}{lll}\n"
        "\\toprule\n"
        "Item & Value & Role/source \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n",
    )


def make_shift_table() -> None:
    path = ROOT / "results" / "shift_protocol_ood" / "shift_protocol_summary.csv"
    df = pd.read_csv(path)
    keep = [
        "in_distribution",
        "load_up_20",
        "cold_wave_extreme",
        "equipment_degradation",
        "compound_extreme",
    ]
    df = df[df["scenario"].isin(keep)].copy()
    cols = [
        "scenario",
        "family",
        "electric_load_mw_relative_change",
        "heat_load_mw_th_relative_change",
        "pv_available_mw_relative_change",
        "wind_available_mw_relative_change",
        "cop_ashp_radiator_relative_change",
    ]
    df = df[cols]
    header = (
        "Scenario & Family & $\\Delta P^{load}$ & $\\Delta Q^{load}$ & "
        "$\\Delta PV$ & $\\Delta Wind$ & $\\Delta COP$ \\\\"
    )
    lines = []
    for _, row in df.iterrows():
        lines.append(
            " & ".join(
                [
                    latex_escape(row["scenario"]),
                    latex_escape(row["family"]),
                    fmt(row["electric_load_mw_relative_change"], 2),
                    fmt(row["heat_load_mw_th_relative_change"], 2),
                    fmt(row["pv_available_mw_relative_change"], 2),
                    fmt(row["wind_available_mw_relative_change"], 2),
                    fmt(row["cop_ashp_radiator_relative_change"], 2),
                ]
            )
            + " \\\\"
        )
    write(
        "table_shift_protocol.tex",
        "\\begin{table}[t]\n"
        "\\centering\n"
        "\\caption{Representative distribution-shift scenarios used for evaluation. Relative changes are reported against the reference data.}\n"
        "\\label{tab:shift_protocol}\n"
        "\\begin{tabular}{llrrrrr}\n"
        "\\toprule\n"
        f"{header}\n"
        "\\midrule\n"
        + "\n".join(lines)
        + "\n\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n",
    )


def make_main_results_table() -> None:
    path = ROOT / "results" / "week13_14_experiments" / "week13_main_summary.csv"
    df = pd.read_csv(path)
    methods = [
        "rolling_mpc",
        "rule_based",
        "cql",
        "cql_adaptive_safety",
        "iql",
        "iql_adaptive_safety",
    ]
    scenarios = ["in_distribution", "load_up_20", "cold_wave_extreme", "compound_extreme"]
    df = df[df["method"].isin(methods) & df["scenario"].isin(scenarios)].copy()
    order = {m: i for i, m in enumerate(methods)}
    df["order"] = df["method"].map(order)
    df = df.sort_values(["scenario", "order"])
    lines = []
    for _, row in df.iterrows():
        lines.append(
            f"{latex_escape(row['scenario'])} & {latex_escape(row['method'])} & "
            f"{fmt(row['mean_episode_cost_eur'], 0)} & "
            f"{fmt(row['mean_hard_safety_cost'], 2)} & "
            f"{fmt(row['intervention_rate'], 2)} & "
            f"{fmt(row['mean_decision_time_ms'], 2)} \\\\"
        )
    write(
        "table_main_results.tex",
        "\\begin{table}[t]\n"
        "\\centering\n"
        "\\caption{Main dispatch results. Costs are mean episode operating costs; hard safety cost summarizes physical infeasibility and emergency violations.}\n"
        "\\label{tab:main_results}\n"
        "\\begin{tabular}{llrrrr}\n"
        "\\toprule\n"
        "Scenario & Method & Cost (EUR) & Hard safety & Interv. rate & Time (ms) \\\\\n"
        "\\midrule\n"
        + "\n".join(lines)
        + "\n\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n",
    )


def make_statistical_tests_table() -> None:
    path = ROOT / "results" / "week15_16_experiments" / "week16_pairwise_tests.csv"
    df = pd.read_csv(path)
    df = df[(df["n_pairs"] >= 5) & (df["p_value"] < 0.05)].copy()
    df = df[
        [
            "scenario",
            "baseline",
            "treatment",
            "n_pairs",
            "mean_delta",
            "p_value",
        ]
    ]
    lines = []
    for _, row in df.iterrows():
        lines.append(
            f"{latex_escape(row['scenario'])} & {latex_escape(row['baseline'])} $\\rightarrow$ "
            f"{latex_escape(row['treatment'])} & {int(row['n_pairs'])} & "
            f"{fmt(row['mean_delta'], 2)} & {fmt(row['p_value'], 4)} \\\\"
        )
    write(
        "table_paired_tests.tex",
        "\\begin{table}[t]\n"
        "\\centering\n"
        "\\caption{Paired tests for hard-safety reductions in five-seed scenarios. Negative mean delta indicates lower hard safety cost after adaptive safety.}\n"
        "\\label{tab:paired_tests}\n"
        "\\begin{tabular}{llrrr}\n"
        "\\toprule\n"
        "Scenario & Comparison & Pairs & Mean delta & $p$ value \\\\\n"
        "\\midrule\n"
        + "\n".join(lines)
        + "\n\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n",
    )


def make_figure_plan_table() -> None:
    rows = [
        ("Fig. 1", "Framework and adaptive safety mechanism", "Schematic-led composite", "results/figures/adaptive_safety/adaptive_safety_method_flow.pdf"),
        ("Fig. 2", "Data profiles and system operating context", "Quantitative grid", "results/figures/system_profiles/annual_distribution.pdf; typical_days.pdf"),
        ("Fig. 3", "Representative deterministic dispatch", "Quantitative grid", "results/figures/deterministic_dispatch/*_day_dispatch.pdf"),
        ("Fig. 4", "Main baseline comparison", "Hero comparison panel", "results/figures/week13_14/week13_main_results.pdf"),
        ("Fig. 5", "Ablation and sensitivity", "Robustness grid", "results/figures/week13_14/week14_ablation_sensitivity.pdf"),
        ("Fig. 6", "Generalization and stress tests", "Robustness grid", "results/figures/week15_16/week15_stress_summary.pdf"),
        ("Fig. 7", "Adaptive intervention trajectory", "Time-series mechanism", "results/figures/week15_16/week15_intervention_trajectory.pdf"),
        ("Fig. 8", "Statistics, tail risk and failure modes", "Statistical summary", "results/figures/week15_16/week16_statistics_summary.pdf"),
    ]
    body = "\n".join(
        f"{a} & {b} & {c} & \\path{{{d}}} \\\\" for a, b, c, d in rows
    )
    write(
        "table_figure_plan.tex",
        "\\begin{table}[t]\n"
        "\\centering\n"
        "\\caption{Planned main-text figures and their evidence role.}\n"
        "\\label{tab:figure_plan}\n"
        "\\begin{tabular}{llll}\n"
        "\\toprule\n"
        "No. & Manuscript role & Archetype & Source file \\\\\n"
        "\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "\\end{table}\n",
    )


def main() -> None:
    make_system_table()
    make_shift_table()
    make_main_results_table()
    make_statistical_tests_table()
    make_figure_plan_table()


if __name__ == "__main__":
    main()
