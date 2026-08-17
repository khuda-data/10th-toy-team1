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
    # 오버샘플링 완화용 가중치: 이 데이터셋(Global) 안에서 그 사람이 차지하는 행 수의 역수.
    # 사람당 총 가중치 합이 1이 되게 해, 반복 관측이 많은 소수 인원이 loss를 과점하지 않게 한다.
    sample_weight = 1.0 / person_period.groupby("SAMPID")["SAMPID"].transform("size")
    return DatasetBundle(
        name="global",
        X=X,
        y=person_period["employment_transition"].astype("int8"),
        groups=person_period["SAMPID"].astype("string"),
        metadata=metadata,
        sample_weight=sample_weight.astype("float64").reset_index(drop=True),
    )
