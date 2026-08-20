"""SAMPID-그룹 교차검증으로 공통 탐색 범위에서 최적 모델을 고른다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from joblib import parallel_backend
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from code.model.train import build_estimator, load_model_config
from code.preprocess.preprocess import build_preprocessor


def tune_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups_train: pd.Series,
    *,
    model_name: str,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    search_method: str | None = None,
    param_grid: dict[str, list] | None = None,
    estimator_params: dict | None = None,
    sample_weight_train: pd.Series | None = None,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
):
    """GridSearchCV(기본) 또는 팀 공통 RandomizedSearchCV를 Train 내부 CV로 실행한다.

    `parallel_backend_name`은 탐색·평가 방법을 바꾸지 않는 실행 환경 옵션이다. Jupyter에서
    저장소 패키지명 `code`와 표준 라이브러리 이름 충돌로 process worker가 실패할 때만
    ``threading``을 지정한다. ``param_grid``은 단계별 제한 탐색처럼 공통 설정의 기본 범위 대신
    명시 범위를 사용할 때만 전달하고, ``estimator_params``는 탐색하지 않는 고정 모델 파라미터다.
    """
    config = load_model_config(model_config)
    search = param_grid if param_grid is not None else config["models"][model_name]["search"]
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor(X_train, feature_config, model_name=model_name)),
            ("model", build_estimator(model_name, config, params=estimator_params)),
        ]
    )
    # XGBoost의 `train_negative_positive_ratio` marker는 estimator.fit()에서 각 CV Train fold의
    # y만 보고 숫자로 바뀐다. 전체 Train 비율을 모든 fold에 재사용하지 않는다.
    pipeline_param_grid = {f"model__{name}": values for name, values in search.items()}
    cv = StratifiedGroupKFold(
        n_splits=config["split"]["cv_n_splits"], shuffle=True, random_state=config["split"]["random_state"]
    )
    method = search_method or config["tuning"]["default_method"]
    common = {"scoring": config["tuning"]["scoring"], "cv": cv, "n_jobs": n_jobs, "refit": True}
    if method == "grid":
        searcher = GridSearchCV(pipeline, param_grid=pipeline_param_grid, **common)
    elif method == "randomized":
        searcher = RandomizedSearchCV(
            pipeline,
            param_distributions=pipeline_param_grid,
            n_iter=config["tuning"]["randomized_n_iter"],
            random_state=config["random_seed"],
            **common,
        )
    else:
        raise ValueError("search_method는 grid 또는 randomized여야 합니다.")
    fit_params = {"groups": groups_train}
    if sample_weight_train is not None:
        # 학습(fit)에만 반영되고, GridSearchCV가 하이퍼파라미터를 고르는 검증 fold 채점(scoring)에는
        # 적용되지 않는다 〔AI 제안 · 사람 검토 필요 — 이 항목은 아직 팀이 확정하지 않음, 2026-08-18〕.
        fit_params["model__sample_weight"] = sample_weight_train
    if parallel_backend_name is None:
        return searcher.fit(X_train, y_train, **fit_params)
    with parallel_backend(parallel_backend_name):
        return searcher.fit(X_train, y_train, **fit_params)
