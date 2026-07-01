from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHIFT_PROTOCOL_PATH = ROOT / "configs" / "shift_protocol.yaml"


@dataclass(frozen=True)
class ShiftScenario:
    name: str
    family: str
    description: str
    parameters: dict[str, float]


@dataclass(frozen=True)
class ShiftProtocol:
    name: str
    schema_version: str
    description: str
    reference_distribution: dict[str, Any]
    evaluation: dict[str, Any]
    ood: dict[str, Any]
    scenarios: list[ShiftScenario]


TRACKED_COLUMNS = [
    "electric_load_mw",
    "heat_load_mw_th",
    "pv_available_mw",
    "wind_available_mw",
    "cop_ashp_radiator",
    "temperature_c",
]


def load_shift_protocol(path: str | Path = DEFAULT_SHIFT_PROTOCOL_PATH) -> ShiftProtocol:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    scenarios = [
        ShiftScenario(
            name=str(item["name"]),
            family=str(item.get("family", "unspecified")),
            description=str(item.get("description", "")),
            parameters={str(k): float(v) for k, v in item.get("parameters", {}).items()},
        )
        for item in payload["scenarios"]
    ]
    return ShiftProtocol(
        name=str(payload.get("name", "shift_protocol")),
        schema_version=str(payload.get("schema_version", "1.0")),
        description=str(payload.get("description", "")),
        reference_distribution=dict(payload.get("reference_distribution", {})),
        evaluation=dict(payload.get("evaluation", {})),
        ood=dict(payload.get("ood", {})),
        scenarios=scenarios,
    )


def apply_shift_protocol(frame: pd.DataFrame, scenario: ShiftScenario) -> tuple[pd.DataFrame, dict[str, float | str]]:
    shifted = frame.copy()
    params = scenario.parameters
    multipliers = {
        "electric_load_mw": float(params.get("electric_load_multiplier", 1.0)),
        "heat_load_mw_th": float(params.get("heat_load_multiplier", 1.0)),
        "pv_available_mw": float(params.get("pv_multiplier", 1.0)),
        "wind_available_mw": float(params.get("wind_multiplier", 1.0)),
        "cop_ashp_radiator": float(params.get("cop_multiplier", 1.0)),
    }
    for column, multiplier in multipliers.items():
        if column in shifted.columns:
            shifted[column] = shifted[column].astype(float) * multiplier
    if "temperature_c" in shifted.columns:
        shifted["temperature_c"] = shifted["temperature_c"].astype(float) + float(params.get("temperature_delta_c", 0.0))
    if "cop_ashp_radiator" in shifted.columns:
        shifted["cop_ashp_radiator"] = shifted["cop_ashp_radiator"].clip(lower=1.0)
    for column in ["pv_available_mw", "wind_available_mw"]:
        if column in shifted.columns:
            shifted[column] = shifted[column].clip(lower=0.0)

    metadata: dict[str, float | str] = {
        "scenario": scenario.name,
        "family": scenario.family,
    }
    for column in TRACKED_COLUMNS:
        if column in frame.columns and column in shifted.columns:
            before = frame[column].astype(float).to_numpy()
            after = shifted[column].astype(float).to_numpy()
            denom = np.maximum(np.abs(before), 1e-6)
            relative = np.abs(after - before) / denom
            metadata[f"{column}_relative_change"] = float(np.mean(relative))
            metadata[f"{column}_mean_before"] = float(np.mean(before))
            metadata[f"{column}_mean_after"] = float(np.mean(after))
    change_values = [value for key, value in metadata.items() if key.endswith("_relative_change")]
    metadata["mean_absolute_relative_change"] = float(np.mean(change_values)) if change_values else 0.0
    return shifted, metadata


def summarize_shift_protocol(frame: pd.DataFrame, scenarios: Iterable[ShiftScenario]) -> pd.DataFrame:
    rows = []
    for scenario in scenarios:
        _, metadata = apply_shift_protocol(frame, scenario)
        rows.append(
            {
                "scenario": scenario.name,
                "family": scenario.family,
                "description": scenario.description,
                **metadata,
            }
        )
    return pd.DataFrame(rows)


def scenario_by_name(protocol: ShiftProtocol, name: str) -> ShiftScenario:
    for scenario in protocol.scenarios:
        if scenario.name == name:
            return scenario
    raise KeyError(f"unknown shift scenario: {name}")
