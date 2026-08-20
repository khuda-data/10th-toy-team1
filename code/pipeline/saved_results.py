"""저장된 Global Dataset과 SAMPID split을 Notebook·분석 코드에서 다시 읽는 기능."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from code.contracts import DatasetBundle
from code.pipeline.split import select_split
from code.preprocess.build_features import build_features, load_feature_config


def load_saved_global_dataset(
    dataset_path: str | Path,
    feature_config: str | Path | dict,
) -> DatasetBundle:
    """`global_dataset.parquet`을 공통 `DatasetBundle`로 복원한다."""
    frame = pd.read_parquet(dataset_path)
    config = load_feature_config(feature_config)
    target = config["target"]
    group_column = config["group_column"]
    required = [target, group_column, "baseline_year"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"저장 Global Dataset에 필요한 컬럼이 없습니다: {', '.join(missing)}")
    metadata_columns = [column for column in config["metadata_columns"] if column in frame.columns]
    weights = frame["sample_weight"] if "sample_weight" in frame.columns else pd.Series(np.ones(len(frame)))
    return DatasetBundle(
        name="global",
        X=build_features(frame, config, strict=True),
        y=frame[target].astype("int8").reset_index(drop=True),
        groups=frame[group_column].astype("string").reset_index(drop=True),
        metadata=frame[metadata_columns].reset_index(drop=True),
        sample_weight=weights.astype("float64").reset_index(drop=True),
    )


def load_saved_global_train_test(
    dataset_path: str | Path,
    split_path: str | Path,
    feature_config: str | Path | dict,
) -> tuple[DatasetBundle, DatasetBundle]:
    """고정 `split_ids.csv`를 적용한 Global Train/Test Bundle을 반환한다."""
    bundle = load_saved_global_dataset(dataset_path, feature_config)
    split_ids = pd.read_csv(split_path, dtype={"SAMPID": "string"})
    train_bundle = select_split(bundle, split_ids, "train")
    test_bundle = select_split(bundle, split_ids, "test")
    overlap = set(train_bundle.groups.astype("string")) & set(test_bundle.groups.astype("string"))
    if overlap:
        raise RuntimeError("고정 Train/Test split에 겹치는 SAMPID가 있습니다.")
    return train_bundle, test_bundle
