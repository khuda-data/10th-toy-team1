"""설정된 Feature 계약을 DataFrame으로 검증·정렬한다."""

from __future__ import annotations

from pathlib import Path

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
        output[column] = pd.to_numeric(output[column], errors="coerce")
    for column in feature_columns_by_type(config, "categorical"):
        output[column] = output[column].astype("string")
    return output
