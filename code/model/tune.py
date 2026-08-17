"""SAMPID-그룹 교차검증으로 공통 탐색 범위에서 최적 모델을 고른다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
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
    sample_weight_train: pd.Series | None = None,
):
    """GridSearchCV(기본) 또는 팀 공통 RandomizedSearchCV를 Train 내부 CV로 실행한다."""
    config = load_model_config(model_config)
    search = config["models"][model_name]["search"]
    if any("train_negative_positive_ratio" in values for values in search.values()):
        raise NotImplementedError(
            "XGBoost의 scale_pos_weight는 각 CV Train fold에서 계산해야 합니다. "
            "전체 Train 비율을 재사용하면 프로토콜을 어기므로, fold-aware 구현을 추가한 뒤 실행하세요."
        )
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor(X_train, feature_config, model_name=model_name)),
            ("model", build_estimator(model_name, config)),
        ]
    )
    param_grid = {f"model__{name}": values for name, values in search.items()}
    cv = StratifiedGroupKFold(
        n_splits=config["split"]["cv_n_splits"], shuffle=True, random_state=config["split"]["random_state"]
    )
    method = search_method or config["tuning"]["default_method"]
    common = {"scoring": config["tuning"]["scoring"], "cv": cv, "n_jobs": -1, "refit": True}
    if method == "grid":
        searcher = GridSearchCV(pipeline, param_grid=param_grid, **common)
    elif method == "randomized":
        searcher = RandomizedSearchCV(
            pipeline,
            param_distributions=param_grid,
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
    return searcher.fit(X_train, y_train, **fit_params)
