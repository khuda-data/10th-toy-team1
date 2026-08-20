"""Global Stage 2의 Train 내부 Feature 분석 함수.

이 모듈은 고정 Test Dataset을 받지 않는다. Stage 1에서 선택된 고정 파라미터로
SAMPID 그룹 CV를 다시 수행해 validation fold Permutation Importance와 보조적인
계수·XGBoost importance를 만든다. 반환값은 Feature를 삭제하거나 모델을 고르지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import StratifiedGroupKFold

from code.model.train import load_model_config, train_model
from code.preprocess.build_features import feature_columns_by_type, load_feature_config


@dataclass(frozen=True)
class CVFeatureAnalysisResult:
    """모델 하나의 CV 기반 Feature 분석 결과 묶음."""

    model: str
    permutation_summary: pd.DataFrame
    permutation_fold: pd.DataFrame
    coefficient_summary: pd.DataFrame | None = None
    coefficient_components: pd.DataFrame | None = None
    xgb_importance: pd.DataFrame | None = None


def _original_feature_name(transformed_name: str, original_features: list[str]) -> str:
    """ColumnTransformer의 출력명을 features.yaml 원 Feature 이름으로 되돌린다."""
    if "__" in transformed_name:
        _, transformed_name = transformed_name.split("__", 1)
    for feature in sorted(original_features, key=len, reverse=True):
        if transformed_name == feature or transformed_name.startswith(f"{feature}_"):
            return feature
    raise ValueError(f"전처리 출력명을 원 Feature에 연결하지 못했습니다: {transformed_name}")


def _transformed_feature_names(fitted_model, original_features: list[str]) -> list[str]:
    # RareCategoryGrouper는 원 Feature 열을 보존하지만 sklearn의 get_feature_names_out은
    # 구현하지 않는다. 실제 One-Hot 출력명은 뒤의 ColumnTransformer에서 가져온다.
    names = fitted_model.named_steps["preprocessor"].named_steps["columns"].get_feature_names_out()
    return [_original_feature_name(str(name), original_features) for name in names]


def _summarize_permutation(fold_values: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    grouped = fold_values.groupby("feature", sort=False)["importance_mean"]
    summary = grouped.agg(importance_mean="mean", importance_std=lambda values: values.std(ddof=0)).reindex(features)
    summary["importance_mean"] = summary["importance_mean"].fillna(0.0)
    summary["importance_std"] = summary["importance_std"].fillna(0.0)
    positive = fold_values.assign(positive=lambda frame: frame["importance_mean"] > 0).groupby("feature")["positive"].sum()
    summary["positive_fold_count"] = positive.reindex(features, fill_value=0).astype("int64")
    summary = summary.reset_index(names="feature")
    summary = summary.sort_values("importance_mean", ascending=False, kind="stable").reset_index(drop=True)
    summary["rank"] = np.arange(1, len(summary) + 1)
    return summary


def _coefficient_tables(
    fitted_model,
    *,
    fold: int,
    original_features: list[str],
) -> pd.DataFrame:
    coefficients = np.ravel(fitted_model.named_steps["model"].coef_)
    transformed_names = fitted_model.named_steps["preprocessor"].named_steps["columns"].get_feature_names_out()
    if len(coefficients) != len(transformed_names):
        raise RuntimeError("Logistic Regression 계수와 전처리 출력 Feature 수가 다릅니다.")
    output = pd.DataFrame(
        {
            "fold": fold,
            "transformed_feature": transformed_names.astype(str),
            "coefficient": coefficients.astype(float),
        }
    )
    output["feature"] = output["transformed_feature"].map(
        lambda name: _original_feature_name(name, original_features)
    )
    output["absolute_coefficient"] = output["coefficient"].abs()
    return output


def _summarize_coefficients(components: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    summary = (
        components.groupby("feature", sort=False)
        .agg(
            coefficient_mean=("coefficient", "mean"),
            coefficient_magnitude=("absolute_coefficient", "mean"),
            coefficient_abs_max=("absolute_coefficient", "max"),
        )
        .reindex(features)
        .fillna(0.0)
        .reset_index(names="feature")
    )
    summary["coefficient_direction"] = np.where(
        summary["coefficient_mean"] > 0,
        "positive",
        np.where(summary["coefficient_mean"] < 0, "negative", "zero_or_mixed"),
    )
    return summary.sort_values("coefficient_magnitude", ascending=False, kind="stable").reset_index(drop=True)


def _xgb_importance_table(
    fitted_model,
    *,
    fold: int,
    original_features: list[str],
) -> pd.DataFrame:
    """XGBoost의 전처리 후 dummy importance를 원 Feature별 gain/weight로 합친다."""
    estimator = fitted_model.named_steps["model"]
    booster = estimator.get_booster()
    transformed = list(fitted_model.named_steps["preprocessor"].named_steps["columns"].get_feature_names_out())
    gain = booster.get_score(importance_type="gain")
    weight = booster.get_score(importance_type="weight")

    def value(scores: dict[str, float], index: int, name: str) -> float:
        # sklearn Pipeline은 numpy 배열을 XGBoost에 넘기므로 대개 f0, f1 형식이다.
        return float(scores.get(f"f{index}", scores.get(name, 0.0)))

    rows = []
    for index, transformed_name in enumerate(transformed):
        rows.append(
            {
                "fold": fold,
                "feature": _original_feature_name(str(transformed_name), original_features),
                "gain": value(gain, index, str(transformed_name)),
                "weight": value(weight, index, str(transformed_name)),
            }
        )
    return pd.DataFrame(rows).groupby(["fold", "feature"], as_index=False, sort=False)[["gain", "weight"]].sum()


def run_cv_feature_analysis(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups_train: pd.Series,
    *,
    model_name: str,
    params: dict,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    n_repeats: int | None = None,
    n_jobs: int = 1,
) -> CVFeatureAnalysisResult:
    """고정 Stage 1 파라미터로 Train 내부 CV Feature 분석을 실행한다.

    Permutation Importance는 원 Feature DataFrame의 validation 열을 섞는다. 따라서
    One-Hot dummy가 아니라 features.yaml의 원 Feature 42개 단위로 반환된다.
    ``importance_std``는 각 fold에서 repeat 평균을 낸 뒤 그 다섯 값의 표준편차다.
    """
    config = load_model_config(model_config)
    feature_definition = load_feature_config(feature_config)
    features = list(X_train.columns)
    expected_features = [item["name"] for item in feature_definition["features"]]
    if features != expected_features:
        raise ValueError("Stage 2 Feature 분석은 features.yaml의 기본 42개 Feature 순서만 사용합니다.")
    if model_name not in config.get("official_comparison_models", []):
        raise ValueError(f"Stage 2 공식 비교 모델이 아닙니다: {model_name}")

    X = X_train.reset_index(drop=True)
    y = pd.Series(y_train).reset_index(drop=True)
    groups = pd.Series(groups_train).reset_index(drop=True)
    if not (len(X) == len(y) == len(groups)):
        raise ValueError("X_train, y_train, groups_train의 행 수는 같아야 합니다.")
    repeats = n_repeats or int(config["evaluation"]["permutation_repeats"])
    splitter = StratifiedGroupKFold(
        n_splits=config["split"]["cv_n_splits"],
        shuffle=config["split"]["shuffle"],
        random_state=config["split"]["random_state"],
    )

    permutation_rows: list[pd.DataFrame] = []
    coefficient_rows: list[pd.DataFrame] = []
    xgb_rows: list[pd.DataFrame] = []
    for fold, (fit_index, validation_index) in enumerate(splitter.split(X, y, groups)):
        fitted = train_model(
            X.iloc[fit_index], y.iloc[fit_index], groups.iloc[fit_index],
            model_name=model_name,
            feature_config=feature_definition,
            model_config=config,
            params=params,
            sample_weight_train=None,
        )
        permutation = permutation_importance(
            fitted,
            X.iloc[validation_index],
            y.iloc[validation_index],
            scoring=config["evaluation"]["permutation_scoring"],
            n_repeats=repeats,
            random_state=config["random_seed"] + fold,
            n_jobs=n_jobs,
        )
        permutation_rows.append(
            pd.DataFrame(
                {
                    "model": model_name,
                    "fold": fold,
                    "feature": features,
                    "importance_mean": permutation.importances_mean,
                    "importance_repeat_std": permutation.importances_std,
                    "n_repeats": repeats,
                }
            )
        )
        if model_name == "logistic_regression":
            coefficient_rows.append(_coefficient_tables(fitted, fold=fold, original_features=features))
        elif model_name == "xgboost":
            xgb_rows.append(_xgb_importance_table(fitted, fold=fold, original_features=features))

    permutation_fold = pd.concat(permutation_rows, ignore_index=True)
    permutation_summary = _summarize_permutation(permutation_fold, features)
    coefficient_components = pd.concat(coefficient_rows, ignore_index=True) if coefficient_rows else None
    coefficient_summary = (
        _summarize_coefficients(coefficient_components, features) if coefficient_components is not None else None
    )
    xgb_importance = None
    if xgb_rows:
        xgb_importance = (
            pd.concat(xgb_rows, ignore_index=True)
            .groupby("feature", sort=False)[["gain", "weight"]]
            .mean()
            .reindex(features, fill_value=0.0)
            .reset_index()
            .sort_values("gain", ascending=False, kind="stable")
            .reset_index(drop=True)
        )
    return CVFeatureAnalysisResult(
        model=model_name,
        permutation_summary=permutation_summary,
        permutation_fold=permutation_fold,
        coefficient_summary=coefficient_summary,
        coefficient_components=coefficient_components,
        xgb_importance=xgb_importance,
    )


def numeric_correlation_analysis(
    X_train: pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    abs_threshold: float = 0.70,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """수치형 원 Feature의 Pearson·Spearman 행렬과 높은 상관 pair 표를 반환한다.

    ``abs_threshold``는 표를 줄이기 위한 표시 기준일 뿐 Feature 삭제 규칙은 아니다.
    """
    config = load_feature_config(feature_config)
    numeric_features = [name for name in feature_columns_by_type(config, "numeric") if name in X_train.columns]
    numeric = X_train[numeric_features].apply(pd.to_numeric, errors="coerce")
    pearson = numeric.corr(method="pearson")
    spearman = numeric.corr(method="spearman")
    rows = []
    for first_index, first in enumerate(numeric_features):
        for second in numeric_features[first_index + 1 :]:
            pearson_value = pearson.loc[first, second]
            spearman_value = spearman.loc[first, second]
            values = np.abs([pearson_value, spearman_value])
            maximum = np.nan if np.isnan(values).all() else np.nanmax(values)
            if np.isfinite(maximum) and maximum >= abs_threshold:
                rows.append(
                    {
                        "feature_a": first,
                        "feature_b": second,
                        "pearson": pearson_value,
                        "spearman": spearman_value,
                        "max_abs_correlation": maximum,
                    }
                )
    pairs = pd.DataFrame(rows, columns=["feature_a", "feature_b", "pearson", "spearman", "max_abs_correlation"])
    if not pairs.empty:
        pairs = pairs.sort_values("max_abs_correlation", ascending=False, kind="stable").reset_index(drop=True)
    return pearson, spearman, pairs


def calculate_numeric_vif(
    X_train: pd.DataFrame,
    feature_config: str | Path | dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """다범주/One-Hot은 제외하고, 3개 이상 값이 있는 수치형 원 Feature만 VIF를 계산한다."""
    config = load_feature_config(feature_config)
    candidates = [name for name in feature_columns_by_type(config, "numeric") if name in X_train.columns]
    numeric = X_train[candidates].apply(pd.to_numeric, errors="coerce")
    audit_rows = []
    included = []
    for feature in candidates:
        unique_count = int(numeric[feature].dropna().nunique())
        if unique_count < 3:
            reason = "excluded_binary_or_low_variation"
        elif numeric[feature].dropna().empty:
            reason = "excluded_all_missing"
        else:
            reason = "included_multivalued_numeric"
            included.append(feature)
        audit_rows.append({"feature": feature, "n_unique_nonmissing": unique_count, "vif_scope": reason})
    scope = pd.DataFrame(audit_rows)
    if not included:
        return pd.DataFrame(columns=["feature", "vif"]), scope

    prepared = numeric[included].copy()
    prepared = prepared.fillna(prepared.median(numeric_only=True))
    values = []
    for feature in included:
        other_features = [name for name in included if name != feature]
        if not other_features:
            vif = 1.0
        else:
            r_squared = float(LinearRegression().fit(prepared[other_features], prepared[feature]).score(
                prepared[other_features], prepared[feature]
            ))
            vif = np.inf if r_squared >= 1 - 1e-12 else 1.0 / (1.0 - max(r_squared, 0.0))
        values.append({"feature": feature, "vif": vif})
    vif_table = pd.DataFrame(values).sort_values("vif", ascending=False, kind="stable").reset_index(drop=True)
    return vif_table, scope


def build_feature_selection_summary(
    feature_names: list[str],
    *,
    lr_analysis: CVFeatureAnalysisResult,
    xgb_analysis: CVFeatureAnalysisResult,
    pearson: pd.DataFrame,
    spearman: pd.DataFrame,
    vif_table: pd.DataFrame,
) -> pd.DataFrame:
    """42개 원 Feature를 사람이 함께 볼 수 있도록 지표를 한 표로 합친다."""
    summary = pd.DataFrame({"feature": feature_names})

    def merge_columns(frame: pd.DataFrame, columns: list[str], prefix: str) -> None:
        nonlocal summary
        renamed = frame[["feature", *columns]].rename(columns={column: f"{prefix}{column}" for column in columns})
        summary = summary.merge(renamed, on="feature", how="left")

    merge_columns(
        lr_analysis.permutation_summary,
        ["importance_mean", "importance_std", "positive_fold_count", "rank"],
        "lr_permutation_",
    )
    merge_columns(
        xgb_analysis.permutation_summary,
        ["importance_mean", "importance_std", "positive_fold_count", "rank"],
        "xgb_permutation_",
    )
    if lr_analysis.coefficient_summary is not None:
        merge_columns(lr_analysis.coefficient_summary, ["coefficient_magnitude", "coefficient_mean", "coefficient_direction"], "lr_")
    if xgb_analysis.xgb_importance is not None:
        merge_columns(xgb_analysis.xgb_importance, ["gain", "weight"], "xgb_")

    maximum_correlations = []
    numeric_features = set(pearson.index) | set(spearman.index)
    for feature in feature_names:
        values = []
        if feature in numeric_features:
            values.extend(pearson.loc[feature].drop(labels=feature, errors="ignore").abs().dropna().tolist())
            values.extend(spearman.loc[feature].drop(labels=feature, errors="ignore").abs().dropna().tolist())
        maximum_correlations.append(max(values) if values else np.nan)
    summary["max_abs_correlation"] = maximum_correlations
    summary = summary.merge(vif_table.rename(columns={"vif": "vif"}), on="feature", how="left")
    return summary
