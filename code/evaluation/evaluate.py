"""프로토콜 v1.3의 고정 평가 지표를 계산한다."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def calculate_binary_metrics(
    y_true: pd.Series | np.ndarray,
    probability: pd.Series | np.ndarray,
    *,
    threshold: float = 0.5,
) -> dict:
    """확률 예측과 고정 threshold로 이진분류 공통 지표를 계산한다."""
    if not 0 < threshold < 1:
        raise ValueError("분류 threshold는 0과 1 사이여야 합니다.")
    observed = np.asarray(y_true)
    predicted_probability = np.asarray(probability, dtype="float64")
    if len(observed) != len(predicted_probability):
        raise ValueError("y_true와 probability의 행 수는 같아야 합니다.")
    predicted = (predicted_probability >= threshold).astype("int8")
    return {
        "accuracy": accuracy_score(observed, predicted),
        "precision": precision_score(observed, predicted, zero_division=0),
        "recall": recall_score(observed, predicted, zero_division=0),
        "f1": f1_score(observed, predicted, zero_division=0),
        "roc_auc": roc_auc_score(observed, predicted_probability) if pd.Series(observed).nunique() == 2 else np.nan,
        "average_precision": average_precision_score(observed, predicted_probability)
        if pd.Series(observed).nunique() == 2 else np.nan,
        "confusion_matrix": confusion_matrix(observed, predicted, labels=[0, 1]).tolist(),
    }


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series, *, threshold: float = 0.5) -> tuple[dict, pd.DataFrame]:
    """Test Dataset에서 F1과 보조 지표를 한 번 계산하고 예측값을 반환한다."""
    if not hasattr(model, "predict_proba"):
        raise TypeError("공통 평가에는 predict_proba를 제공하는 분류 모델이 필요합니다.")
    probability = model.predict_proba(X_test)[:, 1]
    predicted = (probability >= threshold).astype("int8")
    metrics = calculate_binary_metrics(y_test, probability, threshold=threshold)
    predictions = pd.DataFrame({"y_true": y_test.to_numpy(), "y_probability": probability, "y_predicted": predicted})
    return metrics, predictions
