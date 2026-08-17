"""프로토콜 v1.3의 기준연도 미취업자 Person-Period 분석 행 생성."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

BASELINE_YEARS = (2021, 2022, 2023)
# job_seeker(c602)·recent_employment_prep(c635)는 더 이상 적격 판정 필터로 쓰지 않는다 — 2026-08-15
# "YP2021 Global/Local 데이터셋 전처리 업무안내" 지침에 따라 미취업자(ECOACT∈{2,3}) 전체를 분석 대상으로
# 포함하고, 구직·취업준비 여부는 feature(recent_job_search/recent_employment_prep)로만 쓴다.
REQUIRED_BASELINE_COLUMNS = {"SAMPID", "responded", "ecoact", "job_seeker", "recent_employment_prep"}
REQUIRED_TARGET_COLUMNS = {"SAMPID", "responded", "ecoact"}

# 13번 설계안(plan/details/13-YP2021-PersonPeriod-전처리-설계안.md) §2·§3의 그룹별 결측 처리 원칙.
# Group A(고정·준고정): baseline이 실제 결측(NaN)일 때만 최신순으로 과거 유효값을 채운다.
GROUP_A_BACKFILL_COLUMNS = ("gender", "education_level", "major_group")

# Group D(과거 누적 이력) 경험 여부형 9개: 2021~baseline-1 중 한 해라도 1이면 baseline도 1로
# 유지한다(과거 0·현재 결측만으로 현재도 0이라고 단정하지 않음).
GROUP_D_EVER_FLAG_COLUMNS = (
    "graduation_prep_experience",
    "graduation_job_search_experience",
    "has_certificate",
    "has_employment_certificate",
    "has_major_related_certificate",
    "has_vocational_training",
    "exam_prep_experience",
    "school_work_experience",
    "ever_worked_before",
)

# Group D 개수형 4개: 설문 원문(통합설문지_0227.pdf) 확인 결과 e301(자격증·227쪽)·e101(직업훈련·
# 220쪽)·e001(시험준비·216쪽)은 "[2차 조사] 조사 시점의 경험과 과거의 경험을 모두 응답 / [3차
# 조사 이후] 지난 조사 이후의 경험만 응답"이고, d001(경험일자리·148쪽)은 매 차수 증분형,
# d501(1차 전용 회고조사·194쪽)은 2021년까지 전체 이력이다. 즉 baseline까지 연도별로 단순
# 합산하면(2차=전체이력 + 3차 이후=증분) 정확히 baseline까지의 누적값이 된다. 세션 로그 참조.
# vocational_training_hours·past_work_months는 기간형이고 이미 "1번째 일자리/훈련만 계산"하는
# 설계 한계가 안건함에 등록돼 있어 합산 대상에서 제외한다.
GROUP_D_CUMULATIVE_COUNT_COLUMNS = (
    "certificate_count",
    "vocational_training_count",
    "exam_prep_count",
    "past_job_count",
)


def _validate_wave(frame: pd.DataFrame, year: int, required: set[str]) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{year}년 표준 입력에 필요한 컬럼이 없습니다: {', '.join(missing)}")
    if frame["SAMPID"].isna().any() or frame["SAMPID"].duplicated().any():
        raise ValueError(f"{year}년 표준 입력의 SAMPID는 결측·중복 없이 한 사람당 한 행이어야 합니다.")


def _prior_year_column(
    annual_data: Mapping[int, pd.DataFrame], year: int, sampid: pd.Series, column: str
) -> pd.Series:
    """`year` 조사에 실제 응답한 사람만 대상으로 `column` 값을 `sampid` 순서에 맞춰 조회한다."""
    frame = annual_data.get(year)
    if frame is None or column not in frame.columns:
        return pd.Series(pd.NA, index=sampid.index)
    responded = frame.loc[frame["responded"].eq(1).fillna(False)]
    lookup = responded.drop_duplicates("SAMPID", keep="last").set_index("SAMPID")[column]
    return sampid.map(lookup)


def _backfill_group_a(
    period: pd.DataFrame, annual_data: Mapping[int, pd.DataFrame], baseline_year: int
) -> pd.DataFrame:
    """Group A(고정·준고정): baseline이 실제 결측일 때만 최신순으로 과거 유효값을 채운다.

    `NotApplicable`은 그 해에 이미 확정된 사실이라 덮어쓰지 않고, 그 경우도 더 과거를 계속 찾는다.
    """
    filled = period.copy()
    for column in GROUP_A_BACKFILL_COLUMNS:
        if column not in filled.columns:
            continue
        needs_fill = filled[column].isna()
        if not needs_fill.any():
            continue
        for year in range(baseline_year - 1, 2020, -1):
            if not needs_fill.any():
                break
            prior = _prior_year_column(annual_data, year, filled["SAMPID"], column)
            usable = needs_fill & prior.notna() & prior.ne("NotApplicable")
            filled.loc[usable, column] = prior.loc[usable]
            needs_fill &= ~usable
    return filled


def _accumulate_group_d(
    period: pd.DataFrame, annual_data: Mapping[int, pd.DataFrame], baseline_year: int
) -> pd.DataFrame:
    """Group D(과거 누적 이력): 경험 여부형은 한 해라도 1이면 1로, 개수형 4개는 baseline까지 합산한다."""
    filled = period.copy()
    for column in GROUP_D_EVER_FLAG_COLUMNS:
        if column not in filled.columns:
            continue
        combined = filled[column].astype("Int64")
        for year in range(2021, baseline_year):
            prior = _prior_year_column(annual_data, year, filled["SAMPID"], column)
            combined = combined.mask(prior.eq(1).fillna(False), 1)
        filled[column] = combined

    for column in GROUP_D_CUMULATIVE_COUNT_COLUMNS:
        if column not in filled.columns:
            continue
        total = filled[column].astype("Float64")
        has_value = total.notna()
        for year in range(2021, baseline_year):
            prior = _prior_year_column(annual_data, year, filled["SAMPID"], column).astype("Float64")
            total = total.add(prior, fill_value=0)
            has_value = has_value | prior.notna()
        filled[column] = total.mask(~has_value)
    return filled


def build_person_period_dataset(annual_data: Mapping[int, pd.DataFrame]) -> pd.DataFrame:
    """세 전환의 미취업자(실업·비경제활동) 전체 행을 하나의 Person-Period DataFrame으로 만든다.

    입력 annual_data의 각 행은 해당 조사연도에 실제 응답한 패널 한 명의 표준화된 값이다.
    `job_seeker`, `recent_employment_prep` 등 취업준비 관련 값은 적격 조건이 아니라
    기준연도 Feature로 남긴다. 이 함수는 기준연도 이후(미래) Feature를 합치지 않으므로
    Feature 누수를 만들지 않는다. 기준연도 이전 데이터는 13번 설계안 §2·§3에 따라
    Group A/D 일부 Feature의 결측 보완·이력 누적에만 쓴다(`_backfill_group_a`,
    `_accumulate_group_d`).
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
            # Target을 0으로 자동 대체하지 않는다. 다음연도 ECOACT가 1/2/3일 때만 행을 만든다.
            & merged["target_ecoact"].isin([1, 2, 3]).fillna(False)
        )
        period = merged.loc[eligible].copy()
        period = _backfill_group_a(period, annual_data, baseline_year)
        period = _accumulate_group_d(period, annual_data, baseline_year)
        period.insert(1, "baseline_year", baseline_year)
        period.insert(2, "target_year", baseline_year + 1)
        period["nonemployment_type"] = period["ecoact"].map({2: "unemployed", 3: "economically_inactive"})
        period["employment_transition"] = period["target_ecoact"].eq(1).astype("int8")
        period = period.drop(columns=["target_responded", "target_ecoact"])
        periods.append(period)

    result = pd.concat(periods, ignore_index=True)
    result["SAMPID"] = result["SAMPID"].astype("string")
    result = result.sort_values(["SAMPID", "baseline_year"], kind="stable").reset_index(drop=True)
    # 오버샘플링 완화 feature(2026-08-18, wjdwlsah 확정): 같은 사람이 이전에 몇 번 더
    # 미취업 상태로 관찰됐는지(0부터). Global 전체 이력 기준으로 여기서 한 번만 계산해야
    # Local로 필터링된 뒤에도 값이 왜곡되지 않는다(예: 특정 연도에 희망직업 미응답으로
    # Local에서 그 행만 빠져도, 이 값은 실제 반복 이력을 그대로 유지해야 함).
    result["n_prior_periods"] = result.groupby("SAMPID").cumcount()
    return result
