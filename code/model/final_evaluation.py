"""Global Stage 4의 고정 후보 최종 Test 평가 준비 기능."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from code.contracts import DatasetBundle
from code.evaluation.evaluate import calculate_binary_metrics
from code.model.train import train_model
from code.pipeline.saved_results import select_bundle_features


@dataclass(frozen=True)
class FinalCandidate:
    """Stage 4에 올린 고정 모델·Feature·파라미터 조합."""

    key: str
    model: str
    stage: str
    feature_names: tuple[str, ...]
    params: dict


def load_final_candidates(
    *,
    stage_1_dir: str | Path,
    stage_3_5_dir: str | Path,
    selected_features_path: str | Path,
    all_feature_names: list[str],
) -> list[FinalCandidate]:
    """Stage 1/3.5 artifact만 읽어 네 고정 후보를 복원한다. Test Dataset은 읽지 않는다."""
    stage_1_dir, stage_3_5_dir = Path(stage_1_dir), Path(stage_3_5_dir)
    with (stage_1_dir / "best_params.json").open(encoding="utf-8") as file:
        stage_1_params = json.load(file)
    with (stage_3_5_dir / "final_refined_params.json").open(encoding="utf-8") as file:
        refined_params = json.load(file)
    selected = pd.read_csv(selected_features_path)["feature"].tolist()
    if len(all_feature_names) != 42 or len(selected) != 25 or len(set(selected)) != 25:
        raise ValueError("Stage 4 후보는 42개 1차 Feature와 중복 없는 25개 2차 Feature가 필요합니다.")
    required = {
        "stage_1": {"logistic_regression", "xgboost"},
        "stage_3_5": {"logistic_regression", "xgboost"},
    }
    if not required["stage_1"] <= set(stage_1_params) or not required["stage_3_5"] <= set(refined_params):
        raise ValueError("Stage 1 또는 Stage 3.5 최종 파라미터 artifact에 필요한 모델이 없습니다.")
    return [
        FinalCandidate("lr_stage_1", "logistic_regression", "stage_1", tuple(all_feature_names), stage_1_params["logistic_regression"]),
        FinalCandidate("lr_stage_2", "logistic_regression", "stage_2", tuple(selected), refined_params["logistic_regression"]),
        FinalCandidate("xgb_stage_1", "xgboost", "stage_1", tuple(all_feature_names), stage_1_params["xgboost"]),
        FinalCandidate("xgb_stage_2", "xgboost", "stage_2", tuple(selected), refined_params["xgboost"]),
    ]


def fit_final_candidates(
    train_bundle: DatasetBundle,
    candidates: list[FinalCandidate],
    *,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
) -> dict[str, object]:
    """Train 전체에서만 전처리 fit 후 고정 후보를 학습한다."""
    fitted = {}
    for candidate in candidates:
        subset = select_bundle_features(train_bundle, list(candidate.feature_names), name=candidate.key)
        fitted[candidate.key] = train_model(
            subset.X, subset.y, subset.groups, model_name=candidate.model,
            feature_config=feature_config, model_config=model_config, params=candidate.params,
            sample_weight_train=None,
        )
    return fitted


def predict_final_candidates(
    test_bundle: DatasetBundle,
    candidates: list[FinalCandidate],
    fitted_models: dict[str, object],
    *,
    threshold: float = 0.5,
) -> dict[str, pd.DataFrame]:
    """고정 Test에서 후보별 확률·0.5 예측을 만든다. Stage 4 Notebook에서만 호출한다."""
    if not 0 < threshold < 1:
        raise ValueError("threshold는 0과 1 사이여야 합니다.")
    if "baseline_year" not in test_bundle.metadata:
        raise ValueError("Test prediction 저장에는 baseline_year metadata가 필요합니다.")
    predictions = {}
    for candidate in candidates:
        if candidate.key not in fitted_models:
            raise KeyError(f"학습된 후보가 없습니다: {candidate.key}")
        subset = select_bundle_features(test_bundle, list(candidate.feature_names), name=candidate.key)
        probability = fitted_models[candidate.key].predict_proba(subset.X)[:, 1]
        predictions[candidate.key] = pd.DataFrame(
            {
                "SAMPID": subset.groups.astype("string"),
                "baseline_year": subset.metadata["baseline_year"],
                "y_true": subset.y.astype("int8"),
                "y_proba": probability,
                "y_pred": (probability >= threshold).astype("int8"),
            }
        )
    return predictions


def summarize_final_predictions(
    predictions: dict[str, pd.DataFrame],
    candidates: list[FinalCandidate],
    *,
    threshold: float = 0.5,
) -> tuple[pd.DataFrame, dict[str, list[list[int]]]]:
    """Test prediction을 공통 성능·표본 요약으로 정리한다."""
    rows, matrices = [], {}
    candidate_by_key = {candidate.key: candidate for candidate in candidates}
    for key, frame in predictions.items():
        candidate = candidate_by_key[key]
        metrics = calculate_binary_metrics(frame["y_true"], frame["y_proba"], threshold=threshold)
        rows.append(
            {
                "candidate": key, "model": candidate.model, "stage": candidate.stage,
                "feature_count": len(candidate.feature_names), "test_rows": len(frame),
                "test_unique_SAMPID": frame["SAMPID"].nunique(), "positive_count": int(frame["y_true"].sum()),
                "negative_count": int((frame["y_true"] == 0).sum()), "positive_rate": float(frame["y_true"].mean()),
                "predicted_positive_count": int(frame["y_pred"].sum()), "predicted_positive_rate": float(frame["y_pred"].mean()),
                "test_accuracy": metrics["accuracy"], "test_precision": metrics["precision"],
                "test_recall": metrics["recall"], "test_f1": metrics["f1"],
                "test_roc_auc": metrics["roc_auc"], "test_average_precision": metrics["average_precision"],
                "best_params": candidate.params,
            }
        )
        matrices[key] = metrics["confusion_matrix"]
    return pd.DataFrame(rows), matrices


def load_stage4_cv_f1(stage_1_dir: str | Path, stage_3_5_dir: str | Path) -> pd.DataFrame:
    """기존 Train-CV artifact만 읽어 Stage 4의 CV-vs-Test 비교 입력을 만든다."""
    stage_1 = pd.read_csv(Path(stage_1_dir) / "first_stage_summary.csv")
    stage_3_5 = pd.read_csv(Path(stage_3_5_dir) / "final_tuning_summary.csv")
    stage_1 = stage_1.loc[:, ["model", "cv_f1_mean"]].assign(stage="stage_1")
    stage_2 = stage_3_5.query("stage == 'stage_3_5'").loc[:, ["model", "cv_f1_mean"]].assign(stage="stage_2")
    return pd.concat([stage_1, stage_2], ignore_index=True)


def save_final_test_artifacts(
    *,
    output_dir: str | Path,
    summary: pd.DataFrame,
    bootstrap_ci: pd.DataFrame,
    pairwise_bootstrap: pd.DataFrame,
    predictions: dict[str, pd.DataFrame],
    permutation_importance: dict[str, pd.DataFrame],
    confusion_matrices: dict[str, list[list[int]]],
) -> dict[str, Path]:
    """Stage 4 Notebook 실행 시 최종 Test artifact를 정해진 파일명으로 저장한다."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    paths = {
        "final_test_summary": destination / "final_test_summary.csv",
        "final_test_bootstrap_ci": destination / "final_test_bootstrap_ci.csv",
        "final_test_pairwise_bootstrap": destination / "final_test_pairwise_bootstrap.csv",
        "final_test_predictions": destination / "final_test_predictions.parquet",
        "final_model_comparison": destination / "final_model_comparison.csv",
        "confusion_matrices": destination / "final_test_confusion_matrices.json",
    }
    summary.to_csv(paths["final_test_summary"], index=False)
    bootstrap_ci.to_csv(paths["final_test_bootstrap_ci"], index=False)
    pairwise_bootstrap.to_csv(paths["final_test_pairwise_bootstrap"], index=False)
    summary.to_csv(paths["final_model_comparison"], index=False)
    pd.concat([frame.assign(candidate=key) for key, frame in predictions.items()], ignore_index=True).to_parquet(paths["final_test_predictions"], index=False)
    with paths["confusion_matrices"].open("w", encoding="utf-8") as file:
        json.dump(confusion_matrices, file, ensure_ascii=False, indent=2)
    for key, frame in permutation_importance.items():
        filename = "logistic_regression_final_permutation_importance.csv" if key == "lr_stage_2" else "xgboost_final_permutation_importance.csv"
        path = destination / filename
        frame.to_csv(path, index=False)
        paths[f"{key}_permutation_importance"] = path
    return paths
