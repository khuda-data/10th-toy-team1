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
    n_jobs: int = 1,
) -> pd.DataFrame:
    """One-Hot 이후 dummy가 아닌, Pipeline 입력 전 원 Feature를 섞어 중요도를 계산한다.

    기본값은 순차 실행이다. Jupyter에서 프로젝트 패키지명 ``code``가 표준 라이브러리 모듈과
    충돌하면 loky process worker가 Pipeline을 역직렬화하지 못할 수 있기 때문이다.
    """
    result = permutation_importance(
        model, X_test, y_test, scoring=scoring, n_repeats=n_repeats, random_state=random_state, n_jobs=n_jobs
    )
    output = pd.DataFrame(
        {
            "feature": X_test.columns,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
            "positive_repeat_count": (result.importances > 0).sum(axis=1),
            "scoring": scoring,
            "n_repeats": n_repeats,
        }
    )
    output = output.sort_values("importance_mean", ascending=False, kind="stable").reset_index(drop=True)
    output["rank"] = output.index + 1
    return output
