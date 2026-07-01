from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Iterable

import numpy as np
from scipy.optimize import minimize

from src.envs.integrated_energy_env import IntegratedEnergyEnv, encode_dispatch_action
from src.optimization.deterministic_dispatch import solve_dispatch_day
from src.safety.projection import dispatch_split, project_action


@dataclass(frozen=True)
class FixedProjectionConfig:
    hard_safety_tolerance: float = 1e-6
    hard_safety_penalty: float = 1_000_000.0
    soft_operation_weight: float = 1e-3
    distance_weights: tuple[float, float, float, float] = (1.0, 1.0, 0.5, 0.5)
    max_iterations: int = 60
    solver_ftol: float = 1e-7
    force_solver_failure: bool = False
    prefer_fast_fallback: bool = False


@dataclass(frozen=True)
class ProjectionResult:
    action: np.ndarray
    status: str
    raw_hard_safety_cost: float
    raw_soft_operation_cost: float
    projected_hard_safety_cost: float
    projected_soft_operation_cost: float
    projection_distance_l2: float
    weighted_projection_distance: float
    solve_time_ms: float
    solver_message: str = ""


class FixedSafetyProjectionLayer:
    """One-step fixed physical safety layer for normalized dispatch actions.

    The layer minimizes the weighted distance between a candidate action and a
    corrected action while penalizing hard-safety violations. A deterministic
    candidate-search fallback is used whenever the continuous solver fails or
    returns a poorer hard-safety result.
    """

    def __init__(self, config: FixedProjectionConfig | None = None) -> None:
        self.config = config or FixedProjectionConfig()

    def project(self, env: IntegratedEnergyEnv, action: np.ndarray) -> ProjectionResult:
        tic = time.perf_counter()
        raw = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        raw_split = dispatch_split(env, raw)
        fallback_action, fallback_report = self._fallback_action(env, raw)
        fallback_distance = self._weighted_distance(raw, fallback_action)
        best_action = fallback_action
        best_split = {
            "hard_safety_cost": fallback_report["projected_hard_safety_cost"],
            "soft_operation_cost": fallback_report["projected_soft_operation_cost"],
        }
        status = "fallback"
        message = "deterministic fallback selected"

        if (
            self.config.prefer_fast_fallback
            and best_split["hard_safety_cost"] <= raw_split["hard_safety_cost"] + self.config.hard_safety_tolerance
            and fallback_report["projection_distance_l2"] > 1e-9
        ):
            solve_time_ms = (time.perf_counter() - tic) * 1000.0
            return ProjectionResult(
                action=np.clip(best_action.astype(np.float32), -1.0, 1.0),
                status=status,
                raw_hard_safety_cost=float(raw_split["hard_safety_cost"]),
                raw_soft_operation_cost=float(raw_split["soft_operation_cost"]),
                projected_hard_safety_cost=float(best_split["hard_safety_cost"]),
                projected_soft_operation_cost=float(best_split["soft_operation_cost"]),
                projection_distance_l2=float(np.linalg.norm(best_action - raw)),
                weighted_projection_distance=fallback_distance,
                solve_time_ms=float(solve_time_ms),
                solver_message="fast feasible fallback accepted",
            )

        if not self.config.force_solver_failure:
            opt_action, opt_success, opt_message = self._solve_slsqp(env, raw, fallback_action)
            opt_split = dispatch_split(env, opt_action)
            if self._is_better_than_fallback(opt_action, opt_split, raw, best_action, best_split):
                best_action = opt_action
                best_split = opt_split
                status = "optimal" if opt_success else "fallback"
                message = opt_message
            elif opt_success and opt_split["hard_safety_cost"] <= best_split["hard_safety_cost"] + self.config.hard_safety_tolerance:
                status = "optimal"
                message = "solver succeeded; fallback had equal or shorter correction"
        solve_time_ms = (time.perf_counter() - tic) * 1000.0
        return ProjectionResult(
            action=np.clip(best_action.astype(np.float32), -1.0, 1.0),
            status=status,
            raw_hard_safety_cost=float(raw_split["hard_safety_cost"]),
            raw_soft_operation_cost=float(raw_split["soft_operation_cost"]),
            projected_hard_safety_cost=float(best_split["hard_safety_cost"]),
            projected_soft_operation_cost=float(best_split["soft_operation_cost"]),
            projection_distance_l2=float(np.linalg.norm(best_action - raw)),
            weighted_projection_distance=self._weighted_distance(raw, best_action),
            solve_time_ms=float(solve_time_ms),
            solver_message=message,
        )

    def _fallback_action(self, env: IntegratedEnergyEnv, raw: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
        heuristic_action, heuristic_report = project_action(env, raw)
        best_action = heuristic_action
        best_report = heuristic_report
        mpc_action = self._one_step_mpc_fallback(env)
        if mpc_action is not None:
            mpc_split = dispatch_split(env, mpc_action)
            mpc_report = {
                "raw_hard_safety_cost": heuristic_report["raw_hard_safety_cost"],
                "raw_soft_operation_cost": heuristic_report["raw_soft_operation_cost"],
                "projected_hard_safety_cost": mpc_split["hard_safety_cost"],
                "projected_soft_operation_cost": mpc_split["soft_operation_cost"],
                "projection_distance_l2": float(np.linalg.norm(mpc_action - raw)),
            }
            hard_margin = mpc_report["projected_hard_safety_cost"] - heuristic_report["projected_hard_safety_cost"]
            if hard_margin < -self.config.hard_safety_tolerance or (
                abs(hard_margin) <= self.config.hard_safety_tolerance
                and mpc_report["projection_distance_l2"] < heuristic_report["projection_distance_l2"]
            ):
                best_action = mpc_action
                best_report = mpc_report
        return best_action, best_report

    def _one_step_mpc_fallback(self, env: IntegratedEnergyEnv) -> np.ndarray | None:
        try:
            row = env.frame.iloc[[env._absolute_index()]].copy()
            result = solve_dispatch_day(
                row,
                env.system_config,
                env.cost_config,
                initial_battery_soc_mwh=env.battery_soc_mwh,
                initial_thermal_soc_mwh_th=env.thermal_soc_mwh_th,
                enforce_terminal_soc=False,
            )
            if result.status != "optimal" or result.frame.empty:
                return None
            return encode_dispatch_action(result.frame.iloc[0], env.system_config)
        except Exception:
            return None

    def _weighted_distance(self, raw: np.ndarray, candidate: np.ndarray) -> float:
        weights = np.asarray(self.config.distance_weights, dtype=float)
        diff = np.asarray(candidate, dtype=float) - np.asarray(raw, dtype=float)
        return float(np.sqrt(np.sum(weights * diff * diff)))

    def _objective(self, env: IntegratedEnergyEnv, raw: np.ndarray, x: np.ndarray) -> float:
        split = dispatch_split(env, np.asarray(x, dtype=np.float32))
        hard = max(float(split["hard_safety_cost"]) - self.config.hard_safety_tolerance, 0.0)
        soft = float(split["soft_operation_cost"])
        distance = self._weighted_distance(raw, x) ** 2
        return float(
            distance
            + self.config.hard_safety_penalty * hard * hard
            + self.config.soft_operation_weight * soft
        )

    def _solve_slsqp(
        self,
        env: IntegratedEnergyEnv,
        raw: np.ndarray,
        fallback_action: np.ndarray,
    ) -> tuple[np.ndarray, bool, str]:
        starts = [
            raw,
            fallback_action,
            np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32),
            np.asarray([1.0, 1.0, 0.0, -1.0], dtype=np.float32),
        ]
        best_x = fallback_action.astype(float)
        best_value = self._objective(env, raw, best_x)
        best_success = False
        best_message = "solver was not run"
        for start in starts:
            result = minimize(
                lambda x: self._objective(env, raw, x),
                np.asarray(start, dtype=float),
                method="SLSQP",
                bounds=[(-1.0, 1.0)] * len(raw),
                options={
                    "maxiter": int(self.config.max_iterations),
                    "ftol": float(self.config.solver_ftol),
                    "disp": False,
                },
            )
            value = float(result.fun) if np.isfinite(result.fun) else float("inf")
            if value < best_value:
                best_x = np.clip(result.x.astype(float), -1.0, 1.0)
                best_value = value
                best_success = bool(result.success)
                best_message = str(result.message)
        return best_x.astype(np.float32), best_success, best_message

    def _is_better_than_fallback(
        self,
        opt_action: np.ndarray,
        opt_split: dict[str, float],
        raw: np.ndarray,
        fallback_action: np.ndarray,
        fallback_split: dict[str, float],
    ) -> bool:
        hard_margin = float(opt_split["hard_safety_cost"]) - float(fallback_split["hard_safety_cost"])
        if hard_margin < -self.config.hard_safety_tolerance:
            return True
        if abs(hard_margin) <= self.config.hard_safety_tolerance:
            return self._weighted_distance(raw, opt_action) < self._weighted_distance(raw, fallback_action)
        return False


def evaluate_fixed_projection_layer(
    env: IntegratedEnergyEnv,
    layer: FixedSafetyProjectionLayer,
    actions: Iterable[np.ndarray],
) -> dict[str, float]:
    raw_hard = 0.0
    raw_soft = 0.0
    projected_hard = 0.0
    projected_soft = 0.0
    distances = []
    weighted_distances = []
    solve_times = []
    interventions = 0
    fallbacks = 0
    steps = 0
    env.reset(seed=0)
    for action in actions:
        result = layer.project(env, action)
        raw_hard += result.raw_hard_safety_cost
        raw_soft += result.raw_soft_operation_cost
        projected_hard += result.projected_hard_safety_cost
        projected_soft += result.projected_soft_operation_cost
        distances.append(result.projection_distance_l2)
        weighted_distances.append(result.weighted_projection_distance)
        solve_times.append(result.solve_time_ms)
        interventions += int(result.projection_distance_l2 > 1e-6)
        fallbacks += int(result.status == "fallback")
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
        "intervention_rate": float(interventions / max(steps, 1)),
        "fallback_rate": float(fallbacks / max(steps, 1)),
    }
