"""설정된 Feature 계약을 DataFrame으로 검증·정렬한다."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_feature_config(feature_config: str | Path | dict) -> dict:
    if isinstance(feature_config, dict):
        return feature_config
    with Path(feature_config).open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def feature_columns(feature_config: dict) -> list[str]:
    return [item["name"] for item in feature_config["features"]]


def feature_columns_by_type(feature_config: dict, feature_type: str) -> list[str]:
    return [item["name"] for item in feature_config["features"] if item["type"] == feature_type]


def build_features(
    frame: pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    strict: bool = True,
) -> pd.DataFrame:
    """모든 모델이 같은 순서·타입의 원 Feature DataFrame을 받게 한다.

    strict=True는 원자료 Feature 매핑이 빠진 상태로 모델을 돌려 결측을 임의 처리하는 일을 막는다.
    strict=False는 Person-Period/Local/split 산출물의 구조 확인용으로만 사용한다.
    """
    config = load_feature_config(feature_config)
    columns = feature_columns(config)
    missing = [column for column in columns if column not in frame.columns]
    if missing and strict:
        raise ValueError(
            "Feature 생성이 아직 완성되지 않았습니다. 코드북 대조 후 source adapter 또는 feature builder에 "
            f"다음 표준 컬럼을 추가하세요: {', '.join(missing)}"
        )
    output = frame.reindex(columns=columns).copy()
    for column in feature_columns_by_type(config, "numeric"):
        # nullable Int64/Float64를 그대로 두면 scikit-learn(SimpleImputer 등)이 pd.NA를 numpy
        # object 배열로 받아 "boolean value of NA is ambiguous"로 죽는다(2026-08-16 확인).
        # float64로 바꾸면 pd.NA가 np.nan으로 자동 변환돼 scikit-learn이 정상적으로 결측을 인식한다.
        output[column] = pd.to_numeric(output[column], errors="coerce").astype("float64")
    for column in feature_columns_by_type(config, "categorical"):
        # string dtype의 결측 마커도 pd.NA라 같은 문제가 난다. object로 바꾼 뒤 pd.NA를
        # np.nan으로 명시적으로 치환해야 scikit-learn이 인식하는 결측 표기와 맞는다.
        series = output[column].astype("string").astype(object)
        output[column] = series.where(series.notna(), np.nan)
    return output
