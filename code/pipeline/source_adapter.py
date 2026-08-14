"""제공된 YP2021 Excel 원자료를 공통 파이프라인의 표준 입력으로 바꾼다.

이 모듈은 분석 기준을 정하지 않는다. 프로토콜에 명시된 Person-Period 포함 조건과
희망직업 이력만 안전하게 읽어 전달하며, 나머지 Feature 누적 로직은 preprocess 모듈의
담당자가 코드북 대조 후 보완한다.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

SPECIAL_MISSING_MIN = 9_000_000
WAVE_TO_YEAR = {1: 2021, 2: 2022, 3: 2023, 4: 2024}


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


def _clean_special_missing(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.mask(numeric >= SPECIAL_MISSING_MIN)


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
        frame["responded"] = _clean_special_missing(source[prefix]).eq(1).astype("int8")
        frame["ecoact"] = _clean_special_missing(source[f"{prefix}ecoact"])
        frame["job_seeker"] = _clean_special_missing(source[f"{question}c602"])
        frame["recent_employment_prep"] = _clean_special_missing(source[f"{question}c635"]).eq(1).astype("Int64")
        frame["recent_job_search"] = (
            frame["job_seeker"].eq(1) | _clean_special_missing(source[f"{question}c628"]).eq(1)
        ).astype("Int64")
        for output, input_column in {
            "gender": "gender", "age": f"{prefix}age", "region_5": f"{prefix}region_a",
            "education_level": f"{prefix}edu", "student_status": f"{prefix}student",
            "student_type": f"{prefix}student_type",
        }.items():
            frame[output] = _clean_special_missing(source[input_column])
        current = _clean_special_missing(source.get(f"{prefix}univ_type_current", pd.Series(pd.NA, index=source.index)))
        graduate = _clean_special_missing(source.get(f"{prefix}univ_type_graduate", pd.Series(pd.NA, index=source.index)))
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
            values = _clean_special_missing(source[column])
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
