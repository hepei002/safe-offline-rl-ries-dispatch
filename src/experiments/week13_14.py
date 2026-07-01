from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.offline_rl.evaluation import cvar
from src.policies.common import policy_cost
from src.policies.rule_based import run_rule_based_policy
from src.safety.adaptive_layer import AdaptiveSafetyLayer
from src.safety.fixed_projection import FixedSafetyProjectionLayer


@dataclass
class ConstantPolicy:
    action: np.ndarray

    def predict(self, observation: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(self.action, dtype=np.float32), -1.0, 1.0)


def build_repeated_risk_scores(scores: list[float], episode_hours: int) -> list[float]:
    if not scores:
        return [0.0] * int(episode_hours)
    repeated: list[float] = []
    for score in scores:
        repeated.extend([float(score)] * int(episode_hours))
    return repeated


def evaluate_policy_with_safety_mode(
    policy: Any,
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    episode_starts: list[int],
    episode_hours: int,
    safety_mode: str = "none",
    fixed_layer: FixedSafetyProjectionLayer | None = None,
    adaptive_layer: AdaptiveSafetyLayer | None = None,
    risk_scores: Iterable[float] | None = None,
) -> dict[str, float | int]:
    episode_costs: list[float] = []
    episode_raw_hard: list[float] = []
    episode_hard: list[float] = []
    episode_safety: list[float] = []
    distances: list[float] = []
    weighted_distances: list[float] = []
    decision_times_ms: list[float] = []
    pass_through = 0
    partial = 0
    full = 0
    interventions = 0
    steps = 0
    risk_iter = iter(list(risk_scores) if risk_scores is not None else [])
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
        total_raw_hard = 0.0
        total_hard = 0.0
        total_safety = 0.0
        terminated = False
        while not terminated:
            tic = time.perf_counter()
            raw_action = policy.predict(observation)
            action = np.clip(np.asarray(raw_action, dtype=np.float32), -1.0, 1.0)
            distance = 0.0
            weighted_distance = 0.0
            mode = "pass_through"
            raw_hard_step = 0.0
            if safety_mode == "fixed":
                if fixed_layer is None:
                    raise ValueError("fixed_layer is required for fixed safety mode")
                result = fixed_layer.project(env, action)
                action = result.action
                distance = result.projection_distance_l2
                weighted_distance = result.weighted_projection_distance
                raw_hard_step = result.raw_hard_safety_cost
                mode = "full_projection" if distance > 1e-6 else "pass_through"
            elif safety_mode == "adaptive":
                if adaptive_layer is None:
                    raise ValueError("adaptive_layer is required for adaptive safety mode")
                try:
                    risk = next(risk_iter)
                except StopIteration:
                    risk = 0.0
                result = adaptive_layer.project(env, action, risk_score=float(risk))
                action = result.action
                distance = result.projection_distance_l2
                weighted_distance = result.weighted_projection_distance
                raw_hard_step = result.raw_hard_safety_cost
                mode = result.mode
            elif safety_mode == "ood_warning":
                try:
                    _ = next(risk_iter)
                except StopIteration:
                    pass
            elif safety_mode != "none":
                raise ValueError(f"unknown safety_mode: {safety_mode}")
            decision_times_ms.append((time.perf_counter() - tic) * 1000.0)
            observation, reward, terminated, truncated, info = env.step(action)
            hard = float(info["hard_safety_cost"])
            total_cost += -float(reward)
            total_hard += hard
            total_safety += float(info["safety_cost"])
            total_raw_hard += float(raw_hard_step if safety_mode in {"fixed", "adaptive"} else hard)
            distances.append(distance)
            weighted_distances.append(weighted_distance)
            interventions += int(distance > 1e-6)
            pass_through += int(mode == "pass_through")
            partial += int(mode == "partial_projection")
            full += int(mode == "full_projection")
            steps += 1
            if truncated:
                break
        episode_costs.append(total_cost)
        episode_raw_hard.append(total_raw_hard)
        episode_hard.append(total_hard)
        episode_safety.append(total_safety)
    return {
        "episodes": len(episode_costs),
        "raw_mean_episode_hard_safety_cost": float(np.mean(episode_raw_hard)),
        "mean_episode_cost_eur": float(np.mean(episode_costs)),
        "cvar90_episode_cost_eur": cvar(episode_costs, 0.90),
        "mean_episode_safety_cost": float(np.mean(episode_safety)),
        "mean_episode_hard_safety_cost": float(np.mean(episode_hard)),
        "unsafe_episode_rate": float(np.mean(np.asarray(episode_hard) > 1e-6)),
        "mean_projection_distance_l2": float(np.mean(distances)) if distances else 0.0,
        "mean_weighted_projection_distance": float(np.mean(weighted_distances)) if weighted_distances else 0.0,
        "mean_decision_time_ms": float(np.mean(decision_times_ms)) if decision_times_ms else 0.0,
        "intervention_rate": float(interventions / max(steps, 1)),
        "pass_through_rate": float(pass_through / max(steps, 1)),
        "partial_projection_rate": float(partial / max(steps, 1)),
        "full_projection_rate": float(full / max(steps, 1)),
    }


def evaluate_rule_dispatch(
    frame: pd.DataFrame,
    system_config: dict,
    cost_config: dict,
    *,
    episode_starts: list[int],
    episode_hours: int,
) -> dict[str, float | int]:
    costs = []
    hard = []
    safety = []
    decision_times = []
    for start in episode_starts:
        episode = frame.iloc[start : start + episode_hours].copy()
        tic = time.perf_counter()
        dispatch = run_rule_based_policy(episode, system_config, cost_config)
        elapsed = (time.perf_counter() - tic) * 1000.0 / max(episode_hours, 1)
        costs.append(policy_cost(dispatch, system_config, cost_config))
        hard_value = float((dispatch["electric_shedding_mw"] + dispatch["heat_shedding_mw_th"]).sum())
        hard.append(hard_value)
        safety.append(
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
        decision_times.extend([elapsed] * episode_hours)
    return {
        "episodes": len(costs),
        "raw_mean_episode_hard_safety_cost": float(np.mean(hard)),
        "mean_episode_cost_eur": float(np.mean(costs)),
        "cvar90_episode_cost_eur": cvar(costs, 0.90),
        "mean_episode_safety_cost": float(np.mean(safety)),
        "mean_episode_hard_safety_cost": float(np.mean(hard)),
        "unsafe_episode_rate": float(np.mean(np.asarray(hard) > 1e-6)),
        "mean_projection_distance_l2": 0.0,
        "mean_weighted_projection_distance": 0.0,
        "mean_decision_time_ms": float(np.mean(decision_times)),
        "intervention_rate": 0.0,
        "pass_through_rate": 1.0,
        "partial_projection_rate": 0.0,
        "full_projection_rate": 0.0,
    }


def summarize_main_results(results: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    defaults = {
        "seed": 0,
        "cvar90_episode_cost_eur": results["mean_episode_cost_eur"] if "mean_episode_cost_eur" in results else 0.0,
        "mean_episode_hard_safety_cost": 0.0,
        "unsafe_episode_rate": 0.0,
        "mean_projection_distance_l2": 0.0,
        "intervention_rate": 0.0,
        "mean_decision_time_ms": 0.0,
    }
    for column, default in defaults.items():
        if column not in results.columns:
            results[column] = default
    grouped = results.groupby(["method", "scenario"], as_index=False)
    return grouped.agg(
        seeds=("seed", "nunique") if "seed" in results.columns else ("method", "size"),
        mean_episode_cost_eur=("mean_episode_cost_eur", "mean"),
        std_episode_cost_eur=("mean_episode_cost_eur", "std"),
        cvar90_episode_cost_eur=("cvar90_episode_cost_eur", "mean"),
        mean_hard_safety_cost=("mean_episode_hard_safety_cost", "mean"),
        std_hard_safety_cost=("mean_episode_hard_safety_cost", "std"),
        unsafe_episode_rate=("unsafe_episode_rate", "mean"),
        mean_projection_distance_l2=("mean_projection_distance_l2", "mean"),
        intervention_rate=("intervention_rate", "mean"),
        mean_decision_time_ms=("mean_decision_time_ms", "mean"),
    ).fillna(0.0)


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    formatted = frame.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(lambda value: f"{value:.3f}")
        else:
            formatted[column] = formatted[column].astype(str)
    header = "| " + " | ".join(formatted.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(formatted.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in formatted.astype(str).to_numpy()]
    return "\n".join([header, separator, *rows])
