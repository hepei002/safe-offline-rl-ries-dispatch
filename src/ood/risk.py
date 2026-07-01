from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.neighbors import NearestNeighbors


class OodRiskScorer:
    """Distance-based OOD scorer for state-action vectors."""

    def __init__(self, method: str = "mahalanobis", n_neighbors: int = 5) -> None:
        self.method = method
        self.n_neighbors = n_neighbors
        self.mean_: np.ndarray | None = None
        self.inv_cov_: np.ndarray | None = None
        self.knn_: NearestNeighbors | None = None

    def fit(self, reference: np.ndarray) -> "OodRiskScorer":
        reference = np.asarray(reference, dtype=float)
        if reference.ndim != 2:
            raise ValueError("reference must be a 2D array")
        if self.method == "mahalanobis":
            self.mean_ = reference.mean(axis=0)
            cov = np.cov(reference, rowvar=False)
            cov = np.atleast_2d(cov) + np.eye(reference.shape[1]) * 1e-6
            self.inv_cov_ = np.linalg.pinv(cov)
        elif self.method == "knn":
            self.knn_ = NearestNeighbors(n_neighbors=min(self.n_neighbors, len(reference)))
            self.knn_.fit(reference)
        else:
            raise ValueError(f"unsupported OOD scoring method: {self.method}")
        return self

    def score(self, samples: np.ndarray) -> np.ndarray:
        samples = np.asarray(samples, dtype=float)
        if self.method == "mahalanobis":
            if self.mean_ is None or self.inv_cov_ is None:
                raise RuntimeError("scorer must be fitted before score()")
            diff = samples - self.mean_
            return np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", diff, self.inv_cov_, diff), 0.0))
        if self.knn_ is None:
            raise RuntimeError("scorer must be fitted before score()")
        distances, _ = self.knn_.kneighbors(samples)
        return distances.mean(axis=1)


def evaluate_ood_scores(
    scores: np.ndarray,
    hard_safety_cost: np.ndarray,
    *,
    hard_safety_threshold: float = 1e-6,
) -> dict[str, float]:
    scores = np.asarray(scores, dtype=float)
    hard = np.asarray(hard_safety_cost, dtype=float)
    labels = hard > float(hard_safety_threshold)
    corr = spearmanr(scores, hard).correlation
    metrics = {
        "spearman_corr": float(0.0 if np.isnan(corr) else corr),
        "mean_score_safe": float(scores[~labels].mean()) if (~labels).any() else 0.0,
        "mean_score_unsafe": float(scores[labels].mean()) if labels.any() else 0.0,
        "unsafe_rate": float(labels.mean()),
    }
    if labels.any() and (~labels).any():
        metrics["auroc"] = float(roc_auc_score(labels, scores))
        metrics["auprc"] = float(average_precision_score(labels, scores))
    else:
        metrics["auroc"] = 0.5
        metrics["auprc"] = float(labels.mean())
    return metrics
