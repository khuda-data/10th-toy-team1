"""선택된 공통 설정으로 모델 Pipeline을 학습한다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from code.preprocess.preprocess import build_preprocessor


def load_model_config(model_config: str | Path | dict) -> dict:
    if isinstance(model_config, dict):
        return model_config
    with Path(model_config).open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def build_estimator(model_name: str, model_config: str | Path | dict, params: dict | None = None):
    """프로토콜에 정한 다섯 모델 중 하나를 같은 기본값으로 생성한다."""
    config = load_model_config(model_config)
    if model_name not in config["models"]:
        raise ValueError(f"지원하지 않는 공통 모델입니다: {model_name}")
    kwargs = dict(config["models"][model_name]["fixed"])
    kwargs.update(params or {})
    if model_name == "logistic_regression":
        return LogisticRegression(**kwargs)
    if model_name == "decision_tree":
        return DecisionTreeClassifier(**kwargs)
    if model_name == "random_forest":
        return RandomForestClassifier(**kwargs)
    if model_name == "xgboost":
        try:
            from xgboost import XGBClassifier
        except ImportError as error:
            raise ImportError("XGBoost를 사용하려면 code/requirements.txt의 xgboost를 설치하세요.") from error
        return XGBClassifier(**kwargs)
    if model_name == "lightgbm":
        try:
            from lightgbm import LGBMClassifier
        except ImportError as error:
            raise ImportError("LightGBM을 사용하려면 code/requirements.txt의 lightgbm을 설치하세요.") from error
        return LGBMClassifier(**kwargs)
    raise AssertionError("앞에서 검증한 모델 이름입니다.")


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups_train: pd.Series,
    *,
    model_name: str,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    params: dict | None = None,
) -> Pipeline:
    """Train DataFrame만 이용해 전처리와 분류기를 함께 fit한다.

    groups_train은 API 일관성과 호출부 검증을 위해 받는다. 실제 그룹은 tune_model의 CV에서 사용된다.
    """
    if groups_train.nunique() < 2:
        raise ValueError("SAMPID 그룹이 2개 이상 있어야 학습할 수 있습니다.")
    preprocessor = build_preprocessor(X_train, feature_config, model_name=model_name)
    model = build_estimator(model_name, model_config, params=params)
    pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
    return pipeline.fit(X_train, y_train)
