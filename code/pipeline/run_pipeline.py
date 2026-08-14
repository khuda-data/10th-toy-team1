"""원자료 → Person-Period → Global/Local → split → (선택) 모델·결과 저장 실행점."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from code.contracts import DatasetBundle
from code.evaluation.evaluate import evaluate_model
from code.evaluation.importance import calculate_feature_importance
from code.model.train import train_model
from code.model.tune import tune_model
from code.pipeline.build_global import build_global_dataset
from code.pipeline.build_local import build_local_dataset
from code.pipeline.build_person_period import build_person_period_dataset
from code.pipeline.source_adapter import extract_hope_job_history, load_yp2021_raw, standardize_annual_frames
from code.pipeline.split import build_split_ids, select_split

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "code" / "config"
RESULT = ROOT / "data" / "result"


def _paths() -> dict[str, Path]:
    return {
        "datasets": RESULT / "datasets",
        "splits": RESULT / "splits",
        "metrics": RESULT / "metrics",
        "importance": RESULT / "feature_importance",
        "models": RESULT / "models",
    }


def _prepare_result_directories() -> dict[str, Path]:
    paths = _paths()
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _save_bundle(bundle, path: Path) -> None:
    bundle.to_frame().to_parquet(path, index=False)


def _metric_row(
    dataset: str,
    job_group: str | None,
    model_name: str,
    bundle: DatasetBundle,
    metrics: dict,
    best_params: dict,
    *,
    comparison_status: str = "formal",
    delta_f1: float | None = None,
) -> dict:
    return {
        "dataset": dataset,
        "job_group": job_group,
        "model": model_name,
        "n_rows": len(bundle.y),
        "n_persons": bundle.groups.nunique(),
        "n_positive": int(bundle.y.sum()),
        "n_negative": int((1 - bundle.y).sum()),
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "roc_auc": metrics["roc_auc"],
        "delta_f1": delta_f1,
        "ci95_lower": None,
        "ci95_upper": None,
        "comparison_status": comparison_status,
        "best_params": json.dumps(best_params, ensure_ascii=False, sort_keys=True),
        "random_seed": 42,
    }


def _subset_bundle(bundle: DatasetBundle, mask: pd.Series) -> DatasetBundle:
    selected = mask.to_numpy()
    return DatasetBundle(
        name=bundle.name,
        X=bundle.X.loc[selected].reset_index(drop=True),
        y=bundle.y.loc[selected].reset_index(drop=True),
        groups=bundle.groups.loc[selected].reset_index(drop=True),
        metadata=bundle.metadata.loc[selected].reset_index(drop=True),
    )


def _local_status(bundle: DatasetBundle) -> str | None:
    """프로토콜의 Local 최소 표본 기준에 따라 formal/exploratory/제외를 구분한다."""
    n_rows, n_people = len(bundle.y), bundle.groups.nunique()
    n_positive, n_negative = int(bundle.y.sum()), int((1 - bundle.y).sum())
    if n_rows >= 150 and n_people >= 100 and n_positive >= 40 and n_negative >= 40:
        return "formal"
    if 100 <= n_rows <= 149 and n_positive >= 30 and n_negative >= 30:
        return "exploratory"
    return None


def _fit_model(bundle: DatasetBundle, *, tune: bool, model_name: str, feature_config: Path, model_config: Path):
    if tune:
        search = tune_model(
            bundle.X, bundle.y, bundle.groups,
            model_name=model_name, feature_config=feature_config, model_config=model_config,
        )
        return search.best_estimator_, search.best_params_
    fitted = train_model(
        bundle.X, bundle.y, bundle.groups,
        model_name=model_name, feature_config=feature_config, model_config=model_config,
    )
    return fitted, {}


def run(raw_zip: Path, *, run_modeling: bool, tune: bool, model_name: str) -> None:
    paths = _prepare_result_directories()
    feature_config = CONFIG / "features.yaml"
    model_config = CONFIG / "model_config.yaml"
    mapping = CONFIG / "keco_mapping.csv"

    raw_frames = load_yp2021_raw(raw_zip)
    annual = standardize_annual_frames(raw_frames)
    person_period = build_person_period_dataset(annual)
    person_period.to_parquet(paths["datasets"] / "person_period.parquet", index=False)

    # strict=False는 아직 담당 모듈이 구현하지 않은 이력형 Feature도 schema에 남기는 구조 검증 단계다.
    global_bundle = build_global_dataset(person_period, feature_config, strict_features=False)
    history = extract_hope_job_history(raw_frames)
    local_bundle = build_local_dataset(person_period, history, mapping, feature_config, strict_features=False)
    _save_bundle(global_bundle, paths["datasets"] / "global_dataset.parquet")
    _save_bundle(local_bundle, paths["datasets"] / "local_dataset.parquet")

    split_ids = build_split_ids(global_bundle.y, global_bundle.groups)
    split_ids.to_csv(paths["splits"] / "split_ids.csv", index=False)

    if not run_modeling:
        print("구조 산출물을 저장했습니다. 모든 Feature 매핑 완료 후 --run-modeling으로 공통 모델을 실행하세요.")
        return

    # 모델 단계에서는 누락 Feature를 금지한다. Global/Local이 임의의 부분 Feature로 학습되는 것을 방지한다.
    global_bundle = build_global_dataset(person_period, feature_config, strict_features=True)
    train_bundle = select_split(global_bundle, split_ids, "train")
    test_bundle = select_split(global_bundle, split_ids, "test")
    fitted, best_params = _fit_model(
        train_bundle, tune=tune, model_name=model_name, feature_config=feature_config, model_config=model_config
    )
    metrics, _ = evaluate_model(fitted, test_bundle.X, test_bundle.y)
    metric_rows = [_metric_row("global", None, model_name, test_bundle, metrics, best_params)]
    importance = calculate_feature_importance(fitted, test_bundle.X, test_bundle.y)
    importance.insert(0, "model", model_name)
    importance.insert(0, "job_group", None)
    importance.insert(0, "dataset", "global")
    importance_frames = [importance]
    parameter_runs = [{"dataset": "global", "job_group": None, "model": model_name, "best_params": best_params}]

    local_bundle = build_local_dataset(person_period, history, mapping, feature_config, strict_features=True)
    for job_group in sorted(local_bundle.metadata["job_group"].dropna().unique()):
        group_bundle = _subset_bundle(local_bundle, local_bundle.metadata["job_group"].eq(job_group))
        status = _local_status(group_bundle)
        if status is None:
            print(f"{job_group}: Local 최소 표본 기준 미달로 정식 비교에서 제외합니다.")
            continue
        local_train = select_split(group_bundle, split_ids, "train")
        local_test = select_split(group_bundle, split_ids, "test")
        global_metrics, _ = evaluate_model(fitted, local_test.X, local_test.y)
        local_fitted, local_params = _fit_model(
            local_train, tune=tune, model_name=model_name, feature_config=feature_config, model_config=model_config
        )
        local_metrics, _ = evaluate_model(local_fitted, local_test.X, local_test.y)
        metric_rows.append(
            _metric_row("global_on_local", job_group, model_name, local_test, global_metrics, best_params, comparison_status=status)
        )
        metric_rows.append(
            _metric_row(
                "local", job_group, model_name, local_test, local_metrics, local_params,
                comparison_status=status, delta_f1=local_metrics["f1"] - global_metrics["f1"],
            )
        )
        local_importance = calculate_feature_importance(local_fitted, local_test.X, local_test.y)
        local_importance.insert(0, "model", model_name)
        local_importance.insert(0, "job_group", job_group)
        local_importance.insert(0, "dataset", "local")
        importance_frames.append(local_importance)
        parameter_runs.append({"dataset": "local", "job_group": job_group, "model": model_name, "best_params": local_params})

    pd.DataFrame(metric_rows).to_csv(paths["metrics"] / "metrics.csv", index=False)
    pd.concat(importance_frames, ignore_index=True).to_csv(paths["importance"] / "feature_importance.csv", index=False)
    (paths["models"] / "best_params.json").write_text(
        json.dumps({"runs": parameter_runs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-zip", required=True, type=Path, help="YP2021_EXCEL_*.zip 경로")
    parser.add_argument("--run-modeling", action="store_true", help="Feature 매핑이 완료됐을 때만 모델을 학습·평가")
    parser.add_argument("--tune", action="store_true", help="--run-modeling과 함께 공통 CV 튜닝을 실행")
    parser.add_argument("--model", default="logistic_regression", choices=["logistic_regression", "decision_tree", "random_forest", "xgboost", "lightgbm"])
    args = parser.parse_args()
    if args.tune and not args.run_modeling:
        parser.error("--tune은 --run-modeling과 함께 사용해야 합니다.")
    run(args.raw_zip, run_modeling=args.run_modeling, tune=args.tune, model_name=args.model)


if __name__ == "__main__":
    main()
