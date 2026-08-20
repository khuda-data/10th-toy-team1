"""설정된 Feature 계약을 DataFrame으로 검증·정렬한다."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_feature_config(feature_config: str | Path | dict) -> dict:
    if isinstance(feature_config, dict):
        return feature_config
    with Path(feature_config).open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def _feature_items(feature_config: dict, *, extra_features: Iterable[str] | None = None) -> list[dict]:
    """기본 Feature 목록 + 명시적으로 요청한 optional_features만 덧붙인다.

    extra_features를 안 주면(기본값) 예전 42개짜리 결과와 완전히 동일하다 — n_prior_periods
    등 실험용 선택 Feature가 features:에 없어야만 이 재현성이 보장된다(2026-08-18).
    """
    items = list(feature_config["features"])
    if not extra_features:
        return items
    optional_by_name = {item["name"]: item for item in feature_config.get("optional_features", [])}
    for name in extra_features:
        if name not in optional_by_name:
            raise KeyError(f"optional_features에 정의되지 않은 Feature입니다: {name}")
        items.append(optional_by_name[name])
    return items


def feature_columns(feature_config: dict, *, extra_features: Iterable[str] | None = None) -> list[str]:
    return [item["name"] for item in _feature_items(feature_config, extra_features=extra_features)]


def feature_columns_by_type(
    feature_config: dict, feature_type: str, *, extra_features: Iterable[str] | None = None
) -> list[str]:
    return [
        item["name"]
        for item in _feature_items(feature_config, extra_features=extra_features)
        if item["type"] == feature_type
    ]


def named_feature_set(feature_config: str | Path | dict, feature_set_name: str) -> list[str]:
    """설정에 등록한 사람이 확정한 원 Feature 집합을 순서대로 반환한다."""
    config = load_feature_config(feature_config)
    feature_sets = config.get("feature_sets", {})
    if feature_set_name not in feature_sets:
        raise KeyError(f"features.yaml에 등록되지 않은 Feature set입니다: {feature_set_name}")
    selected = list(feature_sets[feature_set_name])
    all_features = set(feature_columns(config))
    unknown = [feature for feature in selected if feature not in all_features]
    duplicate = [feature for feature in selected if selected.count(feature) > 1]
    if unknown:
        raise ValueError(f"Feature set에 기본 42개 Feature가 아닌 이름이 있습니다: {', '.join(unknown)}")
    if duplicate:
        raise ValueError(f"Feature set에 중복된 Feature가 있습니다: {', '.join(sorted(set(duplicate)))}")
    return selected


def build_features(
    frame: pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    strict: bool = True,
    extra_features: Iterable[str] | None = None,
) -> pd.DataFrame:
    """모든 모델이 같은 순서·타입의 원 Feature DataFrame을 받게 한다.

    strict=True는 원자료 Feature 매핑이 빠진 상태로 모델을 돌려 결측을 임의 처리하는 일을 막는다.
    strict=False는 Person-Period/Local/split 산출물의 구조 확인용으로만 사용한다.
    extra_features는 `optional_features:`에 등록된 이름만 받아 X에 추가로 포함시킨다
    (예: ["n_prior_periods"]) — 기본값(None)은 기존 42개 Feature와 완전히 동일하다.
    """
    config = load_feature_config(feature_config)
    columns = feature_columns(config, extra_features=extra_features)
    missing = [column for column in columns if column not in frame.columns]
    if missing and strict:
        raise ValueError(
            "Feature 생성이 아직 완성되지 않았습니다. 코드북 대조 후 source adapter 또는 feature builder에 "
            f"다음 표준 컬럼을 추가하세요: {', '.join(missing)}"
        )
    output = frame.reindex(columns=columns).copy()
    for column in feature_columns_by_type(config, "numeric", extra_features=extra_features):
        # nullable Int64/Float64를 그대로 두면 scikit-learn(SimpleImputer 등)이 pd.NA를 numpy
        # object 배열로 받아 "boolean value of NA is ambiguous"로 죽는다(2026-08-16 확인).
        # float64로 바꾸면 pd.NA가 np.nan으로 자동 변환돼 scikit-learn이 정상적으로 결측을 인식한다.
        output[column] = pd.to_numeric(output[column], errors="coerce").astype("float64")
    for column in feature_columns_by_type(config, "categorical", extra_features=extra_features):
        # string dtype의 결측 마커도 pd.NA라 같은 문제가 난다. object로 바꾼 뒤 pd.NA를
        # np.nan으로 명시적으로 치환해야 scikit-learn이 인식하는 결측 표기와 맞는다.
        series = output[column].astype("string").astype(object)
        output[column] = series.where(series.notna(), np.nan)
    return output
