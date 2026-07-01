from __future__ import annotations

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.system_profiles import choose_representative_day, scale_series_to_peak


CONFIG_PATH = ROOT / "configs" / "system.yaml"
JOINT_PATH = ROOT / "data" / "processed" / "exogenous" / "germany_joint_hourly_2017_2019.csv"
OPSD_PATH = ROOT / "data" / "raw" / "opsd" / "time_series_60min_singleindex.csv"
OUTPUT_DIR = ROOT / "results" / "figures" / "system_profiles"
SOURCE_DIR = OUTPUT_DIR / "source_data"

PALETTE = {
    "electricity": "#335C81",
    "heat": "#C95D4B",
    "solar": "#E3A62F",
    "wind": "#6C9A8B",
    "temperature": "#6F6AA8",
    "cop": "#3D8B8B",
    "band_electricity": "#B8CCE0",
    "band_heat": "#E7B5AC",
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


def load_profiles() -> tuple[pd.DataFrame, dict]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    frame = pd.read_csv(JOINT_PATH)
    frame["utc_timestamp"] = pd.to_datetime(frame["utc_timestamp"], utc=True)
    frame = frame.set_index("utc_timestamp")

    frame["electric_load_mw"], _ = scale_series_to_peak(
        frame["electric_load_actual_mw"],
        target_peak=config["data_scaling"]["electricity"]["target_peak_mw"],
    )
    frame["heat_load_mw_th"], _ = scale_series_to_peak(
        frame["heat_demand_reference_2015_mw"],
        target_peak=config["data_scaling"]["heat"]["target_peak_mw_th"],
    )

    renewable_columns = [
        "utc_timestamp",
        "DE_solar_capacity",
        "DE_solar_generation_actual",
        "DE_wind_capacity",
        "DE_wind_generation_actual",
    ]
    renewable = pd.read_csv(OPSD_PATH, usecols=renewable_columns, low_memory=False)
    renewable["utc_timestamp"] = pd.to_datetime(renewable["utc_timestamp"], utc=True)
    renewable = renewable.set_index("utc_timestamp").reindex(frame.index)
    capacities = renewable[["DE_solar_capacity", "DE_wind_capacity"]].ffill().bfill()
    solar_cf = (
        renewable["DE_solar_generation_actual"] / capacities["DE_solar_capacity"]
    ).clip(0.0, 1.0)
    wind_cf = (
        renewable["DE_wind_generation_actual"] / capacities["DE_wind_capacity"]
    ).clip(0.0, 1.0)
    frame["solar_available_mw"] = (
        solar_cf * config["renewables"]["photovoltaic"]["capacity_mw"]
    )
    frame["wind_available_mw"] = (
        wind_cf * config["renewables"]["wind"]["capacity_mw"]
    )
    return frame, config


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        va="top",
    )


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")


def plot_typical_days(frame: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    features = ["electric_load_mw", "heat_load_mw_th", "temperature_c"]
    winter_day = choose_representative_day(
        frame,
        months=[12, 1, 2],
        feature_columns=features,
    )
    summer_day = choose_representative_day(
        frame,
        months=[6, 7, 8],
        feature_columns=features,
    )

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), sharex="col")
    for column, (day, season) in enumerate(
        [(winter_day, "Representative winter day"), (summer_day, "Representative summer day")]
    ):
        day_data = frame.loc[day : day + pd.Timedelta(hours=23)].copy()
        hours = np.arange(24)
        ax = axes[0, column]
        ax.plot(hours, day_data["electric_load_mw"], color=PALETTE["electricity"], lw=1.8, label="Electric load")
        ax.plot(hours, day_data["heat_load_mw_th"], color=PALETTE["heat"], lw=1.8, label="Heat load")
        ax.fill_between(hours, 0, day_data["solar_available_mw"], color=PALETTE["solar"], alpha=0.35, label="PV available")
        ax.fill_between(hours, day_data["solar_available_mw"], day_data["solar_available_mw"] + day_data["wind_available_mw"], color=PALETTE["wind"], alpha=0.32, label="Wind available")
        ax.set_title(f"{season}\n{day:%Y-%m-%d}")
        ax.set_ylabel("Power (MW)")
        ax.set_xlim(0, 23)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)
        if column == 0:
            ax.legend(ncol=2, loc="upper left")
        panel_label(ax, "a" if column == 0 else "c")

        ax2 = axes[1, column]
        ax2.plot(hours, day_data["temperature_c"], color=PALETTE["temperature"], lw=1.8, label="Temperature")
        ax2.set_ylabel("Temperature (°C)", color=PALETTE["temperature"])
        ax2.tick_params(axis="y", colors=PALETTE["temperature"])
        ax2.set_xlabel("Hour (UTC)")
        ax2.set_xticks([0, 4, 8, 12, 16, 20, 23])
        ax2.grid(axis="y", color="#D9D9D9", lw=0.5)
        twin = ax2.twinx()
        twin.plot(hours, day_data["cop_ashp_radiator"], color=PALETTE["cop"], lw=1.6, ls="--", label="ASHP COP")
        twin.set_ylabel("COP", color=PALETTE["cop"])
        twin.tick_params(axis="y", colors=PALETTE["cop"])
        twin.spines["top"].set_visible(False)
        lines = ax2.lines + twin.lines
        ax2.legend(lines, [line.get_label() for line in lines], loc="upper left")
        panel_label(ax2, "b" if column == 0 else "d")
        day_data.assign(hour_utc=hours).to_csv(
            SOURCE_DIR / f"typical_{'winter' if column == 0 else 'summer'}_{day:%Y-%m-%d}.csv",
            index_label="utc_timestamp",
        )

    fig.suptitle(
        "Scaled industrial-park demand and renewable availability on representative days",
        fontsize=9,
        y=1.01,
    )
    fig.tight_layout()
    save_figure(fig, OUTPUT_DIR / "typical_days")
    plt.close(fig)
    return winter_day, summer_day


def monthly_quantiles(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = frame[column].groupby(frame.index.month)
    return pd.DataFrame(
        {
            "p25": grouped.quantile(0.25),
            "median": grouped.median(),
            "p75": grouped.quantile(0.75),
            "mean": grouped.mean(),
        }
    )


def plot_annual_distribution(frame: pd.DataFrame) -> None:
    months = np.arange(1, 13)
    month_labels = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    electricity = monthly_quantiles(frame, "electric_load_mw")
    heat = monthly_quantiles(frame, "heat_load_mw_th")
    solar = monthly_quantiles(frame, "solar_available_mw")
    wind = monthly_quantiles(frame, "wind_available_mw")
    temperature = monthly_quantiles(frame, "temperature_c")
    cop = monthly_quantiles(frame, "cop_ashp_radiator")

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2), sharex=True)
    ax = axes[0, 0]
    ax.fill_between(months, electricity["p25"], electricity["p75"], color=PALETTE["band_electricity"], alpha=0.65)
    ax.plot(months, electricity["median"], color=PALETTE["electricity"], marker="o", ms=3, label="Electric load")
    ax.fill_between(months, heat["p25"], heat["p75"], color=PALETTE["band_heat"], alpha=0.55)
    ax.plot(months, heat["median"], color=PALETTE["heat"], marker="o", ms=3, label="Heat load")
    ax.set_ylabel("Hourly load (MW)")
    ax.legend()
    panel_label(ax, "a")

    ax = axes[0, 1]
    ax.plot(months, solar["mean"], color=PALETTE["solar"], marker="o", ms=3, label="PV available")
    ax.plot(months, wind["mean"], color=PALETTE["wind"], marker="o", ms=3, label="Wind available")
    ax.set_ylabel("Monthly mean power (MW)")
    ax.legend()
    panel_label(ax, "b")

    ax = axes[1, 0]
    ax.fill_between(months, temperature["p25"], temperature["p75"], color="#D7D4E8", alpha=0.7)
    ax.plot(months, temperature["median"], color=PALETTE["temperature"], marker="o", ms=3)
    ax.set_ylabel("Temperature (°C)")
    ax.set_xlabel("Month")
    panel_label(ax, "c")

    ax = axes[1, 1]
    ax.fill_between(months, cop["p25"], cop["p75"], color="#C8E0DF", alpha=0.75)
    ax.plot(months, cop["median"], color=PALETTE["cop"], marker="o", ms=3)
    ax.set_ylabel("ASHP COP")
    ax.set_xlabel("Month")
    panel_label(ax, "d")

    for ax in axes.flat:
        ax.set_xticks(months)
        ax.set_xticklabels(month_labels)
        ax.grid(axis="y", color="#D9D9D9", lw=0.5)

    fig.suptitle(
        "Annual distributions reveal seasonal electricity–heat–renewable complementarity",
        fontsize=9,
        y=1.01,
    )
    fig.tight_layout()
    save_figure(fig, OUTPUT_DIR / "annual_distribution")
    plt.close(fig)

    source = pd.concat(
        {
            "electric_load": electricity,
            "heat_load": heat,
            "solar_available": solar,
            "wind_available": wind,
            "temperature": temperature,
            "cop_ashp_radiator": cop,
        },
        axis=1,
    )
    source.index.name = "month"
    source.to_csv(SOURCE_DIR / "annual_monthly_statistics.csv")


def main() -> None:
    configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    frame, _ = load_profiles()
    winter_day, summer_day = plot_typical_days(frame)
    plot_annual_distribution(frame)
    print(f"winter_day={winter_day:%Y-%m-%d}")
    print(f"summer_day={summer_day:%Y-%m-%d}")
    print(f"output_dir={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
