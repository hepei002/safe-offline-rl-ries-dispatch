from __future__ import annotations

import numpy as np
import pandas as pd


def _multiply_with_noise(values: pd.Series, relative_std: float, rng: np.random.Generator) -> pd.Series:
    if relative_std <= 0.0:
        return values.astype(float).copy()
    multiplier = rng.normal(loc=1.0, scale=relative_std, size=len(values))
    return values.astype(float) * multiplier


def apply_forecast_error(frame: pd.DataFrame, policy_config: dict, seed: int | None = None) -> pd.DataFrame:
    """Apply seeded, physically clipped forecast errors to a look-ahead frame."""

    forecast = frame.copy()
    rng = np.random.default_rng(seed)
    error = policy_config.get("forecast_error", {})
    columns = {
        "electric_load_mw": "electric_load_relative_std",
        "heat_load_mw_th": "heat_load_relative_std",
        "pv_available_mw": "renewable_relative_std",
        "wind_available_mw": "renewable_relative_std",
        "cop_ashp_radiator": "cop_relative_std",
        "electricity_import_price_eur_per_mwh": "price_relative_std",
    }
    for column, setting in columns.items():
        if column in forecast.columns:
            forecast[column] = _multiply_with_noise(
                forecast[column],
                float(error.get(setting, 0.0)),
                rng,
            )
    lower_bounds = {
        "electric_load_mw": 0.0,
        "heat_load_mw_th": 0.0,
        "pv_available_mw": 0.0,
        "wind_available_mw": 0.0,
        "cop_ashp_radiator": 1.0,
        "electricity_import_price_eur_per_mwh": 0.0,
    }
    for column, lower in lower_bounds.items():
        if column in forecast.columns:
            forecast[column] = forecast[column].clip(lower=lower)
    return forecast

