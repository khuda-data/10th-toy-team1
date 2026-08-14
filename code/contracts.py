"""모듈 사이에서 공유하는 가벼운 데이터 계약 객체."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatasetBundle:
    """모델 학습에 필요한 Feature, target, SAMPID 그룹과 부가정보 묶음."""

    name: str
    X: pd.DataFrame
    y: pd.Series
    groups: pd.Series
    metadata: pd.DataFrame

    def to_frame(self) -> pd.DataFrame:
        """공용 parquet 저장용으로 metadata, Feature, target을 한 DataFrame으로 합친다."""
        frame = self.metadata.reset_index(drop=True).copy()
        for column in self.X.columns:
            if column in frame.columns:
                # baseline_year처럼 metadata이면서 Feature인 컬럼은 저장 시 한 번만 둔다.
                # 값은 같은 원본 행에서 왔으므로 모델 입력 X에는 그대로 유지된다.
                continue
            frame[column] = self.X[column].reset_index(drop=True)
        frame["employment_transition"] = self.y.reset_index(drop=True).astype("int8")
        return frame
