from __future__ import annotations

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimization.deterministic_dispatch import solve_typical_days


OUTPUT_DIR = ROOT / "results" / "figures" / "deterministic_dispatch"
SOURCE_DIR = OUTPUT_DIR / "source_data"

PALETTE = {
    "grid": "#335C81",
    "chp": "#6C5B7B",
    "pv": "#E3A62F",
    "wind": "#6C9A8B",
    "battery": "#7E9F35",
    "heat_pump": "#3D8B8B",
    "thermal": "#C95D4B",
    "load": "#252525",
    "shed": "#B23A48",
    "soc": "#4A4A4A",
}


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


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.09, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="top")


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")


def plot_dispatch_day(label: str, dispatch: pd.DataFrame) -> None:
    hours = np.arange(len(dispatch))
    date = dispatch.index[0].strftime("%Y-%m-%d")
    title_map = {
        "winter": "Representative winter day",
        "summer": "Representative summer day",
        "shoulder": "Representative shoulder-season day",
    }

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 6.2), sharex=True)

    ax = axes[0]
    electric_components = [
        ("PV used", dispatch["pv_used_mw"], PALETTE["pv"]),
        ("Wind used", dispatch["wind_used_mw"], PALETTE["wind"]),
        ("CHP", dispatch["chp_electric_mw"], PALETTE["chp"]),
        ("Battery discharge", dispatch["battery_discharge_mw"], PALETTE["battery"]),
        ("Grid import", dispatch["grid_import_mw"], PALETTE["grid"]),
        ("Electric shedding", dispatch["electric_shedding_mw"], PALETTE["shed"]),
    ]
    bottom = np.zeros(len(dispatch))
    for name, values, color in electric_components:
        ax.bar(hours, values, bottom=bottom, width=0.82, color=color, alpha=0.78, label=name)
        bottom += values.to_numpy()
    ax.plot(hours, dispatch["electric_load_mw"] + dispatch["heat_pump_electric_mw"] + dispatch["battery_charge_mw"] + dispatch["grid_export_mw"], color=PALETTE["load"], lw=1.7, label="Electric demand + flexible uses")
    ax.set_ylabel("Electric power (MW)")
    ax.set_title(f"{title_map.get(label, label.title())}: deterministic dispatch ({date}, UTC)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    ax.legend(ncol=3, loc="upper left")
    panel_label(ax, "a")

    ax = axes[1]
    heat_components = [
        ("CHP heat", dispatch["chp_heat_mw_th"], PALETTE["chp"]),
        ("Heat pump", dispatch["heat_pump_heat_mw_th"], PALETTE["heat_pump"]),
        ("Thermal discharge", dispatch["thermal_discharge_mw_th"], PALETTE["thermal"]),
        ("Heat shedding", dispatch["heat_shedding_mw_th"], PALETTE["shed"]),
    ]
    bottom = np.zeros(len(dispatch))
    for name, values, color in heat_components:
        ax.bar(hours, values, bottom=bottom, width=0.82, color=color, alpha=0.78, label=name)
        bottom += values.to_numpy()
    ax.plot(hours, dispatch["heat_load_mw_th"] + dispatch["thermal_charge_mw_th"], color=PALETTE["load"], lw=1.7, label="Heat demand + storage charge")
    ax.set_ylabel("Heat power (MWth)")
    ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    ax.legend(ncol=3, loc="upper left")
    panel_label(ax, "b")

    ax = axes[2]
    ax.plot(hours, dispatch["battery_soc_mwh"], color=PALETTE["battery"], lw=1.8, label="Battery SOC")
    ax.plot(hours, dispatch["thermal_soc_mwh_th"], color=PALETTE["thermal"], lw=1.8, label="Thermal storage SOC")
    ax.set_ylabel("Storage energy (MWh)")
    ax.set_xlabel("Hour (UTC)")
    ax.set_xticks([0, 4, 8, 12, 16, 20, 23])
    ax.grid(axis="y", color="#D9D9D9", lw=0.5)
    twin = ax.twinx()
    twin.plot(hours, dispatch["electricity_import_price_eur_per_mwh"], color="#8E8E8E", lw=1.3, ls="--", label="Import price")
    twin.plot(hours, dispatch["cop_ashp_radiator"], color=PALETTE["heat_pump"], lw=1.3, ls=":", label="ASHP COP")
    twin.set_ylabel("Price / COP")
    lines = ax.lines + twin.lines
    ax.legend(lines, [line.get_label() for line in lines], ncol=4, loc="upper left")
    panel_label(ax, "c")

    fig.tight_layout()
    save_figure(fig, OUTPUT_DIR / f"{label}_day_dispatch")
    plt.close(fig)


def write_summary(results: dict[str, pd.DataFrame]) -> None:
    rows = []
    for label, dispatch in results.items():
        rows.append(
            {
                "typical_day": label,
                "date_utc": dispatch.index[0].strftime("%Y-%m-%d"),
                "objective_eur": dispatch["objective_eur"].iloc[0],
                "electric_shedding_mwh": dispatch["electric_shedding_mw"].sum(),
                "heat_shedding_mwh_th": dispatch["heat_shedding_mw_th"].sum(),
                "renewable_curtailment_mwh": dispatch["pv_curtailment_mw"].sum() + dispatch["wind_curtailment_mw"].sum(),
                "grid_import_mwh": dispatch["grid_import_mw"].sum(),
                "chp_electric_mwh": dispatch["chp_electric_mw"].sum(),
                "heat_pump_heat_mwh_th": dispatch["heat_pump_heat_mw_th"].sum(),
            }
        )
    pd.DataFrame(rows).to_csv(SOURCE_DIR / "typical_day_dispatch_summary.csv", index=False)


def main() -> None:
    configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    solved = solve_typical_days()
    frames: dict[str, pd.DataFrame] = {}
    for label, result in solved.items():
        dispatch = result.frame.copy()
        frames[label] = dispatch
        dispatch.to_csv(SOURCE_DIR / f"{label}_day_dispatch.csv", index_label="utc_timestamp")
        plot_dispatch_day(label, dispatch)
        print(f"{label}_day={dispatch.index[0]:%Y-%m-%d}, objective_eur={result.objective_eur:.2f}")
    write_summary(frames)
    print(f"output_dir={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
