"""반복관측 sensitivity Step 4의 Train-CV 진단용 계산 함수."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold

from code.evaluation.evaluate import calculate_binary_metrics
from code.model.train import train_model


def normalize_oof_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """저장 시점이 다른 OOF artifact의 예측 열 이름을 통일한다."""
    return frame.rename(columns={"y_proba": "y_probability", "y_pred": "y_predicted", "y_pred_at_0_5": "y_predicted"})


def subgroup_oof_metrics(oof: pd.DataFrame, group: pd.Series, *, group_name: str) -> pd.DataFrame:
    """OOF를 임의 그룹별로 나누어 비가중 row-level metric을 계산한다."""
    frame = normalize_oof_columns(oof).reset_index(drop=True).copy()
    frame[group_name] = pd.Series(group).reset_index(drop=True)
    rows = []
    for value, part in frame.groupby(group_name, dropna=False, sort=True):
        metric = calculate_binary_metrics(part["y_true"], part["y_probability"])
        rows.append({
            group_name: value, "rows": len(part), "unique_SAMPID": part["SAMPID"].nunique(),
            "positive_count": int(part["y_true"].sum()), "positive_rate": part["y_true"].mean(),
            "predicted_positive_rate": part["y_predicted"].mean(), **metric,
        })
    return pd.DataFrame(rows)


def paired_sampid_bootstrap_f1(
    left: pd.DataFrame, right: pd.DataFrame, *, repeats: int = 1000, random_state: int = 42
) -> pd.DataFrame:
    """같은 SAMPID 표본을 양 OOF에 적용한 paired bootstrap F1 차이를 계산한다."""
    left = normalize_oof_columns(left).sort_values(["SAMPID", "baseline_year"]).reset_index(drop=True)
    right = normalize_oof_columns(right).sort_values(["SAMPID", "baseline_year"]).reset_index(drop=True)
    keys = ["SAMPID", "baseline_year"]
    merged = left.merge(right, on=keys, suffixes=("_left", "_right"), validate="one_to_one")
    if not merged["y_true_left"].equals(merged["y_true_right"]):
        raise ValueError("paired bootstrap OOF의 y_true가 strategy 간 일치해야 합니다.")
    person_code, persons = pd.factorize(merged["SAMPID"], sort=False)
    n_persons = len(persons)

    def person_confusion(prediction_column: str) -> np.ndarray:
        """각 SAMPID의 TP·FP·FN을 한 번만 집계한다."""
        truth = merged["y_true_left"].to_numpy(dtype="int8")
        prediction = merged[prediction_column].to_numpy(dtype="int8")
        return np.column_stack([
            np.bincount(person_code, weights=((truth == 1) & (prediction == 1)), minlength=n_persons),
            np.bincount(person_code, weights=((truth == 0) & (prediction == 1)), minlength=n_persons),
            np.bincount(person_code, weights=((truth == 1) & (prediction == 0)), minlength=n_persons),
        ])

    left_counts = person_confusion("y_predicted_left")
    right_counts = person_confusion("y_predicted_right")

    def f1_from_counts(counts: np.ndarray) -> float:
        true_positive, false_positive, false_negative = counts
        denominator = 2 * true_positive + false_positive + false_negative
        return 0.0 if denominator == 0 else float(2 * true_positive / denominator)

    rng = np.random.default_rng(random_state)
    deltas = []
    for _ in range(repeats):
        sampled_index = rng.choice(n_persons, size=n_persons, replace=True)
        deltas.append(
            f1_from_counts(left_counts[sampled_index].sum(axis=0))
            - f1_from_counts(right_counts[sampled_index].sum(axis=0))
        )
    point = f1_from_counts(left_counts.sum(axis=0)) - f1_from_counts(right_counts.sum(axis=0))
    return pd.DataFrame([{"point_delta_f1": point, "bootstrap_mean_delta": float(np.mean(deltas)), "ci_lower": float(np.quantile(deltas, .025)), "ci_upper": float(np.quantile(deltas, .975)), "bootstrap_repeats": repeats}])


def cv_permutation_importance(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series, *, model_name: str,
    params: dict, feature_config: str | Path | dict, model_config: str | Path | dict,
    n_repeats: int = 20, random_state: int = 42,
) -> pd.DataFrame:
    """각 validation fold의 원 Feature permutation F1 감소량을 합친다. Test는 받지 않는다."""
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    X, y, groups = X.reset_index(drop=True), pd.Series(y).reset_index(drop=True), pd.Series(groups).reset_index(drop=True)
    records = []
    for fold, (fit_idx, valid_idx) in enumerate(splitter.split(X, y, groups)):
        model = train_model(X.iloc[fit_idx], y.iloc[fit_idx], groups.iloc[fit_idx], model_name=model_name, feature_config=feature_config, model_config=model_config, params=params)
        valid_X, valid_y = X.iloc[valid_idx], y.iloc[valid_idx]
        baseline = f1_score(valid_y, (model.predict_proba(valid_X)[:, 1] >= .5).astype("int8"), zero_division=0)
        rng = np.random.default_rng(random_state + fold)
        for feature in X.columns:
            for repeat in range(n_repeats):
                permuted = valid_X.copy()
                permuted[feature] = rng.permutation(permuted[feature].to_numpy())
                score = f1_score(valid_y, (model.predict_proba(permuted)[:, 1] >= .5).astype("int8"), zero_division=0)
                records.append({"fold": fold, "feature": feature, "repeat": repeat, "importance": baseline - score})
    repeats = pd.DataFrame(records)
    summary = repeats.groupby("feature", as_index=False).agg(importance_mean=("importance", "mean"), importance_std=("importance", "std"), positive_repeat_count=("importance", lambda x: int((x > 0).sum())), positive_fold_count=("fold", lambda x: int(repeats.loc[x.index].groupby("fold")["importance"].mean().gt(0).sum())))
    return summary.sort_values("importance_mean", ascending=False).assign(rank=lambda x: range(1, len(x) + 1))
