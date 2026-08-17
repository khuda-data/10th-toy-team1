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
    # 오버샘플링 완화용(2026-08-18): 1 / 이 사람이 이 데이터셋(Global 또는 개별 Local)에서
    # 차지하는 행 수. 이 데이터셋 자체의 행 구조를 반영해야 하므로 Global/Local마다 각각
    # 계산한다(person_period 기준으로 한 번만 계산하는 n_prior_periods와는 다른 성격).
    sample_weight: pd.Series

    def to_frame(self) -> pd.DataFrame:
        """공용 parquet 저장용으로 metadata, Feature, target, 가중치를 한 DataFrame으로 합친다."""
        frame = self.metadata.reset_index(drop=True).copy()
        for column in self.X.columns:
            if column in frame.columns:
                # baseline_year처럼 metadata이면서 Feature인 컬럼은 저장 시 한 번만 둔다.
                # 값은 같은 원본 행에서 왔으므로 모델 입력 X에는 그대로 유지된다.
                continue
            frame[column] = self.X[column].reset_index(drop=True)
        frame["employment_transition"] = self.y.reset_index(drop=True).astype("int8")
        frame["sample_weight"] = self.sample_weight.reset_index(drop=True)
        return frame
