"""XGBoost의 CV fold별 class-ratio 가중치 처리."""

from __future__ import annotations

import numpy as np

TRAIN_NEGATIVE_POSITIVE_RATIO = "train_negative_positive_ratio"

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover - XGBoost를 호출하는 환경에서만 확인한다.
    XGBClassifier = None


def train_negative_positive_ratio(y) -> float:
    """현재 `fit()`에 전달된 Train fold의 negative / positive 비율을 계산한다."""
    values = np.asarray(y)
    negative = int((values == 0).sum())
    positive = int((values == 1).sum())
    if positive == 0 or negative == 0:
        raise ValueError("XGBoost scale_pos_weight 계산에는 Train fold의 두 class가 모두 필요합니다.")
    return negative / positive


if XGBClassifier is not None:

    class FoldAwareXGBClassifier(XGBClassifier):
        """`fit()` 직전에 현재 fold의 y로 marker 가중치를 치환하는 XGBoost 분류기."""

        def fit(self, X, y, *args, **fit_kwargs):
            if self.get_params().get("scale_pos_weight") == TRAIN_NEGATIVE_POSITIVE_RATIO:
                self.set_params(scale_pos_weight=train_negative_positive_ratio(y))
            return super().fit(X, y, *args, **fit_kwargs)

else:

    class FoldAwareXGBClassifier:  # pragma: no cover - import 오류 안내용 대체 객체
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError("XGBoost를 사용하려면 code/requirements.txt의 xgboost를 설치하세요.")
