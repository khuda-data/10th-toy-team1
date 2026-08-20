"""Global Stage 3.5의 제한된 하이퍼파라미터 refinement 공용 기능."""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import prod
from pathlib import Path

import pandas as pd

from code.contracts import DatasetBundle
from code.evaluation.evaluate import calculate_binary_metrics
from code.evaluation.oof import generate_oof_predictions
from code.evaluation.threshold import calculate_threshold_sensitivity, summarize_threshold_sensitivity
from code.model.first_stage import FirstStageModelResult
from code.model.train import load_model_config
from code.model.tune import tune_model


@dataclass(frozen=True)
class RefinementSearchResult:
    """한 제한 GridSearch의 전체 결과와 최적 파라미터."""

    model: str
    refinement_stage: str
    best_params: dict
    best_cv_f1: float
    fold_f1: tuple[float, ...]
    cv_f1_mean: float
    cv_f1_std: float
    cv_results: pd.DataFrame


@dataclass(frozen=True)
class RefinedModelResult:
    """최종 refinement 후보의 GridSearch·OOF 결과 묶음."""

    search: RefinementSearchResult
    model_result: FirstStageModelResult


def count_grid_combinations(param_grid: dict[str, list]) -> int:
    """명시 Grid의 Cartesian 조합 수를 반환한다."""
    return prod(len(values) for values in param_grid.values())


def refinement_config(model_config: str | Path | dict) -> dict:
    """Stage 3.5에 한정된 사람이 지정한 refinement 범위를 읽는다."""
    config = load_model_config(model_config)
    try:
        return config["final_hyperparameter_refinement"]
    except KeyError as error:
        raise KeyError("model_config.yaml에 final_hyperparameter_refinement 설정이 없습니다.") from error


def _search_result(
    train_bundle: DatasetBundle,
    *,
    model_name: str,
    refinement_stage: str,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    param_grid: dict[str, list],
    fixed_model_params: dict | None = None,
    runtime_model_params: dict | None = None,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> RefinementSearchResult:
    """GridSearch 결과를 공통 형태로 정리한다. Test Dataset은 받지 않는다."""
    config = load_model_config(model_config)
    estimator_params = dict(fixed_model_params or {})
    estimator_params.update(runtime_model_params or {})
    search = tune_model(
        train_bundle.X,
        train_bundle.y,
        train_bundle.groups,
        model_name=model_name,
        feature_config=feature_config,
        model_config=config,
        param_grid=param_grid,
        estimator_params=estimator_params or None,
        sample_weight_train=None,
        parallel_backend_name=parallel_backend_name,
        n_jobs=n_jobs,
    )
    best_index = int(search.best_index_)
    selected = {
        name.removeprefix("model__"): value
        for name, value in search.best_params_.items()
        if name.startswith("model__")
    }
    best_params = dict(fixed_model_params or {})
    best_params.update(selected)
    cv_results = pd.DataFrame(search.cv_results_).rename(
        columns=lambda column: column.replace("param_model__", "param_")
    )
    return RefinementSearchResult(
        model=model_name,
        refinement_stage=refinement_stage,
        best_params=best_params,
        best_cv_f1=float(search.best_score_),
        fold_f1=tuple(
            float(search.cv_results_[f"split{fold}_test_score"][best_index])
            for fold in range(config["split"]["cv_n_splits"])
        ),
        cv_f1_mean=float(search.cv_results_["mean_test_score"][best_index]),
        cv_f1_std=float(search.cv_results_["std_test_score"][best_index]),
        cv_results=cv_results,
    )


def run_lr_refinement(
    train_bundle: DatasetBundle,
    *,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> RefinedModelResult:
    """사람이 지정한 28개 LR 조합으로 Stage 3.5 refinement와 OOF를 실행한다."""
    grid = refinement_config(model_config)["logistic_regression"]
    search_result = _search_result(
        train_bundle,
        model_name="logistic_regression",
        refinement_stage="lr",
        feature_config=feature_config,
        model_config=model_config,
        param_grid=grid,
        parallel_backend_name=parallel_backend_name,
        n_jobs=n_jobs,
    )
    return _finalize_refined_model(
        train_bundle, search_result, feature_config=feature_config, model_config=model_config,
        runtime_model_params=None,
    )


def run_xgb_refinement_stage_a(
    train_bundle: DatasetBundle,
    *,
    stage3_params: dict,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> RefinementSearchResult:
    """Tree structure/learning 81개 조합을 Stage 3 XGB 기준선 주변에서 탐색한다."""
    grid = refinement_config(model_config)["xgboost"]["stage_a"]
    fixed = {key: stage3_params[key] for key in ("subsample", "colsample_bytree", "scale_pos_weight") if key in stage3_params}
    return _search_result(
        train_bundle, model_name="xgboost", refinement_stage="xgb_stage_a",
        feature_config=feature_config, model_config=model_config, param_grid=grid,
        fixed_model_params=fixed, runtime_model_params={"n_jobs": 1},
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )


def run_xgb_refinement_stage_b(
    train_bundle: DatasetBundle,
    *,
    stage_a_params: dict,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> RefinementSearchResult:
    """Stage A 최적값을 고정하고 sampling/split regularization 27개 조합을 탐색한다."""
    grid = refinement_config(model_config)["xgboost"]["stage_b"]
    return _search_result(
        train_bundle, model_name="xgboost", refinement_stage="xgb_stage_b",
        feature_config=feature_config, model_config=model_config, param_grid=grid,
        fixed_model_params=stage_a_params, runtime_model_params={"n_jobs": 1},
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )


def run_xgb_refinement_stage_c(
    train_bundle: DatasetBundle,
    *,
    stage_b_params: dict,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> RefinedModelResult:
    """Stage A/B 최적값을 고정하고 L1/L2 regularization 9개 조합과 최종 OOF를 만든다."""
    grid = refinement_config(model_config)["xgboost"]["stage_c"]
    search_result = _search_result(
        train_bundle, model_name="xgboost", refinement_stage="xgb_stage_c",
        feature_config=feature_config, model_config=model_config, param_grid=grid,
        fixed_model_params=stage_b_params, runtime_model_params={"n_jobs": 1},
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )
    return _finalize_refined_model(
        train_bundle, search_result, feature_config=feature_config, model_config=model_config,
        runtime_model_params={"n_jobs": 1},
    )


def _finalize_refined_model(
    train_bundle: DatasetBundle,
    search_result: RefinementSearchResult,
    *,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    runtime_model_params: dict | None,
) -> RefinedModelResult:
    """선택된 고정 최적 파라미터로 Train OOF를 만든다."""
    config = load_model_config(model_config)
    final_params = dict(search_result.best_params)
    final_params.update(runtime_model_params or {})
    oof = generate_oof_predictions(
        train_bundle.X, train_bundle.y, train_bundle.groups,
        model_name=search_result.model, feature_config=feature_config, model_config=config,
        params=final_params, sample_weight_train=None,
    )
    threshold = config["tuning"]["threshold"]
    metrics = calculate_binary_metrics(oof["y_true"], oof["y_probability"], threshold=threshold)
    model_result = FirstStageModelResult(
        model=search_result.model,
        n_features=len(train_bundle.X.columns),
        best_params=search_result.best_params,
        best_cv_f1=search_result.best_cv_f1,
        fold_f1=search_result.fold_f1,
        cv_f1_mean=search_result.cv_f1_mean,
        cv_f1_std=search_result.cv_f1_std,
        oof_metrics=metrics,
        oof_predictions=oof,
    )
    return RefinedModelResult(search=search_result, model_result=model_result)


def create_final_oof_predictions(result: FirstStageModelResult, train_bundle: DatasetBundle) -> pd.DataFrame:
    """최종 OOF parquet 계약(SAMPID·baseline_year·확률·0.5 예측·fold)을 만든다."""
    if "baseline_year" not in train_bundle.metadata:
        raise ValueError("최종 OOF 저장에는 Train metadata의 baseline_year가 필요합니다.")
    oof = result.oof_predictions.copy()
    baseline_year = train_bundle.metadata["baseline_year"].reset_index(drop=True)
    if len(oof) != len(baseline_year):
        raise ValueError("OOF와 Train metadata 행 수가 다릅니다.")
    return pd.DataFrame(
        {
            "SAMPID": oof["SAMPID"].astype("string"),
            "baseline_year": baseline_year,
            "y_true": oof["y_true"].astype("int8"),
            "y_proba": oof["y_probability"],
            "y_pred_at_0_5": oof["y_predicted"].astype("int8"),
            "fold": oof["fold"].astype("int16"),
        }
    )


def stage3_parameter_comparison(stage3_params: dict[str, dict]) -> pd.DataFrame:
    """요청서에 명시된 Stage 3 기준 파라미터와 저장 artifact의 차이를 표시한다."""
    expected = {
        "logistic_regression": {"C": 0.1, "penalty": "l2", "class_weight": "balanced"},
        "xgboost": {
            "max_depth": 3, "learning_rate": 0.03, "n_estimators": 500,
            "min_child_weight": 5, "subsample": 1.0, "colsample_bytree": 0.8,
            "scale_pos_weight": "train_negative_positive_ratio",
        },
    }
    rows = []
    for model, expected_params in expected.items():
        actual = stage3_params.get(model, {})
        rows.append(
            {
                "model": model,
                "expected_params": expected_params,
                "saved_stage_3_params": actual,
                "matches_request": actual == expected_params,
            }
        )
    return pd.DataFrame(rows)


def boundary_flags(params: dict, param_grid: dict[str, list]) -> dict[str, bool]:
    """선택값이 지정 탐색 범위의 양 끝값인지 표시한다. 범위 확장은 하지 않는다."""
    return {
        parameter: params.get(parameter) in {values[0], values[-1]}
        for parameter, values in param_grid.items()
    }


def save_final_tuning_artifacts(
    *,
    output_dir: str | Path,
    stage3_summary: pd.DataFrame,
    stage3_fold_f1: dict[str, tuple[float, ...]],
    lr_refinement: RefinedModelResult,
    xgb_stage_a: RefinementSearchResult,
    xgb_stage_b: RefinementSearchResult,
    xgb_refinement: RefinedModelResult,
    train_bundle: DatasetBundle,
) -> dict[str, Path]:
    """Stage 3.5 전용 artifact를 저장한다. 기존 Stage 3 파일은 수정하지 않는다."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    refined_results = [lr_refinement.model_result, xgb_refinement.model_result]
    refined_summary = pd.DataFrame([result.summary_row() for result in refined_results]).rename(
        columns={"n_features": "feature_count"}
    )
    refined_summary["stage"] = "stage_3_5"
    baseline = stage3_summary.rename(columns={"n_features": "feature_count"}).copy()
    baseline["stage"] = "stage_3"
    columns = [
        "model", "stage", "feature_count", "cv_f1_mean", "cv_f1_std", "oof_precision", "oof_recall",
        "oof_f1", "oof_roc_auc", "best_params",
    ]
    summary = pd.concat([baseline, refined_summary], ignore_index=True).loc[:, columns]
    paths = {"final_tuning_summary": destination / "final_tuning_summary.csv"}
    summary.to_csv(paths["final_tuning_summary"], index=False)

    search_paths = {
        "lr_refinement_results": (lr_refinement.search.cv_results, "lr_refinement_results.csv"),
        "xgb_refinement_stage_a": (xgb_stage_a.cv_results, "xgb_refinement_stage_a.csv"),
        "xgb_refinement_stage_b": (xgb_stage_b.cv_results, "xgb_refinement_stage_b.csv"),
        "xgb_refinement_stage_c": (xgb_refinement.search.cv_results, "xgb_refinement_stage_c.csv"),
    }
    for name, (frame, filename) in search_paths.items():
        path = destination / filename
        frame.to_csv(path, index=False)
        paths[name] = path

    params_path = destination / "final_refined_params.json"
    with params_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "logistic_regression": lr_refinement.model_result.best_params,
                "xgboost_stage_a": xgb_stage_a.best_params,
                "xgboost_stage_b": xgb_stage_b.best_params,
                "xgboost": xgb_refinement.model_result.best_params,
            },
            file, ensure_ascii=False, indent=2,
        )
    paths["final_refined_params"] = params_path

    fold_path = destination / "final_fold_f1.json"
    with fold_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "stage_3": {model: list(values) for model, values in stage3_fold_f1.items()},
                "stage_3_5": {result.model: list(result.fold_f1) for result in refined_results},
            },
            file, ensure_ascii=False, indent=2,
        )
    paths["final_fold_f1"] = fold_path

    sensitivity = pd.concat(
        [
            calculate_threshold_sensitivity(
                result.model_result.oof_predictions["y_true"], result.model_result.oof_predictions["y_probability"],
                model=result.model_result.model,
            )
            for result in (lr_refinement, xgb_refinement)
        ],
        ignore_index=True,
    )
    sensitivity_path = destination / "threshold_sensitivity.csv"
    sensitivity.to_csv(sensitivity_path, index=False)
    paths["threshold_sensitivity"] = sensitivity_path
    threshold_summary_path = destination / "threshold_summary.csv"
    summarize_threshold_sensitivity(sensitivity).to_csv(threshold_summary_path, index=False)
    paths["threshold_summary"] = threshold_summary_path

    for refined in (lr_refinement, xgb_refinement):
        path = destination / f"refined_{refined.model_result.model}_oof_predictions.parquet"
        create_final_oof_predictions(refined.model_result, train_bundle).to_parquet(path, index=False)
        paths[f"refined_{refined.model_result.model}_oof"] = path
    return paths
