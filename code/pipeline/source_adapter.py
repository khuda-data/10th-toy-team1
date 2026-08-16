"""제공된 YP2021 Excel 원자료를 공통 파이프라인의 표준 입력으로 바꾼다.

이 모듈은 분석 기준을 정하지 않는다. Person-Period 생성을 위한 기준연도·다음연도
경제활동상태와 희망직업 이력만 안전하게 읽어 전달하며, 나머지 Feature 누적 로직은
preprocess 모듈의 담당자가 코드북 대조 후 보완한다.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

WAVE_TO_YEAR = {1: 2021, 2: 2022, 3: 2023, 4: 2024}
MISSING_RULES_PATH = Path(__file__).resolve().parents[1] / "config" / "yp2021_missing_rules.json"


def _safe_read_excel(path: Path, usecols: list[str] | None, *, nrows: int | None = None) -> pd.DataFrame:
    """공급 Excel의 비표준 synchVertical 속성을 임시 복사본에서만 제거해 읽는다."""
    try:
        return pd.read_excel(path, usecols=usecols, nrows=nrows)
    except TypeError as error:
        if "synchVertical" not in str(error):
            raise

    with TemporaryDirectory(prefix="yp2021_xlsx_") as directory:
        repaired = Path(directory) / path.name
        with ZipFile(path) as source, ZipFile(repaired, "w", ZIP_DEFLATED) as target:
            for member in source.infolist():
                data = source.read(member.filename)
                if member.filename.startswith("xl/worksheets/") and member.filename.endswith(".xml"):
                    data = data.replace(b' synchVertical="1"', b"")
                target.writestr(member, data)
        return pd.read_excel(repaired, usecols=usecols, nrows=nrows)


def _source_columns(wave: int) -> list[str]:
    prefix = f"w{wave:02d}"
    question = f"y{wave:02d}"
    columns = [
        "sampid", prefix, f"{prefix}ecoact", "gender", f"{prefix}age", f"{prefix}region_a",
        f"{prefix}edu", f"{prefix}student", f"{prefix}student_type", f"{prefix}univ_type_current",
        f"{prefix}univ_type_graduate", f"{prefix}eduy", f"{prefix}edum", f"date{wave:02d}_y",
        f"date{wave:02d}_m", f"{question}c602", f"{question}c628", f"{question}c635",
        f"{question}c773z",
        # [취준] 업무/직무 관련 자격증을 스펙으로 준비했는지 — 1~4차 전체에서 물어봄(취준 응답자 대상).
        f"{question}c720",
        # [공통] 전공계열 — 1~4차 전체(코드북 확인).
        f"{question}a413",
    ]
    if wave >= 2:
        columns.extend([
            f"{question}a193", f"{question}a194", f"{question}a244z",
            # [졸|취준] 업무/직무 관련 자격증 스펙 — c720의 졸업자 버전. 1차엔 없음.
            f"{question}a207",
            # 자격증: 취득 여부·개수·[1]번째 자격증의 전공 관련도. 1차엔 문항 자체가 없음(코드북 확인).
            f"{question}e301", f"{question}e302", f"{question}e307_1",
            # 직업교육훈련: 경험 여부·횟수·[1]번째 훈련 총 시간. 1차엔 없음.
            f"{question}e101", f"{question}e102", f"{question}e108_1",
            # 경험일자리(일 경험) 유무·횟수 — 2~4차용 문항.
            f"{question}d001", f"{question}d002",
            # 재학중 일경험 유형[1] — 게이팅(여부) 문항은 코드북에서 못 찾음. 값이 있으면 '있음'만 판정.
            f"{question}a186_1",
            # 취업노력 1~3순위(다중응답) — 2~4차는 순위형, prep_effort_01~12로 멀티핫 전개.
            f"{question}c701a", f"{question}c701b", f"{question}c701c",
            # 시험준비: 경험여부·개수·[1]번째의 현재 지속 여부. 1차엔 없음.
            f"{question}e001", f"{question}e002", f"{question}e008_1",
            # 경험일자리[1]의 시작·종료 시점 — past_work_months 계산용(첫 일자리만, 코드북 근거·한계는 세션 로그 참조).
            f"{question}d003a_1", f"{question}d003b_1",
            f"{question}d036a_1", f"{question}d036b_1", f"{question}d074_1", f"{question}d075_1",
        ])
    if wave == 1:
        # 경험일자리 유무·횟수의 1차 전용 문항(회고조사). 2~4차의 d001/d002와 짝을 이룸.
        columns.extend([f"{question}d501", f"{question}d502"])
        # 1차는 취업노력을 순위형(c701a~c) 대신 문항 12개의 개별 예/아니오로 물어봄 — 코드·순서가 c701의 값 1~12와 동일(코드북 확인).
        columns.extend([f"{question}c70{i}" for i in range(2, 14)])
        # 재학중 일경험 유형[1]의 1차 전용 문항(회고조사). a186_1과 짝을 이룸.
        columns.append(f"{question}a616_1")
        # 경험일자리[1]의 시작·종료 시점 — 1차 전용(회고조사) 문항. d003/d036/d074와 짝을 이룸.
        columns.extend([
            f"{question}d503a_1", f"{question}d503b_1",
            f"{question}d532a_1", f"{question}d532b_1", f"{question}d577a_1", f"{question}d577b_1",
        ])
    return columns


def _available_columns(path: Path) -> set[str]:
    # 첫 행만 읽어 원자료 버전별로 없는 문항을 자동 제외한다.
    return set(_safe_read_excel(path, usecols=None, nrows=0).columns)


def load_yp2021_raw(raw_zip: str | Path) -> dict[int, pd.DataFrame]:
    """공급된 `YP2021_EXCEL_*.zip`에서 차수별 필요 열만 읽는다.

    원본 zip과 xlsx는 수정하지 않으며, 임시 폴더에서만 압축을 풀어 읽는다.
    """
    raw_zip = Path(raw_zip)
    if not raw_zip.is_file():
        raise FileNotFoundError(f"YP2021 원자료 zip을 찾지 못했습니다: {raw_zip}")

    frames: dict[int, pd.DataFrame] = {}
    with TemporaryDirectory(prefix="yp2021_raw_") as directory:
        root = Path(directory)
        with ZipFile(raw_zip) as archive:
            archive.extractall(root)
        for wave, year in WAVE_TO_YEAR.items():
            matches = list(root.glob(f"YP2021_w{wave:02d}.xlsx"))
            if len(matches) != 1:
                raise FileNotFoundError(f"압축파일 안에서 YP2021_w{wave:02d}.xlsx를 찾지 못했습니다.")
            path = matches[0]
            available = _available_columns(path)
            requested = [column for column in _source_columns(wave) if column in available]
            frames[year] = _safe_read_excel(path, usecols=requested)
    return frames


def _load_missing_rules() -> dict[str, dict[str, object]]:
    """코드북 대조를 마친 변수별 특수결측 규칙을 읽는다.

    숫자가 크다는 이유만으로 결측으로 바꾸지 않는다. 새 원변수를 추가할 때는 먼저
    `code/config/yp2021_missing_rules.json`에 그 변수의 코드북 기준을 추가해야 한다.
    """
    with MISSING_RULES_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)
    return config["rules"]


MISSING_RULES = _load_missing_rules()


def _normalize_variable(series: pd.Series, rule_name: str) -> tuple[pd.Series, pd.Series]:
    """원코드를 값과 결측 사유(`Missing`/`NotApplicable`)로 나눠 표준화한다."""
    try:
        rule = MISSING_RULES[rule_name]
    except KeyError as error:
        raise KeyError(f"특수결측 규칙이 없는 변수입니다: {rule_name}") from error

    numeric = pd.to_numeric(series, errors="coerce")
    code_reasons = {int(code): reason for code, reason in rule["source_codes"].items()}
    reasons = pd.Series(pd.NA, index=series.index, dtype="string")
    for code, reason in code_reasons.items():
        reasons.loc[numeric.eq(code)] = reason
    reasons.loc[numeric.isna()] = rule["blank_reason"]
    return numeric.mask(reasons.notna()), reasons


def _categorical_from_reason(value: pd.Series, reason: pd.Series) -> pd.Series:
    """범주형 원 Feature용: `NotApplicable` 사유는 문자열 그대로 남기고, `Missing`만 NaN으로 둔다.

    NaN으로 둔 `Missing`은 이후 `build_preprocessor`가 Train 결측 상수 `Missing`으로 채운다.
    `NotApplicable`은 원자료 분기로 이미 확정된 사실이라 학습 없이 그대로 별도 범주로 남겨야
    프로토콜의 "Missing·NotApplicable은 통합하지 않는다"를 지킬 수 있다. `_normalize_variable`이
    계산하는 사유를 버리지 않고 값에 다시 실어보내는 역할만 한다.
    """
    result = value.astype("string")
    result.loc[reason.eq("NotApplicable")] = "NotApplicable"
    return result


def _normalize_categorical(series: pd.Series, rule_name: str) -> pd.Series:
    """단일 원문항을 범주형 Feature로 표준화한다 (`_normalize_variable` + `_categorical_from_reason`)."""
    return _categorical_from_reason(*_normalize_variable(series, rule_name))


def _merge_categorical_sources(
    left_value: pd.Series, left_reason: pd.Series, right_value: pd.Series, right_reason: pd.Series
) -> pd.Series:
    """두 원문항 중 실제 응답이 있는 쪽 값을 쓰는 범주형 Feature(예: 재학 중 대학유형과 졸업 대학유형).

    응답거절·모름(Missing)을 설문 비해당(NotApplicable)보다 우선해 감사 가능하게 남긴다 —
    `_combine_binary_or`와 같은 원칙.
    """
    value = left_value.combine_first(right_value)
    reason = pd.Series(pd.NA, index=left_value.index, dtype="string")
    both_unobserved = value.isna()
    has_missing = left_reason.eq("Missing") | right_reason.eq("Missing")
    reason.loc[both_unobserved & has_missing] = "Missing"
    reason.loc[both_unobserved & ~has_missing] = "NotApplicable"
    return _categorical_from_reason(value, reason)


def _yes_no(values: pd.Series) -> pd.Series:
    """관측된 1/2형 문항만 1/0으로 변환하고, 미관측 값은 NA로 유지한다."""
    result = pd.Series(pd.NA, index=values.index, dtype="Int64")
    observed = values.notna()
    result.loc[observed] = values.loc[observed].eq(1).astype("Int64")
    return result


def _combine_binary_or(
    left_values: pd.Series,
    left_reasons: pd.Series,
    right_values: pd.Series,
    right_reasons: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """두 문항의 '있음=1'을 합치되, 둘 다 미관측일 때 0을 만들지 않는다."""
    observed = left_values.notna() | right_values.notna()
    value = pd.Series(pd.NA, index=left_values.index, dtype="Int64")
    value.loc[observed] = (
        left_values.loc[observed].eq(1) | right_values.loc[observed].eq(1)
    ).astype("Int64")

    reason = pd.Series(pd.NA, index=left_values.index, dtype="string")
    unobserved = ~observed
    # 응답거절·모름(Missing)을 설문 비해당(NotApplicable)보다 우선해 감사 가능하게 남긴다.
    has_missing = left_reasons.eq("Missing") | right_reasons.eq("Missing")
    reason.loc[unobserved & has_missing] = "Missing"
    reason.loc[unobserved & ~has_missing] = "NotApplicable"
    return value, reason


def _conditional_zero(gate: pd.Series, value: pd.Series) -> pd.Series:
    """상위 '여부' 문항(1=있다/2=없다) 기준으로 하위 개수·시간 문항을 채운다.

    gate=2(없다)면 하위 문항 자체를 안 물어봐 원자료가 비어 있지만, 이 경우는
    '몰라서 결측'이 아니라 '없으니 논리적으로 0'이라 명시적으로 0을 채운다.
    gate=1(있다)이면 실제 응답값을, gate 자체가 결측이면 NA를 그대로 둔다.
    """
    result = pd.Series(pd.NA, index=gate.index, dtype="Float64")
    result.loc[gate.eq(2)] = 0
    has_value = gate.eq(1)
    result.loc[has_value] = value.loc[has_value]
    return result


def standardize_annual_frames(raw_frames: Mapping[int, pd.DataFrame]) -> dict[int, pd.DataFrame]:
    """원자료의 확인된 공통 문항을 Person-Period 입력 이름으로 표준화한다.

    복잡한 이력 누적 Feature는 이 단계에서 억지로 계산하지 않는다. 아직 없는 Feature는
    `build_features(..., strict=True)`가 명시적으로 알려 주므로, 결측을 0으로 바꿔
    분석 의미를 왜곡하지 않는다.
    """
    annual: dict[int, pd.DataFrame] = {}
    for year, source in raw_frames.items():
        wave = year - 2020
        prefix, question = f"w{wave:02d}", f"y{wave:02d}"
        frame = pd.DataFrame({"SAMPID": source["sampid"].astype("string")})
        responded, _ = _normalize_variable(source[prefix], "responded")
        frame["responded"] = _yes_no(responded)
        frame["ecoact"], _ = _normalize_variable(source[f"{prefix}ecoact"], "ecoact")
        frame["job_seeker"], job_seeker_reason = _normalize_variable(source[f"{question}c602"], "job_seeker")
        prep, prep_reason = _normalize_variable(source[f"{question}c635"], "recent_employment_prep_source")
        frame["recent_employment_prep"] = _yes_no(prep)
        frame["recent_employment_prep_reason"] = prep_reason

        previous_search, previous_search_reason = _normalize_variable(
            source[f"{question}c628"], "recent_job_search_source"
        )
        frame["recent_job_search"], frame["recent_job_search_reason"] = _combine_binary_or(
            frame["job_seeker"], job_seeker_reason, previous_search, previous_search_reason
        )

        # age는 수치형이라 값만 쓰고(실제 결측은 이후 Train median으로), 나머지는 범주형이라
        # NotApplicable 사유를 문자열로 보존한다(Missing·NotApplicable을 통합하지 않기 위함).
        frame["age"], _ = _normalize_variable(source[f"{prefix}age"], "age")
        for output, input_column, rule_name in [
            ("gender", "gender", "gender"),
            ("region_5", f"{prefix}region_a", "region_5"),
            ("education_level", f"{prefix}edu", "education_level"),
            ("student_status", f"{prefix}student", "student_status"),
            ("student_type", f"{prefix}student_type", "student_type"),
        ]:
            frame[output] = _normalize_categorical(source[input_column], rule_name)
        current_value, current_reason = _normalize_variable(
            source.get(f"{prefix}univ_type_current", pd.Series(pd.NA, index=source.index)),
            "university_type_current",
        )
        graduate_value, graduate_reason = _normalize_variable(
            source.get(f"{prefix}univ_type_graduate", pd.Series(pd.NA, index=source.index)),
            "university_type_graduate",
        )
        frame["university_type"] = _merge_categorical_sources(
            current_value, current_reason, graduate_value, graduate_reason
        )

        # --- 자격증: e301(취득여부)·e302(개수)·e307_1(1번째 자격증 전공관련도)는 1차 문항 자체가 없음(코드북 확인).
        cert_flag, _ = _normalize_variable(
            source.get(f"{question}e301", pd.Series(pd.NA, index=source.index)), "certificate_flag"
        )
        cert_count_raw, _ = _normalize_variable(
            source.get(f"{question}e302", pd.Series(pd.NA, index=source.index)), "certificate_count"
        )
        frame["has_certificate"] = _yes_no(cert_flag)
        frame["certificate_count"] = _conditional_zero(cert_flag, cert_count_raw)

        # 전공 관련도(1~4점, 3점 이상 '어느 정도 관련 있다'부터를 관련 있음으로 봄 — AI 제안 · 사람 검토 필요).
        major_related_raw, _ = _normalize_variable(
            source.get(f"{question}e307_1", pd.Series(pd.NA, index=source.index)), "certificate_major_related"
        )
        has_major_related = pd.Series(pd.NA, index=cert_flag.index, dtype="Int64")
        has_major_related.loc[cert_flag.eq(2)] = 0
        rated = cert_flag.eq(1) & major_related_raw.notna()
        has_major_related.loc[rated] = (major_related_raw.loc[rated] >= 3).astype("Int64")
        frame["has_major_related_certificate"] = has_major_related

        # [취준] 업무/직무 자격증을 스펙으로 준비했는지 — c720은 1~4차 전부, a207은 졸업자 버전(2차부터).
        # 1차는 c720만으로 채워지므로(a207 없음) 자격증 계열 중 유일하게 1차도 값이 생긴다.
        emp_cert_c, emp_cert_c_reason = _normalize_variable(source[f"{question}c720"], "employment_cert_spec")
        emp_cert_a, emp_cert_a_reason = _normalize_variable(
            source.get(f"{question}a207", pd.Series(pd.NA, index=source.index)), "employment_cert_spec"
        )
        frame["has_employment_certificate"], _ = _combine_binary_or(
            emp_cert_c, emp_cert_c_reason, emp_cert_a, emp_cert_a_reason
        )

        # --- 직업교육훈련: e101(경험여부)·e102(횟수)·e108_1(1번째 훈련 총 시간). 1차 문항 없음(코드북 확인).
        training_flag, _ = _normalize_variable(
            source.get(f"{question}e101", pd.Series(pd.NA, index=source.index)), "vocational_training_flag"
        )
        training_count_raw, _ = _normalize_variable(
            source.get(f"{question}e102", pd.Series(pd.NA, index=source.index)), "vocational_training_count"
        )
        training_hours_raw, _ = _normalize_variable(
            source.get(f"{question}e108_1", pd.Series(pd.NA, index=source.index)), "vocational_training_hours"
        )
        frame["has_vocational_training"] = _yes_no(training_flag)
        frame["vocational_training_count"] = _conditional_zero(training_flag, training_count_raw)
        frame["vocational_training_hours"] = _conditional_zero(training_flag, training_hours_raw)

        # --- 경험일자리(일 경험): 2~4차는 d001/d002, 1차는 회고조사 문항인 d501/d502를 쓴다(짝 문항, 코드북 확인).
        worked_col = f"{question}d501" if wave == 1 else f"{question}d001"
        count_col = f"{question}d502" if wave == 1 else f"{question}d002"
        worked_flag, _ = _normalize_variable(
            source.get(worked_col, pd.Series(pd.NA, index=source.index)), "ever_worked_flag"
        )
        job_count_raw, _ = _normalize_variable(
            source.get(count_col, pd.Series(pd.NA, index=source.index)), "job_count"
        )
        frame["ever_worked_before"] = _yes_no(worked_flag)
        frame["past_job_count"] = _conditional_zero(worked_flag, job_count_raw)

        # --- 전공계열: a413, 1~4차 전체(코드북 확인). 범주형이라 NotApplicable 사유를 문자열로 보존.
        frame["major_group"] = _normalize_categorical(source[f"{question}a413"], "major_group")

        # --- 졸업 후 경과 개월: 조사시점(date_y/date_m) - 최종학력 취득시점(eduy/edum).
        # eduy/edum은 기존에 이미 로딩만 되고 안 쓰이던 컬럼(원래 코드에 있었음).
        grad_year, _ = _normalize_variable(source[f"{prefix}eduy"], "graduation_year")
        grad_month, _ = _normalize_variable(source[f"{prefix}edum"], "graduation_month")
        survey_year, _ = _normalize_variable(source[f"date{wave:02d}_y"], "survey_year")
        survey_month, _ = _normalize_variable(source[f"date{wave:02d}_m"], "survey_month")
        has_all = grad_year.notna() & grad_month.notna() & survey_year.notna() & survey_month.notna()
        months = pd.Series(pd.NA, index=source.index, dtype="Float64")
        months.loc[has_all] = (
            (survey_year.loc[has_all] - grad_year.loc[has_all]) * 12
            + (survey_month.loc[has_all] - grad_month.loc[has_all])
        )
        frame["months_since_graduation"] = months

        # --- 졸업 전후 취업준비·구직활동 경험 — a193/a194, 2~4차만(1차엔 없음, 이미 로딩된 컬럼).
        grad_prep, _ = _normalize_variable(
            source.get(f"{question}a193", pd.Series(pd.NA, index=source.index)), "graduation_prep_flag"
        )
        grad_job_search, _ = _normalize_variable(
            source.get(f"{question}a194", pd.Series(pd.NA, index=source.index)), "graduation_job_search_flag"
        )
        frame["graduation_prep_experience"] = _yes_no(grad_prep)
        frame["graduation_job_search_experience"] = _yes_no(grad_job_search)

        # --- 취업노력 유형 12개 멀티핫(prep_effort_01~12) + 기타(prep_effort_other).
        # 2~4차: c701a/b/c(1~3순위, 값 1~12/97) 중 어디든 그 코드가 있으면 1. 셋 다 결측이면 문항 자체를 안 받은 것.
        # 1차: 순위형 문항이 없고 c702~c713 12개를 각각 예/아니오로 물어봄 — 값 순서가 c701의 코드 1~12와 동일(코드북 확인).
        if wave == 1:
            for i in range(1, 13):
                flag, _ = _normalize_variable(
                    source.get(f"{question}c70{i + 1}", pd.Series(pd.NA, index=source.index)),
                    "job_search_effort_flag",
                )
                frame[f"prep_effort_{i:02d}"] = _yes_no(flag)
            frame["prep_effort_other"] = pd.Series(pd.NA, index=source.index, dtype="Int64")  # 1차엔 '기타' 항목 없음
        else:
            ranks = [
                _normalize_variable(
                    source.get(f"{question}c701{letter}", pd.Series(pd.NA, index=source.index)),
                    "job_search_effort_rank",
                )[0]
                for letter in ("a", "b", "c")
            ]
            observed = ranks[0].notna() | ranks[1].notna() | ranks[2].notna()
            for i in range(1, 13):
                col = pd.Series(pd.NA, index=source.index, dtype="Int64")
                col.loc[observed] = 0
                for rank in ranks:
                    col.loc[rank.eq(i)] = 1
                frame[f"prep_effort_{i:02d}"] = col
            other = pd.Series(pd.NA, index=source.index, dtype="Int64")
            other.loc[observed] = 0
            for rank in ranks:
                other.loc[rank.eq(97)] = 1
            frame["prep_effort_other"] = other

        # --- 시험준비: e001(경험여부)·e002(개수)·e008_1([1]번째 현재 지속 여부). 1차엔 문항 없음(코드북 확인).
        exam_flag, _ = _normalize_variable(
            source.get(f"{question}e001", pd.Series(pd.NA, index=source.index)), "exam_prep_flag"
        )
        exam_count_raw, _ = _normalize_variable(
            source.get(f"{question}e002", pd.Series(pd.NA, index=source.index)), "exam_prep_count"
        )
        exam_current_raw, _ = _normalize_variable(
            source.get(f"{question}e008_1", pd.Series(pd.NA, index=source.index)), "exam_prep_current_flag"
        )
        frame["exam_prep_experience"] = _yes_no(exam_flag)
        frame["exam_prep_count"] = _conditional_zero(exam_flag, exam_count_raw)
        frame["currently_preparing_exam"] = _conditional_zero(exam_flag, _yes_no(exam_current_raw).astype("Float64"))

        # --- 재학중 일경험 유형[1] 〔AI 제안 · 사람 검토 필요〕: 상위 '여부' 게이팅 문항을 코드북에서 못 찾아
        # 값이 있으면 1(있음)만 판정하고, 없으면 NA로 둔다(0으로 단정하지 않음 — '경험없음'과 '문항 비해당'을 못 가름).
        school_work_col = f"{question}a616_1" if wave == 1 else f"{question}a186_1"
        school_work_type, _ = _normalize_variable(
            source.get(school_work_col, pd.Series(pd.NA, index=source.index)), "school_work_experience_type"
        )
        frame["school_work_experience"] = school_work_type.notna().astype("Int64").mask(school_work_type.isna())

        # --- 과거 근무 개월(첫 번째 경험일자리만) 〔AI 제안 · 사람 검토 필요〕: 여러 일자리 중 [1]번째만 계산.
        # 여러 일자리 총 근무기간 합산은 겹치는 기간 처리 등 별도 설계가 필요해 이번엔 [1]번째만 씀.
        if wave == 1:
            start_y_col, start_m_col = f"{question}d503a_1", f"{question}d503b_1"
            end_paid_y_col, end_paid_m_col = f"{question}d532a_1", f"{question}d532b_1"
            end_unpaid_y_col, end_unpaid_m_col = f"{question}d577a_1", f"{question}d577b_1"
        else:
            start_y_col, start_m_col = f"{question}d003a_1", f"{question}d003b_1"
            end_paid_y_col, end_paid_m_col = f"{question}d036a_1", f"{question}d036b_1"
            end_unpaid_y_col, end_unpaid_m_col = f"{question}d074_1", f"{question}d075_1"
        job1_start_y, _ = _normalize_variable(
            source.get(start_y_col, pd.Series(pd.NA, index=source.index)), "job_history_year"
        )
        job1_start_m, _ = _normalize_variable(
            source.get(start_m_col, pd.Series(pd.NA, index=source.index)), "job_history_month"
        )
        job1_end_paid_y, _ = _normalize_variable(
            source.get(end_paid_y_col, pd.Series(pd.NA, index=source.index)), "job_history_year"
        )
        job1_end_paid_m, _ = _normalize_variable(
            source.get(end_paid_m_col, pd.Series(pd.NA, index=source.index)), "job_history_month"
        )
        job1_end_unpaid_y, _ = _normalize_variable(
            source.get(end_unpaid_y_col, pd.Series(pd.NA, index=source.index)), "job_history_year"
        )
        job1_end_unpaid_m, _ = _normalize_variable(
            source.get(end_unpaid_m_col, pd.Series(pd.NA, index=source.index)), "job_history_month"
        )
        job1_end_y = job1_end_paid_y.combine_first(job1_end_unpaid_y)
        job1_end_m = job1_end_paid_m.combine_first(job1_end_unpaid_m)
        job1_has_all = job1_start_y.notna() & job1_start_m.notna() & job1_end_y.notna() & job1_end_m.notna()
        job1_months = pd.Series(pd.NA, index=source.index, dtype="Float64")
        job1_months.loc[job1_has_all] = (
            (job1_end_y.loc[job1_has_all] - job1_start_y.loc[job1_has_all]) * 12
            + (job1_end_m.loc[job1_has_all] - job1_start_m.loc[job1_has_all])
        )
        frame["past_work_months"] = job1_months

        annual[year] = frame
    return annual


def extract_hope_job_history(raw_frames: Mapping[int, pd.DataFrame]) -> pd.DataFrame:
    """각 조사연도에 실제 응답한 현재·장래 희망직업 대분류 이력을 세로 형태로 반환한다."""
    records: list[pd.DataFrame] = []
    for year, source in raw_frames.items():
        wave = year - 2020
        question = f"y{wave:02d}"
        for column, source_name, priority in [
            (f"{question}c773z", "current_preparation", 0),
            (f"{question}a244z", "graduation_future", 1),
        ]:
            if column not in source:
                continue
            values, _ = _normalize_variable(source[column], "hope_job_keco")
            rows = pd.DataFrame(
                {
                    "SAMPID": source["sampid"].astype("string"),
                    "response_year": year,
                    "hope_job_keco": values.astype("Int64").astype("string"),
                    "hope_job_source": source_name,
                    "source_priority": priority,
                }
            )
            records.append(rows.loc[values.notna()])
    if not records:
        return pd.DataFrame(columns=["SAMPID", "response_year", "hope_job_keco", "hope_job_source", "source_priority"])
    return pd.concat(records, ignore_index=True)
