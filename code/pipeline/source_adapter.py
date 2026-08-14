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
    ]
    if wave >= 2:
        columns.extend([f"{question}a193", f"{question}a194", f"{question}a244z"])
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

        for output, input_column, rule_name in [
            ("gender", "gender", "gender"), ("age", f"{prefix}age", "age"),
            ("region_5", f"{prefix}region_a", "region_5"),
            ("education_level", f"{prefix}edu", "education_level"),
            ("student_status", f"{prefix}student", "student_status"),
            ("student_type", f"{prefix}student_type", "student_type"),
        ]:
            frame[output], _ = _normalize_variable(source[input_column], rule_name)
        current, _ = _normalize_variable(
            source.get(f"{prefix}univ_type_current", pd.Series(pd.NA, index=source.index)),
            "university_type_current",
        )
        graduate, _ = _normalize_variable(
            source.get(f"{prefix}univ_type_graduate", pd.Series(pd.NA, index=source.index)),
            "university_type_graduate",
        )
        frame["university_type"] = current.combine_first(graduate)
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
