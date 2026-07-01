from __future__ import annotations

from collections.abc import Mapping


def _get(dispatch: Mapping[str, float], key: str) -> float:
    return float(dispatch.get(key, 0.0))


def split_safety_cost(dispatch: Mapping[str, float]) -> dict[str, float]:
    """Split hard supply risk from soft operation-quality penalties."""

    hard = _get(dispatch, "electric_shedding_mw") + _get(dispatch, "heat_shedding_mw_th")
    soft = (
        _get(dispatch, "heat_dump_mw_th")
        + _get(dispatch, "pv_curtailment_mw")
        + _get(dispatch, "wind_curtailment_mw")
    )
    return {
        "hard_safety_cost": hard,
        "soft_operation_cost": soft,
        "safety_cost": hard + soft,
    }

