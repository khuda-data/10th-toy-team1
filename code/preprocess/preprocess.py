"""Train에서만 fit하는 Global/Local 공통 sklearn 전처리 Pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from code.preprocess.build_features import feature_columns_by_type, load_feature_config


class RareCategoryGrouper(BaseEstimator, TransformerMixin):
    """Train에서 10건 미만인 범주만 Other로 합치고 Missing/NotApplicable은 보존한다."""

    def __init__(
        self,
        columns: Iterable[str],
        min_frequency: int = 10,
        other_label: str = "Other",
        protected_categories: Iterable[str] = ("Missing", "NotApplicable"),
    ) -> None:
        # sklearn.clone()은 __init__ 인자를 변형하지 않고 그대로 속성에 보관해야 한다.
        # list()로 새 객체를 만들면 GridSearchCV가 clone 단계에서 실패한다.
        self.columns = columns
        self.min_frequency = min_frequency
        self.other_label = other_label
        self.protected_categories = protected_categories

    def fit(self, X: pd.DataFrame, y: object = None) -> "RareCategoryGrouper":
        frame = pd.DataFrame(X)
        self.rare_values_: dict[str, set[str]] = {}
        for column in self.columns:
            counts = frame[column].dropna().astype("string").value_counts()
            rare = set(counts[counts < self.min_frequency].index.astype(str)) - set(self.protected_categories)
            self.rare_values_[column] = rare
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        frame = pd.DataFrame(X).copy()
        for column, rare in self.rare_values_.items():
            values = frame[column].astype("string")
            rare_mask = values.isin(rare)
            if rare_mask.any():
                # pandas의 Categorical 열은 미리 정의하지 않은 "Other" 값을 바로 대입하면
                # LossySetitemError를 낸다. 희소 범주를 Other로 묶는 기존 규칙은 그대로 두고,
                # 대입 전 object로 바꿔 pandas 버전과 무관하게 안전하게 처리한다.
                frame[column] = frame[column].astype(object)
                frame.loc[rare_mask, column] = self.other_label
        return frame


def build_preprocessor(
    X_train: pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    model_name: str,
) -> Pipeline:
    """프로토콜의 결측·희소범주·One-Hot·Logistic 스케일링 규칙을 반환한다.

    반환 Pipeline은 아직 fit하지 않은 객체다. `train_model()` 또는 `tune_model()`이 Train에서만 fit한다.
    numeric/categorical 컬럼 목록은 X_train에 실제로 있는 컬럼만 쓴다 — n_prior_periods 같은
    optional_features는 build_features(..., extra_features=...)로 켰을 때만 X_train에 있으므로,
    이렇게 하면 train_model/tune_model에 별도 플래그를 안 넘겨도 자동으로 맞춰진다(2026-08-18).
    """
    config = load_feature_config(feature_config)
    optional_names = [item["name"] for item in config.get("optional_features", [])]
    numeric_columns = [
        column
        for column in feature_columns_by_type(config, "numeric", extra_features=optional_names)
        if column in X_train.columns
    ]
    categorical_columns = [
        column
        for column in feature_columns_by_type(config, "categorical", extra_features=optional_names)
        if column in X_train.columns
    ]
    missing_or_empty = [column for column in X_train.columns if X_train[column].isna().all()]
    if missing_or_empty:
        raise ValueError(
            "아래 Feature가 전부 비어 있어 모델링할 수 없습니다. 0으로 대체하지 말고 코드북·분기 규칙을 구현하세요: "
            + ", ".join(missing_or_empty)
        )

    preprocessing = config["preprocessing"]
    numeric_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if model_name in preprocessing["scaler_models"]:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric_pipeline = Pipeline(numeric_steps)
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value=preprocessing["categorical_missing_label"])),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    transformer = ColumnTransformer(
        [("numeric", numeric_pipeline, numeric_columns), ("categorical", categorical_pipeline, categorical_columns)],
        remainder="drop",
    )
    return Pipeline(
        [
            (
                "rare_categories",
                RareCategoryGrouper(
                    categorical_columns,
                    min_frequency=preprocessing["rare_category_min_frequency"],
                    other_label=preprocessing["rare_category_label"],
                    protected_categories=preprocessing["protected_categories"],
                ),
            ),
            ("columns", transformer),
        ]
    )
