"""Global Stage 1의 Train 내부 LR·XGBoost 비교를 재사용 가능한 함수로 실행한다."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd

from code.contracts import DatasetBundle
from code.evaluation.evaluate import calculate_binary_metrics
from code.evaluation.oof import generate_oof_predictions
from code.model.train import load_model_config
from code.model.tune import tune_model


@dataclass(frozen=True)
class FirstStageModelResult:
    """한 모델의 Train 내부 탐색·OOF 결과 묶음. Test Dataset은 포함하지 않는다."""

    model: str
    n_features: int
    best_params: dict
    best_cv_f1: float
    fold_f1: tuple[float, ...]
    cv_f1_mean: float
    cv_f1_std: float
    oof_metrics: dict
    oof_predictions: pd.DataFrame

    def summary_row(self) -> dict:
        """Notebook 비교표에 바로 쓸 수 있는 한 행을 반환한다."""
        return {
            "model": self.model,
            "n_features": self.n_features,
            "best_cv_f1": self.best_cv_f1,
            "cv_f1_mean": self.cv_f1_mean,
            "cv_f1_std": self.cv_f1_std,
            "oof_precision": self.oof_metrics["precision"],
            "oof_recall": self.oof_metrics["recall"],
            "oof_f1": self.oof_metrics["f1"],
            "oof_roc_auc": self.oof_metrics["roc_auc"],
            "best_params": self.best_params,
        }


def run_global_cv_modeling(
    train_bundle: DatasetBundle,
    *,
    model_name: str,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> FirstStageModelResult:
    """선택된 Global Train Feature로 GridSearchCV와 고정 파라미터 OOF 예측을 실행한다.

    GridSearchCV가 SAMPID 그룹 5-fold F1로 파라미터를 고른 뒤, 같은 최적 파라미터를
    각 CV Train fold에서 새로 fit해 OOF 확률을 만든다. 이 함수는 Test Dataset을 받지 않아
    모델 선택에 Test를 사용할 수 없다.
    """
    config = load_model_config(model_config)
    official_models = config.get("official_comparison_models", [])
    if model_name not in official_models:
        raise ValueError(f"Global 공식 비교 모델이 아닙니다: {model_name}")
    search = tune_model(
        train_bundle.X,
        train_bundle.y,
        train_bundle.groups,
        model_name=model_name,
        feature_config=feature_config,
        model_config=config,
        sample_weight_train=None,
        parallel_backend_name=parallel_backend_name,
        n_jobs=n_jobs,
    )
    best_index = int(search.best_index_)
    fold_f1 = tuple(
        float(search.cv_results_[f"split{fold}_test_score"][best_index])
        for fold in range(config["split"]["cv_n_splits"])
    )
    best_params = {
        name.removeprefix("model__"): value
        for name, value in search.best_params_.items()
        if name.startswith("model__")
    }
    oof_predictions = generate_oof_predictions(
        train_bundle.X,
        train_bundle.y,
        train_bundle.groups,
        model_name=model_name,
        feature_config=feature_config,
        model_config=config,
        params=best_params,
        sample_weight_train=None,
    )
    threshold = config["tuning"]["threshold"]
    oof_metrics = calculate_binary_metrics(
        oof_predictions["y_true"], oof_predictions["y_probability"], threshold=threshold
    )
    return FirstStageModelResult(
        model=model_name,
        n_features=len(train_bundle.X.columns),
        best_params=best_params,
        best_cv_f1=float(search.best_score_),
        fold_f1=fold_f1,
        cv_f1_mean=float(search.cv_results_["mean_test_score"][best_index]),
        cv_f1_std=float(search.cv_results_["std_test_score"][best_index]),
        oof_metrics=oof_metrics,
        oof_predictions=oof_predictions,
    )


def run_first_stage_modeling(
    train_bundle: DatasetBundle,
    *,
    model_name: str,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    parallel_backend_name: str | None = None,
    n_jobs: int = -1,
) -> FirstStageModelResult:
    """Stage 1의 기본 42개 Feature 조건을 검증한 뒤 공통 Global CV 함수를 호출한다."""
    if len(train_bundle.X.columns) != 42:
        raise ValueError("Global Stage 1은 optional Feature 없이 42개 Feature만 사용합니다.")
    return run_global_cv_modeling(
        train_bundle,
        model_name=model_name,
        feature_config=feature_config,
        model_config=model_config,
        parallel_backend_name=parallel_backend_name,
        n_jobs=n_jobs,
    )


def save_first_stage_oof_predictions(result: FirstStageModelResult, output_dir: str | Path) -> Path:
    """이후 Feature 분석에 재사용할 Train OOF 확률을 모델별 parquet으로 보관한다."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{result.model}_oof_predictions.parquet"
    result.oof_predictions.to_parquet(path, index=False)
    return path


def save_modeling_artifacts(
    results: list[FirstStageModelResult],
    output_dir: str | Path,
    *,
    summary_filename: str = "modeling_summary.csv",
) -> dict[str, Path]:
    """단계별 CV 결과의 OOF·요약·파라미터·fold F1을 재사용 가능 파일로 저장한다."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for result in results:
        paths[f"{result.model}_oof"] = save_first_stage_oof_predictions(result, destination)
    summary_path = destination / summary_filename
    first_stage_summary(results).to_csv(summary_path, index=False)
    paths["summary"] = summary_path
    params_path = destination / "best_params.json"
    with params_path.open("w", encoding="utf-8") as file:
        json.dump({result.model: result.best_params for result in results}, file, ensure_ascii=False, indent=2)
    paths["best_params"] = params_path
    fold_path = destination / "fold_f1.json"
    with fold_path.open("w", encoding="utf-8") as file:
        json.dump({result.model: list(result.fold_f1) for result in results}, file, ensure_ascii=False, indent=2)
    paths["fold_f1"] = fold_path
    return paths


def save_first_stage_artifacts(results: list[FirstStageModelResult], output_dir: str | Path) -> dict[str, Path]:
    """Stage 2가 GridSearch를 다시 하지 않도록 Stage 1 결과를 표준 파일명으로 저장한다."""
    return save_modeling_artifacts(results, output_dir, summary_filename="first_stage_summary.csv")


def load_first_stage_best_params(output_dir: str | Path) -> dict[str, dict]:
    """Stage 1에서 저장한 최적 파라미터를 Stage 2용으로 복원한다."""
    path = Path(output_dir) / "best_params.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Stage 1 최적 파라미터 파일이 없습니다: {path}. "
            "01_first_model.ipynb의 Stage 1 결과 저장 셀을 먼저 실행하세요."
        )
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_stage_fold_f1(output_dir: str | Path) -> dict[str, tuple[float, ...]]:
    """저장된 단계별 fold F1을 비교용으로 복원한다."""
    path = Path(output_dir) / "fold_f1.json"
    if not path.exists():
        raise FileNotFoundError(
            f"저장된 fold F1 파일이 없습니다: {path}. "
            "01_first_model.ipynb의 Stage 1 결과 저장 셀을 다시 실행하세요."
        )
    with path.open(encoding="utf-8") as file:
        return {model: tuple(float(value) for value in values) for model, values in json.load(file).items()}


def first_stage_summary(results: list[FirstStageModelResult]) -> pd.DataFrame:
    """모델별 비교표에 필요한 고정 열을 반환한다."""
    columns = [
        "model", "n_features", "best_cv_f1", "cv_f1_mean", "cv_f1_std", "oof_precision", "oof_recall",
        "oof_f1", "oof_roc_auc", "best_params",
    ]
    return pd.DataFrame([result.summary_row() for result in results], columns=columns)
