"""SAMPID 기준 Train/Test 고정 분할."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from code.contracts import DatasetBundle


def build_split_ids(
    y: pd.Series,
    groups: pd.Series,
    *,
    n_splits: int = 5,
    test_fold: int = 0,
    random_state: int = 42,
) -> pd.DataFrame:
    """Global Dataset에서 한 번 생성해 Global/Local이 공유할 SAMPID 분할표를 만든다."""
    if not 0 <= test_fold < n_splits:
        raise ValueError("test_fold는 0 이상 n_splits 미만이어야 합니다.")
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    group_folds: dict[str, int] = {}
    for fold, (_, test_index) in enumerate(splitter.split(np.zeros(len(y)), y, groups)):
        for sampid in groups.iloc[test_index].astype("string").unique():
            group_folds[str(sampid)] = fold
    if len(group_folds) != groups.astype("string").nunique():
        raise RuntimeError("모든 SAMPID에 outer_fold를 배정하지 못했습니다.")
    result = pd.DataFrame({"SAMPID": list(group_folds), "outer_fold": list(group_folds.values())})
    result["split"] = np.where(result["outer_fold"].eq(test_fold), "test", "train")
    result["SAMPID"] = result["SAMPID"].astype("string")
    return result.sort_values("SAMPID").reset_index(drop=True)


def select_split(bundle: DatasetBundle, split_ids: pd.DataFrame, split: str) -> DatasetBundle:
    """고정된 SAMPID 표를 적용해 Train 또는 Test DatasetBundle을 반환한다."""
    if split not in {"train", "test"}:
        raise ValueError("split은 train 또는 test여야 합니다.")
    lookup = split_ids.set_index("SAMPID")["split"]
    assigned = bundle.groups.astype("string").map(lookup)
    if assigned.isna().any():
        raise ValueError("split_ids.csv에 없는 SAMPID가 DatasetBundle에 있습니다.")
    mask = assigned.eq(split).to_numpy()
    return DatasetBundle(
        name=bundle.name,
        X=bundle.X.loc[mask].reset_index(drop=True),
        y=bundle.y.loc[mask].reset_index(drop=True),
        groups=bundle.groups.loc[mask].reset_index(drop=True),
        metadata=bundle.metadata.loc[mask].reset_index(drop=True),
    )
