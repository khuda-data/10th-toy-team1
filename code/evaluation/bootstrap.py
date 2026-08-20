"""SAMPID 단위 bootstrap 신뢰구간 계산."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


def _metric_values(y_true: np.ndarray, probability: np.ndarray, *, threshold: float) -> dict[str, float]:
    predicted = (probability >= threshold).astype("int8")
    return {
        "accuracy": accuracy_score(y_true, predicted),
        "precision": precision_score(y_true, predicted, zero_division=0),
        "recall": recall_score(y_true, predicted, zero_division=0),
        "f1": f1_score(y_true, predicted, zero_division=0),
        "roc_auc": roc_auc_score(y_true, probability),
    }


def bootstrap_confidence_intervals(
    y_true: pd.Series | np.ndarray,
    probability: pd.Series | np.ndarray,
    groups: pd.Series | np.ndarray,
    *,
    threshold: float = 0.5,
    n_repeats: int = 1000,
    random_state: int = 42,
) -> pd.DataFrame:
    """SAMPID를 복원추출해 고정 threshold 지표의 95% 신뢰구간을 반환한다.

    한 사람이 여러 Person-Period 행을 가질 수 있으므로 행이 아니라 SAMPID를 추출 단위로 쓴다.
    특정 bootstrap 표본에 한 class만 있으면 해당 반복 전체를 제외한다.
    """
    if not 0 < threshold < 1:
        raise ValueError("분류 threshold는 0과 1 사이여야 합니다.")
    if n_repeats < 1:
        raise ValueError("n_repeats는 1 이상이어야 합니다.")

    y = np.asarray(y_true, dtype="int8")
    scores = np.asarray(probability, dtype="float64")
    group_values = pd.Series(groups, copy=False).astype("string")
    if not (len(y) == len(scores) == len(group_values)):
        raise ValueError("y_true, probability, groups의 길이는 같아야 합니다.")
    if group_values.isna().any():
        raise ValueError("SAMPID 결측이 있는 예측에는 bootstrap을 계산할 수 없습니다.")
    if not np.isin(y, [0, 1]).all():
        raise ValueError("y_true는 0 또는 1이어야 합니다.")

    unique_groups = group_values.unique().to_numpy()
    if len(unique_groups) < 2:
        raise ValueError("bootstrap에는 SAMPID가 2개 이상 필요합니다.")
    row_indices = {
        group: np.flatnonzero(group_values.to_numpy() == group)
        for group in unique_groups
    }
    rng = np.random.default_rng(random_state)
    metric_rows: list[dict[str, float]] = []
    for _ in range(n_repeats):
        selected_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        selected_rows = np.concatenate([row_indices[group] for group in selected_groups])
        sampled_y = y[selected_rows]
        if np.unique(sampled_y).size < 2:
            continue
        metric_rows.append(_metric_values(sampled_y, scores[selected_rows], threshold=threshold))

    if not metric_rows:
        raise RuntimeError("유효한 bootstrap 표본이 없어 신뢰구간을 계산하지 못했습니다.")
    bootstrap_metrics = pd.DataFrame(metric_rows)
    point_estimate = _metric_values(y, scores, threshold=threshold)
    return pd.DataFrame(
        {
            "metric": bootstrap_metrics.columns,
            "estimate": [point_estimate[metric] for metric in bootstrap_metrics.columns],
            "bootstrap_mean": bootstrap_metrics.mean().to_numpy(),
            "ci95_lower": bootstrap_metrics.quantile(0.025).to_numpy(),
            "ci95_upper": bootstrap_metrics.quantile(0.975).to_numpy(),
            "n_valid_repeats": len(bootstrap_metrics),
            "n_repeats": n_repeats,
            "bootstrap_unit": "SAMPID",
            "threshold": threshold,
        }
    )


def paired_bootstrap_f1_difference(
    y_true: pd.Series | np.ndarray,
    probability_a: pd.Series | np.ndarray,
    probability_b: pd.Series | np.ndarray,
    groups: pd.Series | np.ndarray,
    *,
    threshold: float = 0.5,
    n_repeats: int = 1000,
    random_state: int = 42,
    comparison: str | None = None,
) -> pd.DataFrame:
    """같은 SAMPID 복원표본에서 두 모델의 F1(A-B) 차이 95% CI를 계산한다."""
    y = np.asarray(y_true, dtype="int8")
    scores_a = np.asarray(probability_a, dtype="float64")
    scores_b = np.asarray(probability_b, dtype="float64")
    group_values = pd.Series(groups, copy=False).astype("string")
    if not (len(y) == len(scores_a) == len(scores_b) == len(group_values)):
        raise ValueError("paired bootstrap 입력의 길이는 모두 같아야 합니다.")
    if group_values.isna().any() or group_values.nunique() < 2:
        raise ValueError("paired bootstrap에는 결측 없는 SAMPID가 2개 이상 필요합니다.")
    if n_repeats < 1 or not 0 < threshold < 1:
        raise ValueError("n_repeats와 threshold 범위를 확인하세요.")

    unique_groups = group_values.unique().to_numpy()
    group_array = group_values.to_numpy()
    row_indices = {group: np.flatnonzero(group_array == group) for group in unique_groups}
    rng = np.random.default_rng(random_state)
    deltas = []
    for _ in range(n_repeats):
        sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        sampled_rows = np.concatenate([row_indices[group] for group in sampled_groups])
        f1_a = f1_score(y[sampled_rows], scores_a[sampled_rows] >= threshold, zero_division=0)
        f1_b = f1_score(y[sampled_rows], scores_b[sampled_rows] >= threshold, zero_division=0)
        deltas.append(float(f1_a - f1_b))
    point = f1_score(y, scores_a >= threshold, zero_division=0) - f1_score(y, scores_b >= threshold, zero_division=0)
    values = np.asarray(deltas, dtype="float64")
    return pd.DataFrame(
        [{
            "comparison": comparison or "model_a - model_b",
            "point_estimate_delta_f1": point,
            "bootstrap_mean_delta": float(values.mean()),
            "ci95_lower": float(np.quantile(values, 0.025)),
            "ci95_upper": float(np.quantile(values, 0.975)),
            "n_repeats": n_repeats,
            "bootstrap_unit": "SAMPID",
            "threshold": threshold,
        }]
    )
