"""원 Feature 단위 Permutation Importance 계산."""

from __future__ import annotations

import pandas as pd
from sklearn.inspection import permutation_importance


def calculate_feature_importance(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    scoring: str = "f1",
    n_repeats: int = 20,
    random_state: int = 42,
) -> pd.DataFrame:
    """One-Hot 이후 dummy가 아닌, Pipeline 입력 전 원 Feature를 섞어 중요도를 계산한다."""
    result = permutation_importance(
        model, X_test, y_test, scoring=scoring, n_repeats=n_repeats, random_state=random_state, n_jobs=-1
    )
    output = pd.DataFrame(
        {
            "feature": X_test.columns,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
            "scoring": scoring,
            "n_repeats": n_repeats,
        }
    )
    output = output.sort_values("importance_mean", ascending=False, kind="stable").reset_index(drop=True)
    output["rank"] = output.index + 1
    return output
