from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def scale_series_to_peak(
    values: pd.Series,
    *,
    target_peak: float,
) -> tuple[pd.Series, float]:
    peak = float(values.max())
    if peak <= 0:
        raise ValueError("source series peak must be positive")
    factor = float(target_peak) / peak
    return values.astype(float) * factor, factor


def choose_representative_day(
    frame: pd.DataFrame,
    *,
    months: Iterable[int],
    feature_columns: list[str],
) -> pd.Timestamp:
    selected = frame.loc[frame.index.month.isin(list(months)), feature_columns]
    if selected.empty:
        raise ValueError("no data available for requested months")

    daily = selected.resample("D").mean().dropna()
    spread = daily.std(ddof=0).replace(0.0, 1.0)
    standardized = (daily - daily.mean()) / spread
    target = standardized.median(axis=0)
    distance = np.sqrt(((standardized - target) ** 2).sum(axis=1))
    return pd.Timestamp(distance.idxmin())
