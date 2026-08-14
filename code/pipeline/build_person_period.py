"""프로토콜 v1.2의 Person-Period 분석 행 생성."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

BASELINE_YEARS = (2021, 2022, 2023)
# job_seeker(c602)·recent_employment_prep(c635)는 더 이상 적격 판정 필터로 쓰지 않는다 — 2026-08-15
# "YP2021 Global/Local 데이터셋 전처리 업무안내" 지침에 따라 미취업자(ECOACT∈{2,3}) 전체를 분석 대상으로
# 포함하고, 구직·취업준비 여부는 feature(recent_job_search/recent_employment_prep)로만 쓴다.
REQUIRED_BASELINE_COLUMNS = {"SAMPID", "responded", "ecoact", "job_seeker", "recent_employment_prep"}
REQUIRED_TARGET_COLUMNS = {"SAMPID", "responded", "ecoact"}


def _validate_wave(frame: pd.DataFrame, year: int, required: set[str]) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{year}년 표준 입력에 필요한 컬럼이 없습니다: {', '.join(missing)}")
    if frame["SAMPID"].isna().any() or frame["SAMPID"].duplicated().any():
        raise ValueError(f"{year}년 표준 입력의 SAMPID는 결측·중복 없이 한 사람당 한 행이어야 합니다.")


def build_person_period_dataset(annual_data: Mapping[int, pd.DataFrame]) -> pd.DataFrame:
    """세 전환의 미취업자(실업·비경제활동) 전체 행을 하나의 Person-Period DataFrame으로 만든다.

    입력 annual_data의 각 행은 해당 조사연도에 실제 응답한 패널 한 명의 표준화된 값이다.
    이 함수는 기준연도 이후 컬럼을 합치지 않으므로 Feature 누수를 만들지 않는다.
    """
    expected = set(range(2021, 2025))
    missing_years = sorted(expected - set(annual_data))
    if missing_years:
        raise ValueError(f"2021~2024 네 차수 입력이 필요합니다. 없음: {missing_years}")

    periods: list[pd.DataFrame] = []
    for baseline_year in BASELINE_YEARS:
        baseline = annual_data[baseline_year].copy()
        next_year = annual_data[baseline_year + 1].copy()
        _validate_wave(baseline, baseline_year, REQUIRED_BASELINE_COLUMNS)
        _validate_wave(next_year, baseline_year + 1, REQUIRED_TARGET_COLUMNS)

        target = next_year[["SAMPID", "responded", "ecoact"]].rename(
            columns={"responded": "target_responded", "ecoact": "target_ecoact"}
        )
        merged = baseline.merge(target, on="SAMPID", how="inner", validate="one_to_one")
        eligible = (
            merged["responded"].eq(1).fillna(False)
            & merged["target_responded"].eq(1).fillna(False)
            & merged["ecoact"].isin([2, 3]).fillna(False)
        )
        period = merged.loc[eligible].copy()
        period.insert(1, "baseline_year", baseline_year)
        period.insert(2, "target_year", baseline_year + 1)
        period["nonemployment_type"] = period["ecoact"].map({2: "unemployed", 3: "economically_inactive"})
        period["employment_transition"] = period["target_ecoact"].eq(1).astype("int8")
        period = period.drop(columns=["target_responded", "target_ecoact"])
        periods.append(period)

    result = pd.concat(periods, ignore_index=True)
    result["SAMPID"] = result["SAMPID"].astype("string")
    return result.sort_values(["SAMPID", "baseline_year"], kind="stable").reset_index(drop=True)
