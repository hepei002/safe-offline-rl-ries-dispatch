from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Iterable

import numpy as np

from src.envs.integrated_energy_env import IntegratedEnergyEnv
from src.safety.fixed_projection import FixedSafetyProjectionLayer, ProjectionResult
from src.safety.projection import dispatch_split


@dataclass(frozen=True)
class AdaptiveSafetyConfig:
    low_risk_threshold: float = 1.0
    high_risk_threshold: float = 3.0
    blend_grid_size: int = 11
    hard_safety_tolerance: float = 1e-6
    force_project_if_hard_violation: bool = True


@dataclass(frozen=True)
class AdaptiveProjectionResult:
    action: np.ndarray
    mode: str
    risk_score: float
    risk_weight: float
    raw_hard_safety_cost: float
    raw_soft_operation_cost: float
    projected_hard_safety_cost: float
    projected_soft_operation_cost: float
    projection_distance_l2: float
    weighted_projection_distance: float
    solve_time_ms: float
    base_status: str


class AdaptiveSafetyLayer:
    """OOD-aware safety layer that gates a fixed physical projection layer.

    Low-risk safe actions are passed through. High-risk or physically unsafe
    actions use the fixed projection. Medium-risk cases search along the line
    segment from the raw action to the fixed safe action and select the closest
    action that matches the fixed layer's hard-safety level.
    """

    def __init__(
        self,
        fixed_layer: FixedSafetyProjectionLayer,
        config: AdaptiveSafetyConfig | None = None,
    ) -> None:
        self.fixed_layer = fixed_layer
        self.config = config or AdaptiveSafetyConfig()

    def risk_weight(self, risk_score: float) -> float:
        low = float(self.config.low_risk_threshold)
        high = float(self.config.high_risk_threshold)
        if high <= low:
            return 1.0
        return float(np.clip((float(risk_score) - low) / (high - low), 0.0, 1.0))

    def project(
        self,
        env: IntegratedEnergyEnv,
        action: np.ndarray,
        *,
        risk_score: float,
    ) -> AdaptiveProjectionResult:
        tic = time.perf_counter()
        raw = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        raw_split = dispatch_split(env, raw)
        weight = self.risk_weight(risk_score)
        if (
            weight <= 0.0
            and raw_split["hard_safety_cost"] <= self.config.hard_safety_tolerance
        ):
            solve_time_ms = (time.perf_counter() - tic) * 1000.0
            return AdaptiveProjectionResult(
                action=raw,
                mode="pass_through",
                risk_score=float(risk_score),
                risk_weight=weight,
                raw_hard_safety_cost=float(raw_split["hard_safety_cost"]),
                raw_soft_operation_cost=float(raw_split["soft_operation_cost"]),
                projected_hard_safety_cost=float(raw_split["hard_safety_cost"]),
                projected_soft_operation_cost=float(raw_split["soft_operation_cost"]),
                projection_distance_l2=0.0,
                weighted_projection_distance=0.0,
                solve_time_ms=solve_time_ms,
                base_status="not_called",
            )

        fixed = self.fixed_layer.project(env, raw)
        if weight >= 1.0 or (
            self.config.force_project_if_hard_violation
            and raw_split["hard_safety_cost"] > self.config.hard_safety_tolerance
        ):
            return self._from_fixed(raw, risk_score, weight, fixed, "full_projection", tic)

        partial_action, partial_split = self._closest_feasible_blend(env, raw, fixed.action, fixed.projected_hard_safety_cost)
        distance = float(np.linalg.norm(partial_action - raw))
        weighted_distance = self.fixed_layer._weighted_distance(raw, partial_action)
        solve_time_ms = fixed.solve_time_ms + (time.perf_counter() - tic) * 1000.0
        mode = "partial_projection" if distance > 1e-9 else "pass_through"
        return AdaptiveProjectionResult(
            action=partial_action.astype(np.float32),
            mode=mode,
            risk_score=float(risk_score),
            risk_weight=weight,
            raw_hard_safety_cost=float(raw_split["hard_safety_cost"]),
            raw_soft_operation_cost=float(raw_split["soft_operation_cost"]),
            projected_hard_safety_cost=float(partial_split["hard_safety_cost"]),
            projected_soft_operation_cost=float(partial_split["soft_operation_cost"]),
            projection_distance_l2=distance,
            weighted_projection_distance=weighted_distance,
            solve_time_ms=float(solve_time_ms),
            base_status=fixed.status,
        )

    def _from_fixed(
        self,
        raw: np.ndarray,
        risk_score: float,
        weight: float,
        fixed: ProjectionResult,
        mode: str,
        tic: float,
    ) -> AdaptiveProjectionResult:
        return AdaptiveProjectionResult(
            action=fixed.action,
            mode=mode,
            risk_score=float(risk_score),
            risk_weight=float(weight),
            raw_hard_safety_cost=fixed.raw_hard_safety_cost,
            raw_soft_operation_cost=fixed.raw_soft_operation_cost,
            projected_hard_safety_cost=fixed.projected_hard_safety_cost,
            projected_soft_operation_cost=fixed.projected_soft_operation_cost,
            projection_distance_l2=fixed.projection_distance_l2,
            weighted_projection_distance=fixed.weighted_projection_distance,
            solve_time_ms=float(fixed.solve_time_ms + (time.perf_counter() - tic) * 1000.0),
            base_status=fixed.status,
        )

    def _closest_feasible_blend(
        self,
        env: IntegratedEnergyEnv,
        raw: np.ndarray,
        fixed_action: np.ndarray,
        target_hard_cost: float,
    ) -> tuple[np.ndarray, dict[str, float]]:
        best_action = fixed_action.astype(np.float32)
        best_split = dispatch_split(env, best_action)
        target = float(target_hard_cost) + self.config.hard_safety_tolerance
        for alpha in np.linspace(0.0, 1.0, max(int(self.config.blend_grid_size), 2)):
            candidate = raw + float(alpha) * (fixed_action - raw)
            candidate = np.clip(candidate.astype(np.float32), -1.0, 1.0)
            split = dispatch_split(env, candidate)
            if split["hard_safety_cost"] <= target:
                best_action = candidate
                best_split = split
                break
        return best_action, best_split


def evaluate_adaptive_safety_layer(
    env: IntegratedEnergyEnv,
    layer: AdaptiveSafetyLayer,
    actions: Iterable[np.ndarray],
    risk_scores: Iterable[float],
) -> dict[str, float]:
    raw_hard = 0.0
    raw_soft = 0.0
    projected_hard = 0.0
    projected_soft = 0.0
    distances = []
    weighted_distances = []
    solve_times = []
    modes: list[str] = []
    steps = 0
    env.reset(seed=0)
    for action, risk_score in zip(actions, risk_scores):
        result = layer.project(env, action, risk_score=float(risk_score))
        raw_hard += result.raw_hard_safety_cost
        raw_soft += result.raw_soft_operation_cost
        projected_hard += result.projected_hard_safety_cost
        projected_soft += result.projected_soft_operation_cost
        distances.append(result.projection_distance_l2)
        weighted_distances.append(result.weighted_projection_distance)
        solve_times.append(result.solve_time_ms)
        modes.append(result.mode)
        steps += 1
        _, _, terminated, truncated, _ = env.step(result.action)
        if terminated or truncated:
            break
    return {
        "steps": float(steps),
        "raw_hard_safety_cost": float(raw_hard),
        "raw_soft_operation_cost": float(raw_soft),
        "projected_hard_safety_cost": float(projected_hard),
        "projected_soft_operation_cost": float(projected_soft),
        "mean_projection_distance_l2": float(np.mean(distances)) if distances else 0.0,
        "mean_weighted_projection_distance": float(np.mean(weighted_distances)) if weighted_distances else 0.0,
        "mean_solve_time_ms": float(np.mean(solve_times)) if solve_times else 0.0,
        "p95_solve_time_ms": float(np.quantile(solve_times, 0.95)) if solve_times else 0.0,
        "intervention_rate": float(np.mean(np.asarray(distances) > 1e-6)) if distances else 0.0,
        "pass_through_rate": float(np.mean([mode == "pass_through" for mode in modes])) if modes else 0.0,
        "partial_projection_rate": float(np.mean([mode == "partial_projection" for mode in modes])) if modes else 0.0,
        "full_projection_rate": float(np.mean([mode == "full_projection" for mode in modes])) if modes else 0.0,
    }
