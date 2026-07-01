from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
import torch
from torch import nn
import torch.nn.functional as F

from src.ood.risk import evaluate_ood_scores


def _ordered_columns(frame: pd.DataFrame, prefix: str) -> list[str]:
    return sorted(
        [column for column in frame.columns if column.startswith(prefix)],
        key=lambda name: name.replace(prefix, ""),
    )


def _transition_arrays(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    obs_cols = _ordered_columns(frame, "obs_")
    action_cols = _ordered_columns(frame, "action_")
    next_obs_cols = _ordered_columns(frame, "next_obs_")
    if not obs_cols or not action_cols or not next_obs_cols:
        raise ValueError("frame must contain obs_, action_ and next_obs_ transition columns")
    inputs = np.concatenate(
        [
            frame[obs_cols].to_numpy(dtype=np.float32),
            frame[action_cols].to_numpy(dtype=np.float32),
        ],
        axis=1,
    )
    targets = frame[next_obs_cols].to_numpy(dtype=np.float32) - frame[obs_cols].to_numpy(dtype=np.float32)
    return inputs, targets


class _DynamicsModel(nn.Module):
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


@dataclass
class DynamicsEnsembleRiskEstimator:
    n_models: int = 5
    hidden_dim: int = 64
    epochs: int = 50
    learning_rate: float = 1e-3
    batch_size: int = 256
    seed: int = 0

    def __post_init__(self) -> None:
        self.models_: list[_DynamicsModel] = []
        self.input_mean_: np.ndarray | None = None
        self.input_std_: np.ndarray | None = None
        self.target_mean_: np.ndarray | None = None
        self.target_std_: np.ndarray | None = None
        self.reference_mean_: np.ndarray | None = None
        self.reference_inv_cov_: np.ndarray | None = None
        self.residual_scale_: float = 1.0

    def fit(self, frame: pd.DataFrame) -> "DynamicsEnsembleRiskEstimator":
        inputs, targets = _transition_arrays(frame)
        rng = np.random.default_rng(self.seed)
        torch.manual_seed(self.seed)
        self.input_mean_ = inputs.mean(axis=0)
        self.input_std_ = inputs.std(axis=0) + 1e-6
        self.target_mean_ = targets.mean(axis=0)
        self.target_std_ = targets.std(axis=0) + 1e-6
        x = ((inputs - self.input_mean_) / self.input_std_).astype(np.float32)
        y = ((targets - self.target_mean_) / self.target_std_).astype(np.float32)
        self.reference_mean_ = x.mean(axis=0)
        cov = np.cov(x, rowvar=False)
        cov = np.atleast_2d(cov) + np.eye(x.shape[1]) * 1e-5
        self.reference_inv_cov_ = np.linalg.pinv(cov)
        self.models_ = []
        for model_idx in range(int(self.n_models)):
            torch.manual_seed(self.seed + model_idx * 997)
            model = _DynamicsModel(x.shape[1], y.shape[1], int(self.hidden_dim))
            opt = torch.optim.Adam(model.parameters(), lr=float(self.learning_rate))
            bootstrap = rng.integers(0, len(x), size=len(x))
            xb = torch.as_tensor(x[bootstrap], dtype=torch.float32)
            yb = torch.as_tensor(y[bootstrap], dtype=torch.float32)
            for _ in range(int(self.epochs)):
                order = rng.permutation(len(xb))
                for start in range(0, len(order), int(self.batch_size)):
                    idx = order[start : start + int(self.batch_size)]
                    pred = model(xb[idx])
                    loss = F.mse_loss(pred, yb[idx])
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
            model.eval()
            self.models_.append(model)
        train_scores = self._raw_components(inputs, targets)
        self.residual_scale_ = float(np.percentile(train_scores["combined_raw"], 90) + 1e-6)
        return self

    def _check_fitted(self) -> None:
        if (
            not self.models_
            or self.input_mean_ is None
            or self.input_std_ is None
            or self.target_mean_ is None
            or self.target_std_ is None
            or self.reference_mean_ is None
            or self.reference_inv_cov_ is None
        ):
            raise RuntimeError("DynamicsEnsembleRiskEstimator must be fitted before scoring")

    def _raw_components(self, inputs: np.ndarray, targets: np.ndarray) -> dict[str, np.ndarray]:
        self._check_fitted()
        x = ((inputs - self.input_mean_) / self.input_std_).astype(np.float32)
        y = ((targets - self.target_mean_) / self.target_std_).astype(np.float32)
        xt = torch.as_tensor(x, dtype=torch.float32)
        predictions = []
        with torch.no_grad():
            for model in self.models_:
                predictions.append(model(xt).cpu().numpy())
        preds = np.stack(predictions, axis=0)
        disagreement = preds.std(axis=0).mean(axis=1)
        mean_pred = preds.mean(axis=0)
        prediction_error = np.square(mean_pred - y).mean(axis=1)
        diff = x - self.reference_mean_
        novelty = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", diff, self.reference_inv_cov_, diff), 0.0))
        combined = disagreement + prediction_error + 0.05 * novelty
        return {
            "disagreement": disagreement,
            "prediction_error": prediction_error,
            "novelty": novelty,
            "combined_raw": combined,
        }

    def score_components(self, frame: pd.DataFrame) -> pd.DataFrame:
        inputs, targets = _transition_arrays(frame)
        components = self._raw_components(inputs, targets)
        return pd.DataFrame(
            {
                "ensemble_ood_score": components["combined_raw"] / self.residual_scale_,
                "ensemble_disagreement": components["disagreement"],
                "ensemble_prediction_error": components["prediction_error"],
                "state_action_novelty": components["novelty"],
            },
            index=frame.index,
        )

    def score(self, frame: pd.DataFrame) -> np.ndarray:
        return self.score_components(frame)["ensemble_ood_score"].to_numpy(dtype=float)


def evaluate_ensemble_risk_by_scenario(
    estimator: DynamicsEnsembleRiskEstimator,
    frame: pd.DataFrame,
    *,
    scenario_column: str = "scenario",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if scenario_column not in frame.columns:
        raise ValueError(f"frame must contain {scenario_column!r}")
    if "hard_safety_cost" not in frame.columns:
        raise ValueError("frame must contain hard_safety_cost")
    scored = frame.copy()
    components = estimator.score_components(frame)
    for column in components.columns:
        scored[column] = components[column].to_numpy()
    rows = []
    global_metrics = evaluate_ood_scores(
        scored["ensemble_ood_score"].to_numpy(dtype=float),
        scored["hard_safety_cost"].to_numpy(dtype=float),
    )
    rows.append(
        {
            "scenario": "all",
            "transitions": int(len(scored)),
            "mean_ood_score": float(scored["ensemble_ood_score"].mean()),
            "p90_ood_score": float(scored["ensemble_ood_score"].quantile(0.9)),
            "mean_hard_safety_cost": float(scored["hard_safety_cost"].mean()),
            **global_metrics,
        }
    )
    for scenario, group in scored.groupby(scenario_column):
        metrics = evaluate_ood_scores(
            group["ensemble_ood_score"].to_numpy(dtype=float),
            group["hard_safety_cost"].to_numpy(dtype=float),
        )
        rows.append(
            {
                "scenario": scenario,
                "transitions": int(len(group)),
                "mean_ood_score": float(group["ensemble_ood_score"].mean()),
                "p90_ood_score": float(group["ensemble_ood_score"].quantile(0.9)),
                "mean_hard_safety_cost": float(group["hard_safety_cost"].mean()),
                **metrics,
            }
        )
    return scored, pd.DataFrame(rows).sort_values("scenario").reset_index(drop=True)
