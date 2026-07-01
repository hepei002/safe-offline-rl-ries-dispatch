from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import (
    ACTION_NAMES,
    OBSERVATION_NAMES,
    IntegratedEnergyEnv,
    encode_dispatch_action,
)
from src.optimization.deterministic_dispatch import solve_dispatch_day
from src.policies.random_policy import run_safe_random_policy
from src.policies.rolling_mpc import run_rolling_mpc
from src.policies.rule_based import run_rule_based_policy
from src.safety.costs import split_safety_cost


POLICY_NAMES = [
    "perfect_information_lp",
    "rolling_mpc",
    "noisy_rolling_mpc",
    "rule_based",
    "safe_random",
]


def episode_hours_from_config(dataset_config: dict) -> int:
    if "episode_hours" in dataset_config:
        return int(dataset_config["episode_hours"])
    return int(dataset_config["source_period"]["episode_hours"])


def lookahead_hours_from_config(dataset_config: dict) -> int:
    if "lookahead_hours" in dataset_config:
        return int(dataset_config["lookahead_hours"])
    source = dataset_config.get("source_period", {})
    return int(source.get("lookahead_hours", episode_hours_from_config(dataset_config)))


def build_transition_frame(
    frame: pd.DataFrame,
    dispatch: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    *,
    quality: str,
    policy_name: str,
    episode_id: str,
    start_index: int,
) -> pd.DataFrame:
    """Replay a physical dispatch table in the Gymnasium environment."""

    env = IntegratedEnergyEnv(
        frame,
        system_config,
        policy_config,
        episode_hours=len(dispatch),
        start_index=start_index,
    )
    observation, info = env.reset(seed=0, options={"start_index": start_index})
    records: list[dict[str, float | int | str | bool]] = []
    for step, (_, dispatch_row) in enumerate(dispatch.iterrows()):
        action = encode_dispatch_action(dispatch_row, system_config)
        next_observation, reward, terminated, truncated, step_info = env.step(action)
        record: dict[str, float | int | str | bool] = {
            "quality": quality,
            "policy": policy_name,
            "episode_id": episode_id,
            "step": step,
            "utc_timestamp": step_info["utc_timestamp"],
            "reward": float(reward),
            "cost": float(-reward),
            "safety_cost": float(step_info["safety_cost"]),
            "hard_safety_cost": float(step_info["hard_safety_cost"]),
            "soft_operation_cost": float(step_info["soft_operation_cost"]),
            "terminal": bool(terminated),
            "truncated": bool(truncated),
        }
        for name, value in zip(OBSERVATION_NAMES, observation):
            record[f"obs_{name}"] = float(value)
        for name, value in zip(ACTION_NAMES, action):
            record[f"action_{name}"] = float(value)
        for name, value in zip(OBSERVATION_NAMES, next_observation):
            record[f"next_obs_{name}"] = float(value)
        dispatch_info = step_info["dispatch"]
        for key in [
            "grid_import_mw",
            "grid_export_mw",
            "chp_electric_mw",
            "heat_pump_heat_mw_th",
            "battery_soc_mwh",
            "thermal_soc_mwh_th",
            "electric_shedding_mw",
            "heat_shedding_mw_th",
            "heat_dump_mw_th",
            "pv_curtailment_mw",
            "wind_curtailment_mw",
            "electric_balance_residual_mw",
            "heat_balance_residual_mw_th",
        ]:
            record[key] = float(dispatch_info[key])
        split = split_safety_cost(dispatch_info)
        record["hard_safety_cost"] = split["hard_safety_cost"]
        record["soft_operation_cost"] = split["soft_operation_cost"]
        record["safety_cost"] = split["safety_cost"]
        records.append(record)
        observation = next_observation
    return pd.DataFrame(records)


def choose_policy_for_episode(
    policy_mix: Mapping[str, float],
    episode_number: int,
) -> str:
    """Deterministically allocate episodes according to cumulative mix weights."""

    if not policy_mix:
        raise ValueError("policy_mix must not be empty")
    names = list(policy_mix.keys())
    weights = np.asarray([float(policy_mix[name]) for name in names], dtype=float)
    if (weights < 0).any() or weights.sum() <= 0.0:
        raise ValueError("policy_mix weights must be non-negative and sum to a positive value")
    cumulative = np.cumsum(weights / weights.sum())
    value = ((episode_number * 9973) % 10000) / 10000.0
    return names[int(np.searchsorted(cumulative, value, side="right"))]


def make_policy_schedule(policy_mix: Mapping[str, float], episodes: int) -> list[str]:
    """Allocate a finite episode schedule that closely matches mix weights."""

    if episodes <= 0:
        raise ValueError("episodes must be positive")
    names = list(policy_mix.keys())
    weights = np.asarray([float(policy_mix[name]) for name in names], dtype=float)
    if (weights < 0).any() or weights.sum() <= 0.0:
        raise ValueError("policy_mix weights must be non-negative and sum to a positive value")
    expected = weights / weights.sum() * episodes
    counts = np.floor(expected).astype(int)
    remainder = episodes - int(counts.sum())
    if remainder > 0:
        order = np.argsort(-(expected - counts))
        for idx in order[:remainder]:
            counts[idx] += 1
    schedule: list[str] = []
    for name, count in zip(names, counts):
        schedule.extend([name] * int(count))
    # Interleave policies so early subsets are mixed instead of block-ordered.
    interleaved = sorted(
        enumerate(schedule),
        key=lambda item: ((item[0] % max(len(names), 1)), item[0]),
    )
    return [name for _, name in interleaved]


def run_policy_dispatch(
    policy_name: str,
    frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    *,
    episode_hours: int,
    seed: int,
) -> pd.DataFrame:
    """Generate one episode of physical dispatch for a named behavior policy."""

    episode_frame = frame.iloc[:episode_hours].copy()
    if policy_name == "perfect_information_lp":
        return solve_dispatch_day(
            episode_frame,
            system_config,
            policy_config,
            enforce_terminal_soc=True,
        ).frame
    if policy_name == "rolling_mpc":
        return run_rolling_mpc(
            frame,
            system_config,
            policy_config,
            evaluation_hours=episode_hours,
            noisy=False,
            seed=seed,
        )
    if policy_name == "noisy_rolling_mpc":
        return run_rolling_mpc(
            frame,
            system_config,
            policy_config,
            evaluation_hours=episode_hours,
            noisy=True,
            seed=seed,
        )
    if policy_name == "rule_based":
        return run_rule_based_policy(episode_frame, system_config, policy_config)
    if policy_name == "safe_random":
        return run_safe_random_policy(
            episode_frame,
            system_config,
            policy_config,
            seed=seed,
        )
    raise ValueError(f"unknown policy_name: {policy_name}")


def generate_quality_dataset(
    full_frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    dataset_config: dict,
    quality: str,
) -> pd.DataFrame:
    episode_hours = episode_hours_from_config(dataset_config)
    lookahead_hours = lookahead_hours_from_config(dataset_config)
    quality_config = dataset_config["qualities"][quality]
    episodes = int(quality_config["episodes"])
    policy_mix = quality_config["policy_mix"]
    start_offset = int(quality_config.get("start_offset_hours", 0))
    stride = int(quality_config.get("stride_hours", episode_hours))
    seed_base = int(quality_config.get("seed", 1000))

    schedule = make_policy_schedule(policy_mix, episodes)

    parts: list[pd.DataFrame] = []
    for episode_number in range(episodes):
        start = start_offset + episode_number * stride
        end = start + max(episode_hours, lookahead_hours)
        if end > len(full_frame):
            break
        policy_name = schedule[episode_number]
        episode_frame = full_frame.iloc[start:end].copy()
        dispatch = run_policy_dispatch(
            policy_name,
            episode_frame,
            system_config,
            policy_config,
            episode_hours=episode_hours,
            seed=seed_base + episode_number,
        )
        transitions = build_transition_frame(
            episode_frame.iloc[:episode_hours],
            dispatch.iloc[:episode_hours],
            system_config,
            policy_config,
            quality=quality,
            policy_name=policy_name,
            episode_id=f"{quality}_{episode_number:04d}",
            start_index=0,
        )
        parts.append(transitions)
    if not parts:
        raise ValueError(f"no episodes generated for quality={quality}")
    return pd.concat(parts, ignore_index=True)


def generate_offline_datasets(
    full_frame: pd.DataFrame,
    system_config: dict,
    policy_config: dict,
    dataset_config: dict,
    output_dir: Path,
) -> dict[str, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets: dict[str, pd.DataFrame] = {}
    for quality in dataset_config["qualities"]:
        dataset = generate_quality_dataset(
            full_frame,
            system_config,
            policy_config,
            dataset_config,
            quality,
        )
        dataset.to_parquet(output_dir / f"{quality}.parquet", index=False)
        datasets[quality] = dataset
    summary = summarize_dataset_quality(datasets)
    summary.to_csv(output_dir / "dataset_quality_summary.csv", index=False)
    return datasets


def summarize_dataset_quality(datasets: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    action_columns = [column for column in next(iter(datasets.values())).columns if column.startswith("action_")]
    obs_columns = [column for column in next(iter(datasets.values())).columns if column.startswith("obs_")]
    for quality, dataset in datasets.items():
        episode_returns = dataset.groupby("episode_id")["reward"].sum()
        episode_safety = dataset.groupby("episode_id")["safety_cost"].sum()
        episode_hard = dataset.groupby("episode_id")["hard_safety_cost"].sum()
        episode_soft = dataset.groupby("episode_id")["soft_operation_cost"].sum()
        rows.append(
            {
                "quality": quality,
                "transitions": int(len(dataset)),
                "episodes": int(dataset["episode_id"].nunique()),
                "policy_mix_observed": ";".join(
                    f"{name}:{count}"
                    for name, count in dataset["policy"].value_counts().sort_index().items()
                ),
                "mean_reward": float(dataset["reward"].mean()),
                "mean_episode_return": float(episode_returns.mean()),
                "p10_episode_return": float(episode_returns.quantile(0.10)),
                "p90_episode_return": float(episode_returns.quantile(0.90)),
                "mean_safety_cost": float(dataset["safety_cost"].mean()),
                "mean_episode_safety_cost": float(episode_safety.mean()),
                "mean_hard_safety_cost": float(dataset["hard_safety_cost"].mean()),
                "mean_episode_hard_safety_cost": float(episode_hard.mean()),
                "mean_soft_operation_cost": float(dataset["soft_operation_cost"].mean()),
                "mean_episode_soft_operation_cost": float(episode_soft.mean()),
                "unsafe_transition_rate": float((dataset["hard_safety_cost"] > 1e-9).mean()),
                "action_coverage_score": float(dataset[action_columns].std(ddof=0).mean()),
                "state_coverage_score": float(dataset[obs_columns].std(ddof=0).mean()),
            }
        )
    return pd.DataFrame(rows)
