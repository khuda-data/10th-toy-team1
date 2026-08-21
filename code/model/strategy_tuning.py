"""반복관측 sensitivity B/C 전용 Train-CV 재튜닝 기능.

공식 Global Stage 1~4의 기본 탐색 경로는 변경하지 않는다. 이 모듈은 Step 3 Notebook에서만
명시적으로 호출하며, Test Dataset을 입력으로 받지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import prod
from pathlib import Path

import pandas as pd

from code.contracts import DatasetBundle
from code.evaluation.evaluate import calculate_binary_metrics
from code.evaluation.oof import generate_oof_predictions
from code.model.locked_sensitivity import (
    LockedModelResult,
    create_locked_oof_artifact,
    run_weighted_class_locked_oof,
)
from code.model.train import WEIGHTED_CLASS_BALANCED, load_model_config
from code.model.tune import tune_model
from code.model.xgboost import (
    TRAIN_NEGATIVE_POSITIVE_RATIO,
    TRAIN_WEIGHTED_NEGATIVE_POSITIVE_RATIO,
)


@dataclass(frozen=True)
class StrategySearchResult:
    """한 strategy-specific GridSearch의 결과와 선택된 parameter."""

    model: str
    stage: str
    best_params: dict
    best_cv_f1: float
    fold_f1: tuple[float, ...]
    cv_f1_mean: float
    cv_f1_std: float
    cv_results: pd.DataFrame


@dataclass(frozen=True)
class StrategyTunedResult:
    """최종 best parameter의 CV·비가중 OOF 결과."""

    strategy: str
    search: StrategySearchResult
    metrics: dict
    oof_predictions: pd.DataFrame
    audit: pd.DataFrame | None = None

    def summary_row(self) -> dict:
        return {
            "strategy": self.strategy,
            "model": self.search.model,
            "feature_count": None,  # save 함수에서 bundle feature 수로 채운다.
            "best_cv_f1": self.search.best_cv_f1,
            "cv_f1_mean": self.search.cv_f1_mean,
            "cv_f1_std": self.search.cv_f1_std,
            "oof_accuracy": self.metrics["accuracy"],
            "oof_precision": self.metrics["precision"],
            "oof_recall": self.metrics["recall"],
            "oof_f1": self.metrics["f1"],
            "oof_roc_auc": self.metrics["roc_auc"],
            "oof_average_precision": self.metrics["average_precision"],
            "predicted_positive_rate": float(self.oof_predictions["y_predicted"].mean()),
            "best_params": self.search.best_params,
        }


def step3_tuning_grids(model_config: str | Path | dict, *, strategy: str) -> dict:
    """요청서에 고정된 B/C Step 3 제한 Grid를 반환한다."""
    config = load_model_config(model_config)
    refinement = config["final_hyperparameter_refinement"]
    lr_grid = {name: list(values) for name, values in refinement["logistic_regression"].items()}
    if strategy == "C":
        lr_grid.pop("class_weight")
    elif strategy != "B":
        raise ValueError("strategy는 'B' 또는 'C'여야 합니다.")
    return {
        "logistic_regression": lr_grid,
        "xgboost": {
            stage: {name: list(values) for name, values in grid.items()}
            for stage, grid in refinement["xgboost"].items()
        },
    }


def count_grid_combinations(grid: dict[str, list]) -> int:
    """명시된 Grid의 조합 수를 계산한다."""
    return prod(len(values) for values in grid.values())


def _search(
    bundle: DatasetBundle,
    *,
    model_name: str,
    stage: str,
    param_grid: dict[str, list],
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    fixed_params: dict | None = None,
    sample_weight_train: pd.Series | None = None,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> StrategySearchResult:
    """한 GridSearch를 실행할 코드를 만들고 결과를 공통 계약으로 정리한다."""
    config = load_model_config(model_config)
    search = tune_model(
        bundle.X,
        bundle.y,
        bundle.groups,
        model_name=model_name,
        feature_config=feature_config,
        model_config=config,
        param_grid=param_grid,
        estimator_params=fixed_params,
        sample_weight_train=sample_weight_train,
        parallel_backend_name=parallel_backend_name,
        n_jobs=n_jobs,
    )
    best_index = int(search.best_index_)
    selected = {
        name.removeprefix("model__"): value
        for name, value in search.best_params_.items()
        if name.startswith("model__")
    }
    params = dict(fixed_params or {})
    params.update(selected)
    return StrategySearchResult(
        model=model_name,
        stage=stage,
        best_params=params,
        best_cv_f1=float(search.best_score_),
        fold_f1=tuple(
            float(search.cv_results_[f"split{fold}_test_score"][best_index])
            for fold in range(config["split"]["cv_n_splits"])
        ),
        cv_f1_mean=float(search.cv_results_["mean_test_score"][best_index]),
        cv_f1_std=float(search.cv_results_["std_test_score"][best_index]),
        cv_results=pd.DataFrame(search.cv_results_).rename(
            columns=lambda column: column.replace("param_model__", "param_")
        ),
    )


def _xgb_fixed_params(previous: dict, grid: dict[str, list], *, balance_marker: str) -> dict:
    """직전 단계 best에서 이번 단계 search 축만 제외하고 class-balance marker를 고정한다."""
    fixed = {name: value for name, value in previous.items() if name not in grid}
    fixed["scale_pos_weight"] = balance_marker
    fixed["n_jobs"] = 1
    return fixed


def run_b_lr_tuning(
    bundle: DatasetBundle,
    *,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> StrategyTunedResult:
    """B의 26 Feature, 28개 LR Grid 및 비가중 OOF를 준비한다."""
    grid = step3_tuning_grids(model_config, strategy="B")["logistic_regression"]
    search = _search(
        bundle, model_name="logistic_regression", stage="lr", param_grid=grid,
        feature_config=feature_config, model_config=model_config,
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )
    return _finalize_standard(bundle, "B tuned", search, feature_config, model_config)


def run_c_lr_tuning(
    bundle: DatasetBundle,
    *,
    sample_weight_train: pd.Series,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> StrategyTunedResult:
    """C의 25 Feature, 14개 LR Grid 및 fold-aware weighted correction을 준비한다."""
    grid = step3_tuning_grids(model_config, strategy="C")["logistic_regression"]
    search = _search(
        bundle, model_name="logistic_regression", stage="lr", param_grid=grid,
        feature_config=feature_config, model_config=model_config,
        fixed_params={"class_weight": WEIGHTED_CLASS_BALANCED},
        sample_weight_train=sample_weight_train,
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )
    return _finalize_weighted(bundle, "C revised tuned", search, sample_weight_train, feature_config, model_config)


def run_xgb_tuning_stage_a(
    bundle: DatasetBundle,
    *,
    strategy: str,
    stage35_params: dict,
    sample_weight_train: pd.Series | None,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> StrategySearchResult:
    """XGB Phase A를 B raw-count 또는 C weighted-mass correction으로 준비한다."""
    grid = step3_tuning_grids(model_config, strategy=strategy)["xgboost"]["stage_a"]
    marker = TRAIN_NEGATIVE_POSITIVE_RATIO if strategy == "B" else TRAIN_WEIGHTED_NEGATIVE_POSITIVE_RATIO
    return _search(
        bundle, model_name="xgboost", stage="xgb_stage_a", param_grid=grid,
        feature_config=feature_config, model_config=model_config,
        fixed_params=_xgb_fixed_params(stage35_params, grid, balance_marker=marker),
        sample_weight_train=sample_weight_train,
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )


def run_xgb_tuning_stage_b(
    bundle: DatasetBundle,
    *,
    strategy: str,
    stage_a_params: dict,
    sample_weight_train: pd.Series | None,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> StrategySearchResult:
    """XGB Phase B를 직전 Phase A best에서 이어서 준비한다."""
    grid = step3_tuning_grids(model_config, strategy=strategy)["xgboost"]["stage_b"]
    marker = TRAIN_NEGATIVE_POSITIVE_RATIO if strategy == "B" else TRAIN_WEIGHTED_NEGATIVE_POSITIVE_RATIO
    return _search(
        bundle, model_name="xgboost", stage="xgb_stage_b", param_grid=grid,
        feature_config=feature_config, model_config=model_config,
        fixed_params=_xgb_fixed_params(stage_a_params, grid, balance_marker=marker),
        sample_weight_train=sample_weight_train,
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )


def run_xgb_tuning_stage_c(
    bundle: DatasetBundle,
    *,
    strategy: str,
    stage_b_params: dict,
    sample_weight_train: pd.Series | None,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> StrategyTunedResult:
    """XGB Phase C 후 strategy에 맞는 최종 비가중 OOF를 준비한다."""
    grid = step3_tuning_grids(model_config, strategy=strategy)["xgboost"]["stage_c"]
    marker = TRAIN_NEGATIVE_POSITIVE_RATIO if strategy == "B" else TRAIN_WEIGHTED_NEGATIVE_POSITIVE_RATIO
    search = _search(
        bundle, model_name="xgboost", stage="xgb_stage_c", param_grid=grid,
        feature_config=feature_config, model_config=model_config,
        fixed_params=_xgb_fixed_params(stage_b_params, grid, balance_marker=marker),
        sample_weight_train=sample_weight_train,
        parallel_backend_name=parallel_backend_name, n_jobs=n_jobs,
    )
    if strategy == "B":
        return _finalize_standard(bundle, "B tuned", search, feature_config, model_config)
    return _finalize_weighted(bundle, "C revised tuned", search, sample_weight_train, feature_config, model_config)


def _finalize_standard(
    bundle: DatasetBundle, strategy: str, search: StrategySearchResult,
    feature_config: str | Path | dict, model_config: str | Path | dict,
) -> StrategyTunedResult:
    oof = generate_oof_predictions(
        bundle.X, bundle.y, bundle.groups, model_name=search.model,
        feature_config=feature_config, model_config=model_config, params=search.best_params,
    )
    return StrategyTunedResult(
        strategy, search, calculate_binary_metrics(oof["y_true"], oof["y_probability"]), oof
    )


def _finalize_weighted(
    bundle: DatasetBundle, strategy: str, search: StrategySearchResult, sample_weight_train: pd.Series,
    feature_config: str | Path | dict, model_config: str | Path | dict,
) -> StrategyTunedResult:
    locked, audit = run_weighted_class_locked_oof(
        bundle, model_name=search.model, locked_params=search.best_params,
        feature_config=feature_config, model_config=model_config, sample_weight_train=sample_weight_train,
    )
    return StrategyTunedResult(strategy, search, locked.metrics, locked.oof_predictions, audit)


def save_strategy_tuning_artifacts(
    *,
    output_dir: str | Path,
    bundle: DatasetBundle,
    tuned_results: list[StrategyTunedResult],
    lr_search: StrategySearchResult,
    xgb_stage_a: StrategySearchResult,
    xgb_stage_b: StrategySearchResult,
    xgb_stage_c: StrategySearchResult,
) -> dict[str, Path]:
    """Step 3 strategy 전용 결과만 저장한다. 기존 locked/A artifact는 바꾸지 않는다."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for result in tuned_results:
        row = result.summary_row()
        row["feature_count"] = bundle.X.shape[1]
        rows.append(row)
    paths = {"summary": destination / "tuning_summary.csv"}
    pd.DataFrame(rows).to_csv(paths["summary"], index=False)
    paths["best_params"] = destination / "best_params.json"
    with paths["best_params"].open("w", encoding="utf-8") as file:
        json.dump(
            {
                "logistic_regression": tuned_results[0].search.best_params,
                "xgboost_stage_a": xgb_stage_a.best_params,
                "xgboost_stage_b": xgb_stage_b.best_params,
                "xgboost": tuned_results[1].search.best_params,
            },
            file, ensure_ascii=False, indent=2,
        )
    paths["fold_f1"] = destination / "fold_f1.json"
    with paths["fold_f1"].open("w", encoding="utf-8") as file:
        json.dump({result.search.model: list(result.search.fold_f1) for result in tuned_results}, file, ensure_ascii=False, indent=2)
    search_files = {
        "logistic_regression_search_results": (lr_search.cv_results, "logistic_regression_search_results.csv"),
        "xgboost_refinement_stage_a": (xgb_stage_a.cv_results, "xgboost_refinement_stage_a.csv"),
        "xgboost_refinement_stage_b": (xgb_stage_b.cv_results, "xgboost_refinement_stage_b.csv"),
        "xgboost_refinement_stage_c": (xgb_stage_c.cv_results, "xgboost_refinement_stage_c.csv"),
    }
    for name, (frame, filename) in search_files.items():
        paths[name] = destination / filename
        frame.to_csv(paths[name], index=False)
    confusion = {}
    for result in tuned_results:
        locked = LockedModelResult(
            result.strategy, result.search.model, bundle.X.shape[1], result.search.best_params,
            result.search.fold_f1, result.metrics, result.oof_predictions,
        )
        key = result.search.model
        paths[f"{key}_oof"] = destination / f"{key}_oof_predictions.parquet"
        create_locked_oof_artifact(locked, bundle).to_parquet(paths[f"{key}_oof"], index=False)
        confusion[key] = result.metrics["confusion_matrix"]
    paths["confusion_matrices"] = destination / "confusion_matrices.json"
    with paths["confusion_matrices"].open("w", encoding="utf-8") as file:
        json.dump(confusion, file, ensure_ascii=False, indent=2)
    audits = [result.audit.assign(model=result.search.model) for result in tuned_results if result.audit is not None]
    if audits:
        paths["weighted_class_audit"] = destination / "weighted_class_audit.csv"
        pd.concat(audits, ignore_index=True).to_csv(paths["weighted_class_audit"], index=False)
    return paths
