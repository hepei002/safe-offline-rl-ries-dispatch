from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.policies.common import policy_cost
from src.policies.rule_based import run_rule_based_policy


def cvar(values: list[float], alpha: float = 0.90) -> float:
    if not values:
        return 0.0
    arr = np.asarray(values, dtype=float)
    threshold = np.quantile(arr, alpha)
    tail = arr[arr >= threshold]
    return float(tail.mean()) if len(tail) else float(arr.max())


def evaluate_policy_on_frame(
    policy: Any,
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    episode_starts: list[int],
    episode_hours: int,
) -> dict[str, float | int]:
    episode_costs: list[float] = []
    episode_safety: list[float] = []
    episode_hard_safety: list[float] = []
    decision_times_ms: list[float] = []
    for start in episode_starts:
        env = IntegratedEnergyEnv(
            frame,
            system_config,
            cost_config,
            episode_hours=episode_hours,
            start_index=start,
        )
        observation, _ = env.reset(seed=0, options={"start_index": start})
        total_cost = 0.0
        total_safety = 0.0
        total_hard_safety = 0.0
        terminated = False
        while not terminated:
            tic = time.perf_counter()
            action = policy.predict(observation)
            decision_times_ms.append((time.perf_counter() - tic) * 1000.0)
            observation, reward, terminated, truncated, info = env.step(action)
            total_cost += -float(reward)
            total_safety += float(info["safety_cost"])
            dispatch = info["dispatch"]
            total_hard_safety += float(dispatch["electric_shedding_mw"] + dispatch["heat_shedding_mw_th"])
            if truncated:
                break
        episode_costs.append(total_cost)
        episode_safety.append(total_safety)
        episode_hard_safety.append(total_hard_safety)
    return {
        "episodes": len(episode_costs),
        "mean_episode_cost_eur": float(np.mean(episode_costs)),
        "cvar90_episode_cost_eur": cvar(episode_costs, 0.90),
        "mean_episode_safety_cost": float(np.mean(episode_safety)),
        "mean_episode_hard_safety_cost": float(np.mean(episode_hard_safety)),
        "unsafe_episode_rate": float(np.mean(np.asarray(episode_safety) > 1e-9)),
        "mean_decision_time_ms": float(np.mean(decision_times_ms)),
    }


def evaluate_rule_policy_on_frame(
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    episode_starts: list[int],
    episode_hours: int,
) -> dict[str, float | int]:
    episode_costs: list[float] = []
    episode_safety: list[float] = []
    episode_hard_safety: list[float] = []
    decision_times_ms: list[float] = []
    for start in episode_starts:
        episode = frame.iloc[start : start + episode_hours].copy()
        tic = time.perf_counter()
        dispatch = run_rule_based_policy(episode, system_config, cost_config)
        decision_times_ms.extend([((time.perf_counter() - tic) * 1000.0) / max(episode_hours, 1)] * episode_hours)
        episode_costs.append(policy_cost(dispatch, system_config, cost_config))
        episode_safety.append(
            float(
                (
                    dispatch["electric_shedding_mw"]
                    + dispatch["heat_shedding_mw_th"]
                    + dispatch["heat_dump_mw_th"]
                    + dispatch["pv_curtailment_mw"]
                    + dispatch["wind_curtailment_mw"]
                ).sum()
            )
        )
        episode_hard_safety.append(
            float((dispatch["electric_shedding_mw"] + dispatch["heat_shedding_mw_th"]).sum())
        )
    return {
        "episodes": len(episode_costs),
        "mean_episode_cost_eur": float(np.mean(episode_costs)),
        "cvar90_episode_cost_eur": cvar(episode_costs, 0.90),
        "mean_episode_safety_cost": float(np.mean(episode_safety)),
        "mean_episode_hard_safety_cost": float(np.mean(episode_hard_safety)),
        "unsafe_episode_rate": float(np.mean(np.asarray(episode_safety) > 1e-9)),
        "mean_decision_time_ms": float(np.mean(decision_times_ms)),
    }
