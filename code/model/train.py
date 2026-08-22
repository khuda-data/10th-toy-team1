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


WEIGHTED_CLASS_BALANCED = "weighted_class_balanced"


class FoldAwareLogisticRegression(LogisticRegression):
    """Fit fold의 sample_weight mass로 class_weight를 계산하는 LR이다.

    일반 ``LogisticRegression``의 공개 parameter 계약을 그대로 상속한다. sentinel은
    C-revised tuning에서만 opt-in으로 사용하며, fit 직전 숫자 dictionary로 치환된다.
    """

    def fit(self, X, y, sample_weight=None):
        if self.get_params().get("class_weight") == WEIGHTED_CLASS_BALANCED:
            if sample_weight is None:
                raise ValueError("weighted_class_balanced에는 sample_weight가 필요합니다.")
            target = pd.Series(y).reset_index(drop=True)
            weights = pd.Series(sample_weight).reset_index(drop=True).astype("float64")
            if len(target) != len(weights) or weights.isna().any() or weights.le(0).any():
                raise ValueError("weighted_class_balanced에는 y와 같은 길이의 양수 sample_weight가 필요합니다.")
            positive = float(weights[target.eq(1)].sum())
            negative = float(weights[target.eq(0)].sum())
            if positive <= 0 or negative <= 0:
                raise ValueError("weighted_class_balanced에는 두 class의 양수 weighted mass가 필요합니다.")
            total = positive + negative
            self.set_params(class_weight={0: total / (2 * negative), 1: total / (2 * positive)})
        return super().fit(X, y, sample_weight=sample_weight)


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
        if kwargs.get("class_weight") == WEIGHTED_CLASS_BALANCED:
            return FoldAwareLogisticRegression(**kwargs)
        return LogisticRegression(**kwargs)
    if model_name == "decision_tree":
        return DecisionTreeClassifier(**kwargs)
    if model_name == "random_forest":
        return RandomForestClassifier(**kwargs)
    if model_name == "xgboost":
        from code.model.xgboost import FoldAwareXGBClassifier

        return FoldAwareXGBClassifier(**kwargs)
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
    sample_weight_train: pd.Series | None = None,
) -> Pipeline:
    """Train DataFrame만 이용해 전처리와 분류기를 함께 fit한다.

    groups_train은 API 일관성과 호출부 검증을 위해 받는다. 실제 그룹은 tune_model의 CV에서 사용된다.
    """
    if groups_train.nunique() < 2:
        raise ValueError("SAMPID 그룹이 2개 이상 있어야 학습할 수 있습니다.")
    preprocessor = build_preprocessor(X_train, feature_config, model_name=model_name)
    model = build_estimator(model_name, model_config, params=params)
    pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
    fit_params = {} if sample_weight_train is None else {"model__sample_weight": sample_weight_train}
    return pipeline.fit(X_train, y_train, **fit_params)
