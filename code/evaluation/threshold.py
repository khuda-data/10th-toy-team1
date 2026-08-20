"""Train OOF 확률로 threshold 민감도를 계산하는 공용 기능."""

from __future__ import annotations

import numpy as np
import pandas as pd

from code.evaluation.evaluate import calculate_binary_metrics


def calculate_threshold_sensitivity(
    y_true: pd.Series | np.ndarray,
    y_probability: pd.Series | np.ndarray,
    *,
    model: str,
    thresholds: np.ndarray | None = None,
) -> pd.DataFrame:
    """OOF 확률에서 threshold별 지표를 계산한다.

    이 함수는 최적 threshold를 채택하거나 모델을 선택하지 않는다. 호출부가 Train OOF만
    전달하는 구조라 Test label·확률을 이 분석에 섞을 수 없다.
    """
    values = np.arange(0.20, 0.801, 0.01) if thresholds is None else np.asarray(thresholds, dtype=float)
    rows = []
    probability = np.asarray(y_probability, dtype="float64")
    for threshold in values:
        metrics = calculate_binary_metrics(y_true, probability, threshold=float(threshold))
        rows.append(
            {
                "model": model,
                "threshold": float(np.round(threshold, 2)),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "predicted_positive_rate": float((probability >= threshold).mean()),
            }
        )
    return pd.DataFrame(rows)


def summarize_threshold_sensitivity(sensitivity: pd.DataFrame) -> pd.DataFrame:
    """0.5와 OOF F1 최대 threshold를 나란히 보인다. 최대값 동률이면 작은 threshold를 쓴다."""
    required = {"model", "threshold", "precision", "recall", "f1", "predicted_positive_rate"}
    missing = sorted(required - set(sensitivity.columns))
    if missing:
        raise ValueError(f"threshold sensitivity에 필요한 열이 없습니다: {', '.join(missing)}")

    rows = []
    for model, model_rows in sensitivity.groupby("model", sort=False):
        ordered = model_rows.sort_values("threshold").reset_index(drop=True)
        default = ordered.loc[np.isclose(ordered["threshold"], 0.5)]
        if len(default) != 1:
            raise ValueError("threshold sensitivity에는 0.50 행이 정확히 하나 있어야 합니다.")
        default_row = default.iloc[0]
        best_row = ordered.loc[ordered["f1"].idxmax()]
        for threshold_type, row in (("default", default_row), ("oof_best", best_row)):
            rows.append(
                {
                    "model": model,
                    "threshold_type": threshold_type,
                    "threshold": row["threshold"],
                    "precision": row["precision"],
                    "recall": row["recall"],
                    "f1": row["f1"],
                    "predicted_positive_rate": row["predicted_positive_rate"],
                    "delta_f1_from_0_5": row["f1"] - default_row["f1"],
                    "delta_precision_from_0_5": row["precision"] - default_row["precision"],
                    "delta_recall_from_0_5": row["recall"] - default_row["recall"],
                }
            )
    return pd.DataFrame(rows)
