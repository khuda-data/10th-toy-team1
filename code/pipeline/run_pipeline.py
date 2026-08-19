"""원자료 → Person-Period → Global/Local → split → (선택) 모델·결과 저장 실행점."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    # Windows 콘솔 기본 코드페이지(cp949)는 이 스크립트가 출력하는 일부 문자(예: em dash)를
    # 인코딩하지 못해 UnicodeEncodeError로 죽는다. 실제 산출물 저장은 이미 끝난 뒤 마지막
    # 안내 print()에서만 죽는 경우라도 스크립트가 실패한 것처럼 보이므로 UTF-8로 고정한다.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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


def experiment_name(*, use_n_prior_periods: bool, use_sample_weight: bool) -> str:
    """오버샘플링 완화 실험 세 가지(2026-08-18, wjdwlsah 지시)를 구분하는 이름.

    n_prior_periods(Feature 포함 여부)와 sample_weight(학습 가중치 반영 여부)는 서로 독립적으로
    켜고 끌 수 있어야 ①Baseline(42개 Feature) ②+n_prior_periods(43개) ③+sample_weight를
    다른 조건은 전부 동일하게 두고 비교할 수 있다. 결과 파일 경로·metrics·모델 산출물이 전부
    이 이름으로 분리되므로, 세 실험은 항상 독립적인 산출물을 만든다.
    """
    if not use_n_prior_periods and not use_sample_weight:
        return "baseline_42features"
    if use_n_prior_periods and not use_sample_weight:
        return "with_n_prior_periods"
    if use_sample_weight and not use_n_prior_periods:
        return "with_sample_weight"
    return "with_n_prior_periods_and_sample_weight"


def _paths(name: str) -> dict[str, Path]:
    base = RESULT / name
    return {
        "datasets": base / "datasets",
        "splits": base / "splits",
        "metrics": base / "metrics",
        "importance": base / "feature_importance",
        "models": base / "models",
    }


def _prepare_result_directories(name: str) -> dict[str, Path]:
    paths = _paths(name)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _save_bundle(bundle, path: Path) -> None:
    bundle.to_frame().to_parquet(path, index=False)


def _metric_row(
    experiment: str,
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
        "experiment": experiment,
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
    groups = bundle.groups.loc[selected].reset_index(drop=True)
    # 직군별 부분집합이 실제 학습 단위이므로, 가중치도 Local 전체가 아니라 이 부분집합
    # 안에서의 행 수 기준으로 다시 계산한다(build_local_dataset과 같은 이유). 이 계산 자체는
    # use_sample_weight와 무관하게 항상 해 둔다 — 실제로 학습에 쓸지는 _fit_model이 결정한다.
    sample_weight = 1.0 / groups.groupby(groups).transform("size")
    return DatasetBundle(
        name=bundle.name,
        X=bundle.X.loc[selected].reset_index(drop=True),
        y=bundle.y.loc[selected].reset_index(drop=True),
        groups=groups,
        metadata=bundle.metadata.loc[selected].reset_index(drop=True),
        sample_weight=sample_weight.astype("float64"),
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


def _fit_model(
    bundle: DatasetBundle,
    *,
    tune: bool,
    model_name: str,
    feature_config: Path,
    model_config: Path,
    use_sample_weight: bool = False,
):
    """sample_weight는 use_sample_weight=True일 때만 학습(fit)에 반영한다(기본: 미반영).

    DatasetBundle.sample_weight 자체는 (use_sample_weight와 무관하게) 항상 계산돼 있으므로,
    여기서 켜고 끄는 것만으로 "①Baseline ③+sample_weight" 두 실험을 다른 코드 변경 없이 비교할 수 있다.
    """
    sample_weight_train = bundle.sample_weight if use_sample_weight else None
    if tune:
        search = tune_model(
            bundle.X, bundle.y, bundle.groups,
            model_name=model_name, feature_config=feature_config, model_config=model_config,
            sample_weight_train=sample_weight_train,
        )
        return search.best_estimator_, search.best_params_
    fitted = train_model(
        bundle.X, bundle.y, bundle.groups,
        model_name=model_name, feature_config=feature_config, model_config=model_config,
        sample_weight_train=sample_weight_train,
    )
    return fitted, {}


def _load_person_period(raw_zip: Path) -> tuple[dict[int, pd.DataFrame], pd.DataFrame]:
    """raw zip을 한 번만 읽어 hope_job_history 계산에 필요한 raw_frames와 person_period를 만든다.

    n_prior_periods는 person_period 단계에서 이미 계산돼 있고(PR#4 major_group 백필과도 무관),
    use_n_prior_periods/use_sample_weight 어느 조합이든 이 person_period 자체는 완전히 동일하다
    — 그래서 raw 로딩(가장 오래 걸리는 단계)은 실험 조합 수와 무관하게 한 번만 하면 된다.
    """
    raw_frames = load_yp2021_raw(raw_zip)
    annual = standardize_annual_frames(raw_frames)
    person_period = build_person_period_dataset(annual)
    return raw_frames, person_period


def run_experiment(
    raw_frames: dict[int, pd.DataFrame],
    person_period: pd.DataFrame,
    *,
    run_modeling: bool,
    tune: bool,
    model_name: str,
    use_n_prior_periods: bool,
    use_sample_weight: bool,
) -> None:
    """세 오버샘플링 완화 실험 중 하나를 끝까지 돌려 experiment_name() 하위에 독립 저장한다."""
    name = experiment_name(use_n_prior_periods=use_n_prior_periods, use_sample_weight=use_sample_weight)
    paths = _prepare_result_directories(name)
    feature_config = CONFIG / "features.yaml"
    model_config = CONFIG / "model_config.yaml"
    mapping = CONFIG / "keco_mapping.csv"

    person_period.to_parquet(paths["datasets"] / "person_period.parquet", index=False)

    # strict=False는 아직 담당 모듈이 구현하지 않은 이력형 Feature도 schema에 남기는 구조 검증 단계다.
    global_bundle = build_global_dataset(
        person_period, feature_config, strict_features=False, use_n_prior_periods=use_n_prior_periods
    )
    history = extract_hope_job_history(raw_frames)
    local_bundle = build_local_dataset(
        person_period, history, mapping, feature_config, strict_features=False, use_n_prior_periods=use_n_prior_periods
    )
    _save_bundle(global_bundle, paths["datasets"] / "global_dataset.parquet")
    _save_bundle(local_bundle, paths["datasets"] / "local_dataset.parquet")

    split_ids = build_split_ids(global_bundle.y, global_bundle.groups)
    split_ids.to_csv(paths["splits"] / "split_ids.csv", index=False)

    if not run_modeling:
        print(f"[{name}] 구조 산출물을 저장했습니다. 모든 Feature 매핑 완료 후 --run-modeling으로 공통 모델을 실행하세요.")
        return

    # 모델 단계에서는 누락 Feature를 금지한다. Global/Local이 임의의 부분 Feature로 학습되는 것을 방지한다.
    global_bundle = build_global_dataset(
        person_period, feature_config, strict_features=True, use_n_prior_periods=use_n_prior_periods
    )
    train_bundle = select_split(global_bundle, split_ids, "train")
    test_bundle = select_split(global_bundle, split_ids, "test")
    fitted, best_params = _fit_model(
        train_bundle, tune=tune, model_name=model_name, feature_config=feature_config, model_config=model_config,
        use_sample_weight=use_sample_weight,
    )
    joblib.dump(fitted, paths["models"] / f"global_{model_name}.joblib")
    metrics, _ = evaluate_model(fitted, test_bundle.X, test_bundle.y)
    metric_rows = [_metric_row(name, "global", None, model_name, test_bundle, metrics, best_params)]
    importance = calculate_feature_importance(fitted, test_bundle.X, test_bundle.y)
    importance.insert(0, "model", model_name)
    importance.insert(0, "job_group", None)
    importance.insert(0, "dataset", "global")
    importance.insert(0, "experiment", name)
    importance_frames = [importance]
    parameter_runs = [{"experiment": name, "dataset": "global", "job_group": None, "model": model_name, "best_params": best_params}]

    local_bundle = build_local_dataset(
        person_period, history, mapping, feature_config, strict_features=True, use_n_prior_periods=use_n_prior_periods
    )
    for job_group in sorted(local_bundle.metadata["job_group"].dropna().unique()):
        group_bundle = _subset_bundle(local_bundle, local_bundle.metadata["job_group"].eq(job_group))
        status = _local_status(group_bundle)
        if status is None:
            print(f"[{name}] {job_group}: Local 최소 표본 기준 미달로 정식 비교에서 제외합니다.")
            continue
        local_train = select_split(group_bundle, split_ids, "train")
        local_test = select_split(group_bundle, split_ids, "test")
        global_metrics, _ = evaluate_model(fitted, local_test.X, local_test.y)
        local_fitted, local_params = _fit_model(
            local_train, tune=tune, model_name=model_name, feature_config=feature_config, model_config=model_config,
            use_sample_weight=use_sample_weight,
        )
        joblib.dump(local_fitted, paths["models"] / f"local_{job_group}_{model_name}.joblib")
        local_metrics, _ = evaluate_model(local_fitted, local_test.X, local_test.y)
        metric_rows.append(
            _metric_row(name, "global_on_local", job_group, model_name, local_test, global_metrics, best_params, comparison_status=status)
        )
        metric_rows.append(
            _metric_row(
                name, "local", job_group, model_name, local_test, local_metrics, local_params,
                comparison_status=status, delta_f1=local_metrics["f1"] - global_metrics["f1"],
            )
        )
        local_importance = calculate_feature_importance(local_fitted, local_test.X, local_test.y)
        local_importance.insert(0, "model", model_name)
        local_importance.insert(0, "job_group", job_group)
        local_importance.insert(0, "dataset", "local")
        local_importance.insert(0, "experiment", name)
        importance_frames.append(local_importance)
        parameter_runs.append({"experiment": name, "dataset": "local", "job_group": job_group, "model": model_name, "best_params": local_params})

    pd.DataFrame(metric_rows).to_csv(paths["metrics"] / "metrics.csv", index=False)
    pd.concat(importance_frames, ignore_index=True).to_csv(paths["importance"] / "feature_importance.csv", index=False)
    (paths["models"] / "best_params.json").write_text(
        json.dumps({"experiment": name, "runs": parameter_runs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[{name}] 완료 — {paths['metrics'] / 'metrics.csv'}")


def run(
    raw_zip: Path,
    *,
    run_modeling: bool,
    tune: bool,
    model_name: str,
    use_n_prior_periods: bool = False,
    use_sample_weight: bool = False,
    compare_oversampling_mitigation: bool = False,
) -> None:
    raw_frames, person_period = _load_person_period(raw_zip)
    if compare_oversampling_mitigation:
        # ①Baseline(42개) ②+n_prior_periods(43개) ③+sample_weight — 다른 조건은 전부 동일하게
        # 두고 이 세 조합만 바꿔 비교한다(2026-08-18, wjdwlsah 지시). raw 로딩·person_period는
        # 위에서 이미 한 번만 계산했으므로 여기서는 재사용만 한다.
        variants = [
            dict(use_n_prior_periods=False, use_sample_weight=False),
            dict(use_n_prior_periods=True, use_sample_weight=False),
            dict(use_n_prior_periods=False, use_sample_weight=True),
        ]
        for variant in variants:
            run_experiment(
                raw_frames, person_period, run_modeling=run_modeling, tune=tune, model_name=model_name, **variant
            )
        return
    run_experiment(
        raw_frames, person_period, run_modeling=run_modeling, tune=tune, model_name=model_name,
        use_n_prior_periods=use_n_prior_periods, use_sample_weight=use_sample_weight,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-zip", required=True, type=Path, help="YP2021_EXCEL_*.zip 경로")
    parser.add_argument("--run-modeling", action="store_true", help="Feature 매핑이 완료됐을 때만 모델을 학습·평가")
    parser.add_argument("--tune", action="store_true", help="--run-modeling과 함께 공통 CV 튜닝을 실행")
    parser.add_argument("--model", default="logistic_regression", choices=["logistic_regression", "decision_tree", "random_forest", "xgboost", "lightgbm"])
    parser.add_argument(
        "--use-n-prior-periods", action="store_true",
        help="n_prior_periods를 43번째 Feature로 X에 포함한다(기본: 미포함, 42개 Feature 그대로).",
    )
    parser.add_argument(
        "--use-sample-weight", action="store_true",
        help="학습(fit)에 sample_weight를 반영한다(기본: 미반영). 검증 fold 채점에는 항상 미반영.",
    )
    parser.add_argument(
        "--compare-oversampling-mitigation", action="store_true",
        help="raw 데이터를 한 번만 읽어 baseline/+n_prior_periods/+sample_weight 세 실험을 모두 실행한다. "
             "--use-n-prior-periods/--use-sample-weight와 함께 쓸 수 없다.",
    )
    args = parser.parse_args()
    if args.tune and not args.run_modeling:
        parser.error("--tune은 --run-modeling과 함께 사용해야 합니다.")
    if args.compare_oversampling_mitigation and (args.use_n_prior_periods or args.use_sample_weight):
        parser.error("--compare-oversampling-mitigation은 --use-n-prior-periods/--use-sample-weight와 함께 쓸 수 없습니다.")
    run(
        args.raw_zip, run_modeling=args.run_modeling, tune=args.tune, model_name=args.model,
        use_n_prior_periods=args.use_n_prior_periods, use_sample_weight=args.use_sample_weight,
        compare_oversampling_mitigation=args.compare_oversampling_mitigation,
    )


if __name__ == "__main__":
    main()
