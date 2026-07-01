from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping

import pandas as pd


OPSD_COLUMNS = {
    "DE_load_actual_entsoe_transparency": "electric_load_actual_mw",
    "DE_solar_generation_actual": "solar_generation_actual_mw",
    "DE_wind_generation_actual": "wind_generation_actual_mw",
    "DE_wind_onshore_generation_actual": "wind_onshore_generation_actual_mw",
    "DE_wind_offshore_generation_actual": "wind_offshore_generation_actual_mw",
}

WEATHER_COLUMNS = {
    "DE_temperature": "temperature_c",
    "DE_radiation_direct_horizontal": "radiation_direct_horizontal_w_m2",
    "DE_radiation_diffuse_horizontal": "radiation_diffuse_horizontal_w_m2",
}

HEAT_PROFILE_COLUMNS = {
    "DE_heat_profile_space_COM": "heat_profile_space_com_mw_per_twh",
    "DE_heat_profile_space_MFH": "heat_profile_space_mfh_mw_per_twh",
    "DE_heat_profile_space_SFH": "heat_profile_space_sfh_mw_per_twh",
    "DE_heat_profile_water_COM": "heat_profile_water_com_mw_per_twh",
    "DE_heat_profile_water_MFH": "heat_profile_water_mfh_mw_per_twh",
    "DE_heat_profile_water_SFH": "heat_profile_water_sfh_mw_per_twh",
}

HEAT_DEMAND_COLUMNS = {
    "DE_heat_demand_space_COM": "heat_profile_space_com_mw_per_twh",
    "DE_heat_demand_space_MFH": "heat_profile_space_mfh_mw_per_twh",
    "DE_heat_demand_space_SFH": "heat_profile_space_sfh_mw_per_twh",
    "DE_heat_demand_water_COM": "heat_profile_water_com_mw_per_twh",
    "DE_heat_demand_water_MFH": "heat_profile_water_mfh_mw_per_twh",
    "DE_heat_demand_water_SFH": "heat_profile_water_sfh_mw_per_twh",
}

COP_COLUMNS = {
    "DE_COP_ASHP_floor": "cop_ashp_floor",
    "DE_COP_ASHP_radiator": "cop_ashp_radiator",
    "DE_COP_ASHP_water": "cop_ashp_water",
}


def normalize_hourly_utc(
    frame: pd.DataFrame,
    *,
    start: str,
    end: str,
    max_interpolation_gap: int,
    source_name: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return a unique, complete UTC-hourly frame with explicit imputation flags."""
    data = frame.copy()
    data["utc_timestamp"] = pd.to_datetime(
        data["utc_timestamp"], utc=True, errors="raise"
    )
    duplicate_rows = int(data["utc_timestamp"].duplicated().sum())
    numeric_columns = [column for column in data.columns if column != "utc_timestamp"]
    data = data.groupby("utc_timestamp", as_index=True)[numeric_columns].mean()

    hourly_index = pd.date_range(start=start, end=end, freq="h", tz="UTC")
    data = data.reindex(hourly_index)
    missing_before = data.isna()
    data = data.interpolate(
        method="time",
        limit=max_interpolation_gap,
        limit_area="inside",
    )
    if data.isna().any().any():
        unresolved = data.isna().sum()
        unresolved = unresolved[unresolved > 0].to_dict()
        raise ValueError(f"{source_name} has unresolved missing values: {unresolved}")

    imputed_column = f"imputed_{source_name}"
    data[imputed_column] = missing_before.any(axis=1)
    data.index.name = "utc_timestamp"
    report = {
        "duplicate_rows": duplicate_rows,
        "imputed_cells": int(missing_before.sum().sum()),
        "imputed_rows": int(missing_before.any(axis=1).sum()),
    }
    return data, report


def build_reference_heat_demand(
    profiles: pd.DataFrame,
    annual_twh: Mapping[str, float],
) -> pd.Series:
    """Scale normalized MW/TWh profiles using reference-year annual TWh weights."""
    result = pd.Series(0.0, index=profiles.index, dtype=float)
    for profile_name, weight_twh in annual_twh.items():
        result = result + profiles[profile_name] * float(weight_twh)
    return result


def _read_csv(
    path: Path,
    *,
    usecols: list[str],
    separator: str = ",",
    decimal: str = ".",
) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep=separator,
        decimal=decimal,
        usecols=usecols,
        low_memory=False,
    )


def _reference_heat_weights(when2heat_path: Path) -> dict[str, float]:
    columns = ["utc_timestamp", *HEAT_DEMAND_COLUMNS]
    demand = _read_csv(
        when2heat_path,
        usecols=columns,
        separator=";",
        decimal=",",
    )
    demand["utc_timestamp"] = pd.to_datetime(demand["utc_timestamp"], utc=True)
    demand = demand[demand["utc_timestamp"].dt.year == 2015]
    demand = demand.rename(columns=HEAT_DEMAND_COLUMNS)
    demand, _ = normalize_hourly_utc(
        demand,
        start="2015-01-01T00:00:00Z",
        end="2015-12-31T23:00:00Z",
        max_interpolation_gap=1,
        source_name="heat_reference",
    )
    return {
        column: float(demand[column].sum() / 1_000_000.0)
        for column in HEAT_DEMAND_COLUMNS.values()
    }


def build_joint_dataset(
    *,
    raw_root: str | Path,
    start_year: int,
    end_year: int,
) -> tuple[pd.DataFrame, dict]:
    raw_root = Path(raw_root)
    start = f"{start_year}-01-01T00:00:00Z"
    end = f"{end_year}-12-31T23:00:00Z"

    opsd_path = raw_root / "opsd" / "time_series_60min_singleindex.csv"
    weather_path = raw_root / "opsd_weather" / "weather_data.csv"
    when2heat_path = raw_root / "when2heat" / "when2heat.csv"

    opsd = _read_csv(
        opsd_path,
        usecols=["utc_timestamp", *OPSD_COLUMNS],
    ).rename(columns=OPSD_COLUMNS)
    opsd, opsd_report = normalize_hourly_utc(
        opsd,
        start=start,
        end=end,
        max_interpolation_gap=1,
        source_name="opsd",
    )

    weather = _read_csv(
        weather_path,
        usecols=["utc_timestamp", *WEATHER_COLUMNS],
    ).rename(columns=WEATHER_COLUMNS)
    weather, weather_report = normalize_hourly_utc(
        weather,
        start=start,
        end=end,
        max_interpolation_gap=1,
        source_name="weather",
    )

    when2heat = _read_csv(
        when2heat_path,
        usecols=["utc_timestamp", *COP_COLUMNS, *HEAT_PROFILE_COLUMNS],
        separator=";",
        decimal=",",
    ).rename(columns={**COP_COLUMNS, **HEAT_PROFILE_COLUMNS})
    when2heat, heat_report = normalize_hourly_utc(
        when2heat,
        start=start,
        end=end,
        max_interpolation_gap=1,
        source_name="when2heat",
    )

    annual_twh = _reference_heat_weights(when2heat_path)
    when2heat["heat_demand_reference_2015_mw"] = build_reference_heat_demand(
        when2heat,
        annual_twh,
    )

    joint = opsd.join(weather, how="inner").join(when2heat, how="inner")
    joint["radiation_global_horizontal_w_m2"] = (
        joint["radiation_direct_horizontal_w_m2"]
        + joint["radiation_diffuse_horizontal_w_m2"]
    )
    imputation_columns = [
        "imputed_opsd",
        "imputed_weather",
        "imputed_when2heat",
    ]
    joint["imputed_any"] = joint[imputation_columns].any(axis=1)
    joint.insert(0, "utc_timestamp", joint.index.strftime("%Y-%m-%dT%H:%M:%SZ"))
    joint = joint.reset_index(drop=True)

    if joint["utc_timestamp"].duplicated().any():
        raise ValueError("joint dataset contains duplicate UTC timestamps")
    if joint.isna().any().any():
        raise ValueError("joint dataset contains missing values")

    expected_rows = len(
        pd.date_range(start=start, end=end, freq="h", tz="UTC")
    )
    if len(joint) != expected_rows:
        raise ValueError(
            f"joint dataset has {len(joint)} rows, expected {expected_rows}"
        )

    report = {
        "period": {
            "start_utc": start,
            "end_utc": end,
            "rows": len(joint),
        },
        "opsd": opsd_report,
        "weather": weather_report,
        "when2heat": heat_report,
        "heat_reference_year": 2015,
        "heat_reference_annual_twh": {
            **annual_twh,
            "total": float(sum(annual_twh.values())),
        },
        "price_note": (
            "DE_LU day-ahead price is not included because it does not provide "
            "a complete 2017-2019 common window."
        ),
    }
    return joint, report


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_outputs(
    *,
    raw_root: str | Path,
    data_root: str | Path,
    start_year: int,
    end_year: int,
) -> dict:
    raw_root = Path(raw_root)
    data_root = Path(data_root)
    joint, report = build_joint_dataset(
        raw_root=raw_root,
        start_year=start_year,
        end_year=end_year,
    )

    output_name = f"germany_joint_hourly_{start_year}_{end_year}.csv"
    aligned_dir = data_root / "interim" / "aligned"
    processed_dir = data_root / "processed" / "exogenous"
    metadata_dir = data_root / "processed" / "metadata"
    aligned_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    aligned_path = aligned_dir / output_name
    processed_path = processed_dir / output_name
    joint.to_csv(aligned_path, index=False, float_format="%.6f")
    joint.to_csv(processed_path, index=False, float_format="%.6f")

    raw_files = [
        raw_root / "opsd" / "time_series_60min_singleindex.csv",
        raw_root / "opsd_weather" / "weather_data.csv",
        raw_root / "when2heat" / "when2heat.csv",
    ]
    report["raw_files"] = [
        {
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "modified": path.stat().st_mtime,
            "sha256": _sha256(path),
        }
        for path in raw_files
    ]
    report["output"] = {
        "path": processed_path.as_posix(),
        "bytes": processed_path.stat().st_size,
        "sha256": _sha256(processed_path),
        "columns": list(joint.columns),
    }
    report_path = metadata_dir / f"quality_report_{start_year}_{end_year}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2019)
    args = parser.parse_args()
    report = write_outputs(
        raw_root=args.raw_root,
        data_root=args.data_root,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
