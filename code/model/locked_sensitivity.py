"""동결된 Global Stage 3.5 파라미터로 반복관측 sensitivity OOF를 만드는 공용 함수.

이 모듈은 하이퍼파라미터 탐색·Test 접근을 하지 않는다. 저장된 Stage 3.5 파라미터를
각 Train CV fold의 fit에 그대로 전달하고, 평가는 항상 비가중 OOF 지표로 계산한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.metrics import f1_score

from code.contracts import DatasetBundle
from code.evaluation.evaluate import calculate_binary_metrics
from code.evaluation.oof import generate_oof_predictions


@dataclass(frozen=True)
class LockedModelResult:
    """동결 파라미터 한 모델의 Train OOF 결과."""

    strategy: str
    model: str
    feature_count: int
    params: dict
    fold_f1: tuple[float, ...]
    metrics: dict
    oof_predictions: pd.DataFrame

    def summary_row(self) -> dict:
        return {
            "strategy": self.strategy,
            "model": self.model,
            "feature_count": self.feature_count,
            "cv_f1_mean": sum(self.fold_f1) / len(self.fold_f1),
            "cv_f1_std": pd.Series(self.fold_f1).std(ddof=0),
            "oof_accuracy": self.metrics["accuracy"],
            "oof_precision": self.metrics["precision"],
            "oof_recall": self.metrics["recall"],
            "oof_f1": self.metrics["f1"],
            "oof_roc_auc": self.metrics["roc_auc"],
            "oof_average_precision": self.metrics["average_precision"],
        }


def load_stage_3_5_locked_params(path: str | Path) -> dict[str, dict]:
    """공식 A의 Stage 3.5 최종 LR/XGBoost 파라미터만 읽는다."""
    with Path(path).open(encoding="utf-8") as file:
        saved = json.load(file)
    required = {"logistic_regression", "xgboost"}
    missing = sorted(required - set(saved))
    if missing:
        raise ValueError(f"Stage 3.5 파라미터 파일에 없는 모델이 있습니다: {', '.join(missing)}")
    return {name: dict(saved[name]) for name in required}


def run_locked_model_oof(
    bundle: DatasetBundle,
    *,
    strategy: str,
    model_name: str,
    locked_params: dict,
    feature_config: str | Path | dict,
    model_config: str | Path | dict,
    sample_weight_train: pd.Series | None = None,
) -> LockedModelResult:
    """탐색 없이 동결 파라미터로 5-fold Group OOF를 생성한다.

    `sample_weight_train`은 각 fold의 fit 행에만 전달된다. 반환 metrics와 fold F1은
    sample weight를 사용하지 않는 일반적인 행 단위 OOF 평가다.
    """
    oof = generate_oof_predictions(
        bundle.X,
        bundle.y,
        bundle.groups,
        model_name=model_name,
        feature_config=feature_config,
        model_config=model_config,
        params=locked_params,
        sample_weight_train=sample_weight_train,
    )
    threshold = 0.5
    fold_f1 = tuple(
        f1_score(part["y_true"], part["y_predicted"], zero_division=0)
        for _, part in oof.groupby("fold", sort=True)
    )
    metrics = calculate_binary_metrics(oof["y_true"], oof["y_probability"], threshold=threshold)
    return LockedModelResult(
        strategy=strategy,
        model=model_name,
        feature_count=bundle.X.shape[1],
        params=dict(locked_params),
        fold_f1=fold_f1,
        metrics=metrics,
        oof_predictions=oof,
    )


def create_locked_oof_artifact(result: LockedModelResult, bundle: DatasetBundle) -> pd.DataFrame:
    """요청한 sensitivity OOF 저장 계약으로 변환한다."""
    if "baseline_year" not in bundle.metadata:
        raise ValueError("OOF 저장에는 baseline_year metadata가 필요합니다.")
    oof = result.oof_predictions.reset_index(drop=True)
    baseline_year = bundle.metadata["baseline_year"].reset_index(drop=True)
    if len(oof) != len(baseline_year):
        raise ValueError("OOF와 Train metadata 행 수가 다릅니다.")
    return pd.DataFrame(
        {
            "SAMPID": oof["SAMPID"].astype("string"),
            "baseline_year": baseline_year,
            "y_true": oof["y_true"].astype("int8"),
            "y_proba": oof["y_probability"],
            "y_pred": oof["y_predicted"].astype("int8"),
            "fold": oof["fold"].astype("int16"),
        }
    )


def save_locked_model_artifacts(
    results: list[LockedModelResult], bundle: DatasetBundle, output_dir: str | Path
) -> dict[str, Path]:
    """Sensitivity 전용 결과를 저장하며 A 공식 artifact는 변경하지 않는다."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "locked_model_summary.csv"
    pd.DataFrame([result.summary_row() for result in results]).to_csv(summary_path, index=False)
    fold_path = destination / "locked_fold_f1.json"
    with fold_path.open("w", encoding="utf-8") as file:
        json.dump({result.model: list(result.fold_f1) for result in results}, file, ensure_ascii=False, indent=2)
    paths = {"summary": summary_path, "fold_f1": fold_path}
    for result in results:
        path = destination / f"locked_{result.model}_oof_predictions.parquet"
        create_locked_oof_artifact(result, bundle).to_parquet(path, index=False)
        paths[f"{result.model}_oof"] = path
    return paths


def load_baseline_stage_3_5_summary(path: str | Path) -> pd.DataFrame:
    """A 공식 Stage 3.5 summary를 sensitivity 비교 열로 표준화한다."""
    frame = pd.read_csv(path)
    required = {"model", "stage", "feature_count", "cv_f1_mean", "cv_f1_std", "oof_precision", "oof_recall", "oof_f1", "oof_roc_auc"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"A Stage 3.5 summary에 필요한 컬럼이 없습니다: {', '.join(missing)}")
    baseline = frame.loc[frame["stage"].eq("stage_3_5")].copy()
    if set(baseline["model"]) != {"logistic_regression", "xgboost"}:
        raise ValueError("A Stage 3.5 summary에는 LR·XGBoost가 각각 하나씩 있어야 합니다.")
    baseline.insert(0, "strategy", "A Baseline")
    return baseline.loc[:, [
        "strategy", "model", "feature_count", "cv_f1_mean", "cv_f1_std", "oof_precision", "oof_recall", "oof_f1", "oof_roc_auc"
    ]]


def sensitivity_comparison_table(baseline: pd.DataFrame, results: list[LockedModelResult]) -> pd.DataFrame:
    """A와 한 sensitivity 전략의 비교표를 요청된 열 순서로 만든다."""
    strategy = pd.DataFrame([result.summary_row() for result in results]).loc[:, [
        "strategy", "model", "feature_count", "cv_f1_mean", "cv_f1_std", "oof_precision", "oof_recall", "oof_f1", "oof_roc_auc"
    ]]
    return pd.concat([baseline, strategy], ignore_index=True).sort_values(["model", "strategy"]).reset_index(drop=True)
