"""저장된 Global 산출물을 읽어 감사용 Train DataFrame을 준비하는 보조 함수.

이 모듈은 모델을 학습하거나 split을 새로 만들지 않는다. Sensitivity audit Notebook이
기존 Global split과 Stage 3의 선택 Feature를 같은 방식으로 읽도록 공통 처리만 둔다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from code.pipeline.saved_results import load_saved_global_train


_ROW_KEY = ["SAMPID", "baseline_year", "target_year"]
_REQUIRED_DATASET_COLUMNS = set(_ROW_KEY + ["employment_transition"])


def load_saved_global_train_frame(
    dataset_path: str | Path, split_path: str | Path, feature_config: str | Path | dict | None = None
) -> pd.DataFrame:
    """기존 saved-results 유틸리티로 Global Train 행만 DataFrame으로 복원한다.

    `load_saved_global_train()`을 재사용하므로 고정 split 파일만 적용하고, Test
    DatasetBundle이나 새 split은 만들지 않는다.
    """
    config = feature_config or Path(__file__).resolve().parents[2] / "code" / "config" / "features.yaml"
    train_bundle = load_saved_global_train(dataset_path, split_path, config)
    frame = train_bundle.to_frame()
    missing_dataset = sorted(_REQUIRED_DATASET_COLUMNS - set(frame.columns))
    if missing_dataset:
        raise ValueError(f"저장된 Global Train에 필수 컬럼이 없습니다: {', '.join(missing_dataset)}")
    return frame.reset_index(drop=True)


def load_selected_feature_names(selected_features_path: str | Path) -> list[str]:
    """Stage 3가 저장한 선택 Feature의 순서를 그대로 읽는다."""
    selected = pd.read_csv(selected_features_path)
    if "feature" not in selected.columns:
        raise ValueError("selected_features.csv에는 feature 컬럼이 필요합니다.")
    names = selected["feature"].tolist()
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("selected_features.csv의 feature 값은 비어 있지 않은 문자열이어야 합니다.")
    if len(names) != len(set(names)):
        raise ValueError("selected_features.csv에 중복 Feature가 있습니다.")
    return names


def attach_person_period_column(
    train_frame: pd.DataFrame, person_period_path: str | Path, column: str
) -> pd.DataFrame:
    """Person-Period 원본의 한 컬럼을 같은 행 키로 Train frame에 안전하게 붙인다.

    예를 들어 `n_prior_periods`는 person-period 생성 단계에서 계산된 값을 재사용한다.
    이 함수는 해당 값을 다시 계산하거나 변경하지 않는다.
    """
    if column in train_frame.columns:
        return train_frame.copy()
    person_period = pd.read_parquet(person_period_path)
    required = set(_ROW_KEY + [column])
    missing = sorted(required - set(person_period.columns))
    if missing:
        raise ValueError(f"person_period.parquet에 필요한 컬럼이 없습니다: {', '.join(missing)}")
    if train_frame.duplicated(_ROW_KEY).any() or person_period.duplicated(_ROW_KEY).any():
        raise ValueError("SAMPID·baseline_year·target_year 행 키는 각 입력에서 유일해야 합니다.")

    left = train_frame.copy()
    right = person_period.loc[:, _ROW_KEY + [column]].copy()
    left["SAMPID"] = left["SAMPID"].astype("string")
    right["SAMPID"] = right["SAMPID"].astype("string")
    merged = left.merge(right, on=_ROW_KEY, how="left", validate="one_to_one")
    if merged[column].isna().any():
        raise ValueError(f"Train 행 일부에 person_period의 {column} 값을 연결하지 못했습니다.")
    return merged


def calculate_train_sample_weight(groups: pd.Series) -> pd.Series:
    """Global Train 안의 SAMPID별 행 수 역수(1 / n_i)를 반환한다.

    이 값은 audit 및 모델 fit 입력용이다. metric·OOF 점수 계산에는 사용하지 않는다.
    """
    normalized_groups = groups.astype("string")
    if normalized_groups.isna().any():
        raise ValueError("sample_weight 계산을 위한 SAMPID에 결측이 있습니다.")
    row_count = normalized_groups.groupby(normalized_groups, sort=False).transform("size")
    return (1.0 / row_count).astype("float64").rename("sample_weight")
