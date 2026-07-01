from __future__ import annotations

import numpy as np

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.safety.costs import split_safety_cost


def dispatch_split(env: IntegratedEnergyEnv, action: np.ndarray) -> dict[str, float]:
    dispatch = env._dispatch_from_action(env._current_row(), action).iloc[0].to_dict()
    return split_safety_cost(dispatch)


def project_action(env: IntegratedEnergyEnv, action: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    """Greedy one-step physical safety projection in normalized action space.

    The projection prioritizes removing electric/heat shedding. It searches a
    small deterministic candidate set that increases supply and relaxes
    charging loads, then chooses the feasible action with minimum hard safety
    and shortest distance to the original action.
    """

    raw = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
    raw_split = dispatch_split(env, raw)
    candidates = [
        raw,
        np.asarray([max(raw[0], 0.0), max(raw[1], 0.0), min(raw[2], 0.0), min(raw[3], 0.0)], dtype=np.float32),
        np.asarray([max(raw[0], 0.5), max(raw[1], 0.5), min(raw[2], 0.0), min(raw[3], -0.5)], dtype=np.float32),
        np.asarray([1.0, max(raw[1], 0.5), min(raw[2], 0.0), min(raw[3], -0.5)], dtype=np.float32),
        np.asarray([max(raw[0], 0.5), 1.0, min(raw[2], 0.0), min(raw[3], -0.5)], dtype=np.float32),
        np.asarray([1.0, 1.0, min(raw[2], 0.0), min(raw[3], -0.5)], dtype=np.float32),
        np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32),
        np.asarray([1.0, 1.0, 0.0, -1.0], dtype=np.float32),
        np.asarray([1.0, 1.0, -1.0, 0.0], dtype=np.float32),
    ]
    best_action = raw
    best_split = raw_split
    best_distance = 0.0
    for candidate in candidates:
        candidate = np.clip(candidate, -1.0, 1.0)
        split = dispatch_split(env, candidate)
        distance = float(np.linalg.norm(candidate - raw))
        if (
            split["hard_safety_cost"] < best_split["hard_safety_cost"] - 1e-9
            or (
                abs(split["hard_safety_cost"] - best_split["hard_safety_cost"]) <= 1e-9
                and distance < best_distance
            )
        ):
            best_action = candidate
            best_split = split
            best_distance = distance
    return best_action.astype(np.float32), {
        "raw_hard_safety_cost": raw_split["hard_safety_cost"],
        "raw_soft_operation_cost": raw_split["soft_operation_cost"],
        "projected_hard_safety_cost": best_split["hard_safety_cost"],
        "projected_soft_operation_cost": best_split["soft_operation_cost"],
        "projection_distance_l2": float(np.linalg.norm(best_action - raw)),
    }


def evaluate_projected_actions(
    env: IntegratedEnergyEnv,
    actions: list[np.ndarray],
) -> dict[str, float]:
    raw_hard = 0.0
    raw_soft = 0.0
    projected_hard = 0.0
    projected_soft = 0.0
    distances: list[float] = []
    env.reset(seed=0)
    for action in actions:
        projected, report = project_action(env, action)
        raw_hard += report["raw_hard_safety_cost"]
        raw_soft += report["raw_soft_operation_cost"]
        projected_hard += report["projected_hard_safety_cost"]
        projected_soft += report["projected_soft_operation_cost"]
        distances.append(report["projection_distance_l2"])
        _, _, terminated, truncated, _ = env.step(projected)
        if terminated or truncated:
            break
    return {
        "raw_hard_safety_cost": raw_hard,
        "raw_soft_operation_cost": raw_soft,
        "projected_hard_safety_cost": projected_hard,
        "projected_soft_operation_cost": projected_soft,
        "mean_projection_distance_l2": float(np.mean(distances)) if distances else 0.0,
    }
