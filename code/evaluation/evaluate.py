"""프로토콜 v1.3의 고정 평가 지표를 계산한다."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series, *, threshold: float = 0.5) -> tuple[dict, pd.DataFrame]:
    """Test Dataset에서 F1과 보조 지표를 한 번 계산하고 예측값을 반환한다."""
    if not 0 < threshold < 1:
        raise ValueError("분류 threshold는 0과 1 사이여야 합니다.")
    if not hasattr(model, "predict_proba"):
        raise TypeError("공통 평가에는 predict_proba를 제공하는 분류 모델이 필요합니다.")
    probability = model.predict_proba(X_test)[:, 1]
    predicted = (probability >= threshold).astype("int8")
    metrics = {
        "accuracy": accuracy_score(y_test, predicted),
        "precision": precision_score(y_test, predicted, zero_division=0),
        "recall": recall_score(y_test, predicted, zero_division=0),
        "f1": f1_score(y_test, predicted, zero_division=0),
        "roc_auc": roc_auc_score(y_test, probability) if y_test.nunique() == 2 else np.nan,
        "confusion_matrix": confusion_matrix(y_test, predicted, labels=[0, 1]).tolist(),
    }
    predictions = pd.DataFrame({"y_true": y_test.to_numpy(), "y_probability": probability, "y_predicted": predicted})
    return metrics, predictions
