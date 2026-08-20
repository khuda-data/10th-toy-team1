"""Train 내부 SAMPID 그룹 교차검증의 out-of-fold(OOF) 예측 생성."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from code.model.train import load_model_config, train_model
from code.model.tune import tune_model


def generate_oof_predictions(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups_train: pd.Series,
    *,
    model_name: str,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    tune: bool = False,
    search_method: str | None = None,
    params: dict | None = None,
    sample_weight_train: pd.Series | None = None,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> pd.DataFrame:
    """각 SAMPID 그룹을 한 번씩 검증 fold로 사용한 확률 예측을 반환한다.

    `params`를 주면 매 validation fold에서 그 고정 파라미터로 학습한다. `tune=True`이면
    각 outer CV train fold 안에서 다시 `tune_model()`을 실행한다. 둘은 함께 사용할 수 없다.
    어느 경우든 전처리는 해당 CV Train fold에서만 fit된다.
    """
    config = load_model_config(model_config)
    if tune and params is not None:
        raise ValueError("OOF 생성에서 tune=True와 params는 함께 사용할 수 없습니다.")
    splitter = StratifiedGroupKFold(
        n_splits=config["split"]["cv_n_splits"],
        shuffle=config["split"]["shuffle"],
        random_state=config["split"]["random_state"],
    )
    y = pd.Series(y_train).reset_index(drop=True)
    groups = pd.Series(groups_train).reset_index(drop=True)
    X = X_train.reset_index(drop=True)
    if not (len(X) == len(y) == len(groups)):
        raise ValueError("X_train, y_train, groups_train의 행 수는 같아야 합니다.")
    weights = None if sample_weight_train is None else pd.Series(sample_weight_train).reset_index(drop=True)
    if weights is not None and len(weights) != len(X):
        raise ValueError("sample_weight_train의 행 수는 X_train과 같아야 합니다.")

    probability = np.full(len(X), np.nan, dtype="float64")
    folds = np.full(len(X), -1, dtype="int16")
    for fold, (fit_index, validation_index) in enumerate(splitter.split(X, y, groups)):
        fold_weights = None if weights is None else weights.iloc[fit_index]
        if tune:
            search = tune_model(
                X.iloc[fit_index], y.iloc[fit_index], groups.iloc[fit_index],
                model_name=model_name, feature_config=feature_config, model_config=config,
                search_method=search_method, sample_weight_train=fold_weights,
                parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
            )
            model = search.best_estimator_
        else:
            model = train_model(
                X.iloc[fit_index], y.iloc[fit_index], groups.iloc[fit_index],
                model_name=model_name, feature_config=feature_config, model_config=config,
                params=params, sample_weight_train=fold_weights,
            )
        probability[validation_index] = model.predict_proba(X.iloc[validation_index])[:, 1]
        folds[validation_index] = fold

    if np.isnan(probability).any() or (folds < 0).any():
        raise RuntimeError("일부 Train 행의 OOF 예측을 만들지 못했습니다.")
    return pd.DataFrame(
        {
            "row_index": np.arange(len(X)),
            "fold": folds,
            "SAMPID": groups.astype("string"),
            "y_true": y.astype("int8"),
            "y_probability": probability,
            "y_predicted": (probability >= config["tuning"]["threshold"]).astype("int8"),
        }
    )
