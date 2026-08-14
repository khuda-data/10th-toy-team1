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
        self.columns = list(columns)
        self.min_frequency = min_frequency
        self.other_label = other_label
        self.protected_categories = list(protected_categories)

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
            frame.loc[values.isin(rare), column] = self.other_label
        return frame


def build_preprocessor(
    X_train: pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    model_name: str,
) -> Pipeline:
    """프로토콜의 결측·희소범주·One-Hot·Logistic 스케일링 규칙을 반환한다.

    반환 Pipeline은 아직 fit하지 않은 객체다. `train_model()` 또는 `tune_model()`이 Train에서만 fit한다.
    """
    config = load_feature_config(feature_config)
    numeric_columns = feature_columns_by_type(config, "numeric")
    categorical_columns = feature_columns_by_type(config, "categorical")
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
