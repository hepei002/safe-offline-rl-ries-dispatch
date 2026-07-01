from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
import torch.nn.functional as F


@dataclass
class OfflineTransitions:
    observations: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    next_observations: np.ndarray
    terminals: np.ndarray
    safety_costs: np.ndarray


@dataclass
class TrainingResult:
    algorithm: str
    seed: int
    policy: "TorchPolicy"
    learning_curve: dict[str, list[float]]


def _ordered_columns(frame: pd.DataFrame, prefix: str) -> list[str]:
    return sorted(
        [column for column in frame.columns if column.startswith(prefix)],
        key=lambda name: name.replace(prefix, ""),
    )


def load_transition_arrays(frame: pd.DataFrame) -> OfflineTransitions:
    obs_cols = _ordered_columns(frame, "obs_")
    action_cols = _ordered_columns(frame, "action_")
    next_obs_cols = _ordered_columns(frame, "next_obs_")
    if not obs_cols or not action_cols or not next_obs_cols:
        raise ValueError("transition frame must contain obs_, action_ and next_obs_ columns")
    return OfflineTransitions(
        observations=frame[obs_cols].to_numpy(dtype=np.float32),
        actions=frame[action_cols].to_numpy(dtype=np.float32),
        rewards=frame[["reward"]].to_numpy(dtype=np.float32),
        next_observations=frame[next_obs_cols].to_numpy(dtype=np.float32),
        terminals=frame[["terminal"]].astype(float).to_numpy(dtype=np.float32),
        safety_costs=frame[["safety_cost"]].to_numpy(dtype=np.float32),
    )


def load_transition_parquets(paths: list[str]) -> OfflineTransitions:
    frames = [pd.read_parquet(path) for path in paths]
    return load_transition_arrays(pd.concat(frames, ignore_index=True))


class MLP(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Actor(nn.Module):
    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.body = MLP(obs_dim, action_dim, hidden_dim)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.body(obs))


class Critic(nn.Module):
    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.q = MLP(obs_dim + action_dim, 1, hidden_dim)

    def forward(self, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        return self.q(torch.cat([obs, action], dim=-1))


class ValueNet(nn.Module):
    def __init__(self, obs_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.v = MLP(obs_dim, 1, hidden_dim)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.v(obs)


class TorchPolicy:
    def __init__(self, actor: Actor) -> None:
        self.actor = actor.eval()

    def predict(self, observation: np.ndarray) -> np.ndarray:
        obs = torch.as_tensor(observation, dtype=torch.float32).view(1, -1)
        with torch.no_grad():
            action = self.actor(obs).cpu().numpy()[0]
        return np.clip(action.astype(np.float32), -1.0, 1.0)


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def sample_batch(data: OfflineTransitions, batch_size: int, rng: np.random.Generator) -> dict[str, torch.Tensor]:
    idx = rng.integers(0, len(data.observations), size=batch_size)
    return {
        "obs": torch.as_tensor(data.observations[idx], dtype=torch.float32),
        "actions": torch.as_tensor(data.actions[idx], dtype=torch.float32),
        "rewards": torch.as_tensor(data.rewards[idx], dtype=torch.float32),
        "next_obs": torch.as_tensor(data.next_observations[idx], dtype=torch.float32),
        "terminals": torch.as_tensor(data.terminals[idx], dtype=torch.float32),
    }


def expectile_loss(diff: torch.Tensor, expectile: float) -> torch.Tensor:
    weight = torch.where(diff > 0, expectile, 1.0 - expectile)
    return (weight * diff.pow(2)).mean()


def train_offline_algorithm(
    algorithm: str,
    data: OfflineTransitions,
    config: dict[str, Any],
    *,
    seed: int,
) -> TrainingResult:
    algorithm = algorithm.lower()
    set_seed(seed)
    rng = np.random.default_rng(seed)
    obs_dim = data.observations.shape[1]
    action_dim = data.actions.shape[1]
    hidden = int(config.get("hidden_dim", 64))
    steps = int(config.get("steps", 300))
    batch_size = int(config.get("batch_size", 256))
    lr = float(config.get("learning_rate", 3e-4))
    gamma = float(config.get("gamma", 0.99))
    reward_scale = float(config.get("reward_scale", 0.001))
    actor = Actor(obs_dim, action_dim, hidden)
    actor_opt = torch.optim.Adam(actor.parameters(), lr=lr)
    curve: dict[str, list[float]] = {"actor_loss": [], "critic_loss": []}

    if algorithm == "bc":
        for _ in range(steps):
            batch = sample_batch(data, min(batch_size, len(data.observations)), rng)
            pred = actor(batch["obs"])
            loss = F.mse_loss(pred, batch["actions"])
            actor_opt.zero_grad()
            loss.backward()
            actor_opt.step()
            curve["actor_loss"].append(float(loss.detach()))
            curve["critic_loss"].append(0.0)
        return TrainingResult(algorithm=algorithm, seed=seed, policy=TorchPolicy(actor), learning_curve=curve)

    critic1 = Critic(obs_dim, action_dim, hidden)
    critic2 = Critic(obs_dim, action_dim, hidden)
    critic1_target = deepcopy(critic1)
    critic2_target = deepcopy(critic2)
    actor_target = deepcopy(actor)
    critic_opt = torch.optim.Adam(list(critic1.parameters()) + list(critic2.parameters()), lr=lr)
    tau = float(config.get("tau", 0.005))

    if algorithm == "iql":
        value = ValueNet(obs_dim, hidden)
        value_opt = torch.optim.Adam(value.parameters(), lr=lr)
        expectile = float(config.get("expectile", 0.7))
        beta = float(config.get("advantage_temperature", 3.0))
        max_weight = float(config.get("max_advantage_weight", 20.0))
        for _ in range(steps):
            batch = sample_batch(data, min(batch_size, len(data.observations)), rng)
            scaled_reward = batch["rewards"] * reward_scale
            with torch.no_grad():
                q_min = torch.minimum(critic1(batch["obs"], batch["actions"]), critic2(batch["obs"], batch["actions"]))
            v = value(batch["obs"])
            v_loss = expectile_loss(q_min - v, expectile)
            value_opt.zero_grad()
            v_loss.backward()
            value_opt.step()

            with torch.no_grad():
                target_q = scaled_reward + gamma * (1.0 - batch["terminals"]) * value(batch["next_obs"])
            q1 = critic1(batch["obs"], batch["actions"])
            q2 = critic2(batch["obs"], batch["actions"])
            critic_loss = F.mse_loss(q1, target_q) + F.mse_loss(q2, target_q)
            critic_opt.zero_grad()
            critic_loss.backward()
            critic_opt.step()

            with torch.no_grad():
                advantage = q_min - value(batch["obs"])
                weights = torch.exp(beta * advantage).clamp(max=max_weight)
            pred = actor(batch["obs"])
            actor_loss = (weights * (pred - batch["actions"]).pow(2).mean(dim=1, keepdim=True)).mean()
            actor_opt.zero_grad()
            actor_loss.backward()
            actor_opt.step()
            curve["actor_loss"].append(float(actor_loss.detach()))
            curve["critic_loss"].append(float((critic_loss + v_loss).detach()))
        return TrainingResult(algorithm=algorithm, seed=seed, policy=TorchPolicy(actor), learning_curve=curve)

    if algorithm not in {"td3_bc", "cql"}:
        raise ValueError(f"unsupported offline RL algorithm: {algorithm}")

    bc_weight = float(config.get("bc_weight", 2.5))
    cql_alpha = float(config.get("cql_alpha", 1.0))
    policy_delay = int(config.get("policy_delay", 2))
    for step in range(steps):
        batch = sample_batch(data, min(batch_size, len(data.observations)), rng)
        scaled_reward = batch["rewards"] * reward_scale
        with torch.no_grad():
            next_action = actor_target(batch["next_obs"])
            target_q = scaled_reward + gamma * (1.0 - batch["terminals"]) * torch.minimum(
                critic1_target(batch["next_obs"], next_action),
                critic2_target(batch["next_obs"], next_action),
            )
        q1 = critic1(batch["obs"], batch["actions"])
        q2 = critic2(batch["obs"], batch["actions"])
        critic_loss = F.mse_loss(q1, target_q) + F.mse_loss(q2, target_q)
        if algorithm == "cql":
            random_actions = torch.empty_like(batch["actions"]).uniform_(-1.0, 1.0)
            policy_actions = actor(batch["obs"]).detach()
            conservative = (
                torch.logsumexp(
                    torch.cat(
                        [
                            critic1(batch["obs"], random_actions),
                            critic1(batch["obs"], policy_actions),
                            q1,
                        ],
                        dim=1,
                    ),
                    dim=1,
                    keepdim=True,
                ).mean()
                - q1.mean()
            )
            critic_loss = critic_loss + cql_alpha * conservative
        critic_opt.zero_grad()
        critic_loss.backward()
        critic_opt.step()

        actor_loss_value = torch.tensor(0.0)
        if step % policy_delay == 0:
            pred = actor(batch["obs"])
            q_actor = critic1(batch["obs"], pred)
            if algorithm == "td3_bc":
                q_scale = q_actor.abs().mean().detach().clamp(min=1e-3)
                actor_loss = -q_actor.mean() / q_scale + bc_weight * F.mse_loss(pred, batch["actions"])
            else:
                actor_loss = -0.2 * q_actor.mean() + F.mse_loss(pred, batch["actions"])
            actor_opt.zero_grad()
            actor_loss.backward()
            actor_opt.step()
            actor_loss_value = actor_loss.detach()
            soft_update(actor_target, actor, tau)
            soft_update(critic1_target, critic1, tau)
            soft_update(critic2_target, critic2, tau)
        curve["actor_loss"].append(float(actor_loss_value))
        curve["critic_loss"].append(float(critic_loss.detach()))
    return TrainingResult(algorithm=algorithm, seed=seed, policy=TorchPolicy(actor), learning_curve=curve)


def soft_update(target: nn.Module, source: nn.Module, tau: float) -> None:
    with torch.no_grad():
        for target_param, source_param in zip(target.parameters(), source.parameters()):
            target_param.data.mul_(1.0 - tau).add_(source_param.data, alpha=tau)


def apply_shift_scenario(
    frame: pd.DataFrame,
    cost_config: dict,
    scenario: dict[str, Any],
) -> tuple[pd.DataFrame, dict]:
    shifted = frame.copy()
    shifted_cost = deepcopy(cost_config)
    scenario_type = scenario.get("type", "in_distribution")
    if scenario_type == "in_distribution":
        return shifted, shifted_cost
    if scenario_type == "load_up":
        multiplier = float(scenario.get("multiplier", 1.15))
        shifted["electric_load_mw"] *= multiplier
        shifted["heat_load_mw_th"] *= multiplier
        return shifted, shifted_cost
    if scenario_type == "price_spike":
        multiplier = float(scenario.get("multiplier", 1.8))
        price = shifted_cost["costs"]["electricity_import_eur_per_mwh"]
        for key in ["base", "daytime_adder", "evening_peak_adder"]:
            price[key] = float(price[key]) * multiplier
        return shifted, shifted_cost
    if scenario_type == "efficiency_drop":
        shifted["cop_ashp_radiator"] = shifted["cop_ashp_radiator"] * float(scenario.get("cop_multiplier", 0.85))
        shifted["cop_ashp_radiator"] = shifted["cop_ashp_radiator"].clip(lower=1.0)
        shifted_cost["costs"]["natural_gas_eur_per_mwh_lhv"] = (
            float(shifted_cost["costs"]["natural_gas_eur_per_mwh_lhv"])
            / max(float(scenario.get("chp_efficiency_multiplier", 0.9)), 1e-6)
        )
        return shifted, shifted_cost
    raise ValueError(f"unknown shift scenario type: {scenario_type}")

