"""Person-Period에서 Global Model 입력 묶음을 만든다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from code.contracts import DatasetBundle
from code.preprocess.build_features import build_features, load_feature_config


def build_global_dataset(
    person_period: pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    strict_features: bool = True,
) -> DatasetBundle:
    """Global/Local 공통 Feature 목록을 사용해 전체 Person-Period 입력을 반환한다."""
    config = load_feature_config(feature_config)
    required = {"SAMPID", "baseline_year", "target_year", "employment_transition"}
    missing = sorted(required - set(person_period.columns))
    if missing:
        raise ValueError(f"Person-Period에 필수 컬럼이 없습니다: {', '.join(missing)}")
    X = build_features(person_period, config, strict=strict_features)
    metadata = person_period[["SAMPID", "baseline_year", "target_year"]].copy()
    return DatasetBundle(
        name="global",
        X=X,
        y=person_period["employment_transition"].astype("int8"),
        groups=person_period["SAMPID"].astype("string"),
        metadata=metadata,
    )
