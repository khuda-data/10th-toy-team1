"""기준시점 이전 희망직업 이력을 붙여 Local Dataset을 만든다."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from code.contracts import DatasetBundle
from code.pipeline.build_global import build_global_dataset


def build_local_dataset(
    person_period: pd.DataFrame,
    hope_job_history: pd.DataFrame,
    keco_mapping: str | Path | pd.DataFrame,
    feature_config: str | Path | dict,
    *,
    strict_features: bool = True,
) -> DatasetBundle:
    """baseline_year까지의 가장 최근 실제 희망직업만 써서 Local 입력을 만든다."""
    history_required = {"SAMPID", "response_year", "hope_job_keco", "hope_job_source"}
    missing = sorted(history_required - set(hope_job_history.columns))
    if missing:
        raise ValueError(f"희망직업 이력에 필수 컬럼이 없습니다: {', '.join(missing)}")
    mapping = pd.read_csv(keco_mapping, dtype={"keco_major_code": "string"}) if not isinstance(keco_mapping, pd.DataFrame) else keco_mapping.copy()
    if {"keco_major_code", "job_group"} - set(mapping.columns):
        raise ValueError("KECO 매핑에는 keco_major_code, job_group 컬럼이 필요합니다.")

    base = person_period.reset_index(names="_row_id")
    history = hope_job_history.copy()
    history["SAMPID"] = history["SAMPID"].astype("string")
    history["hope_job_keco"] = history["hope_job_keco"].astype("string")
    history["source_priority"] = history.get("source_priority", history["hope_job_source"].ne("current_preparation").astype(int))
    candidates = base[["_row_id", "SAMPID", "baseline_year"]].merge(history, on="SAMPID", how="left")
    candidates = candidates.loc[candidates["response_year"].le(candidates["baseline_year"])].copy()
    candidates = candidates.sort_values(["_row_id", "response_year", "source_priority"], ascending=[True, False, True])
    latest = candidates.drop_duplicates("_row_id", keep="first")
    local = base.merge(
        latest[["_row_id", "hope_job_keco", "response_year", "hope_job_source"]], on="_row_id", how="inner"
    ).rename(columns={"response_year": "hope_job_year"})
    local = local.merge(mapping, left_on="hope_job_keco", right_on="keco_major_code", how="left", validate="many_to_one")
    local = local.drop(columns=["_row_id", "keco_major_code"])
    local = local.loc[local["job_group"].notna()].reset_index(drop=True)
    bundle = build_global_dataset(local, feature_config, strict_features=strict_features)
    return DatasetBundle(
        name="local",
        X=bundle.X,
        y=bundle.y,
        groups=bundle.groups,
        metadata=local[["SAMPID", "baseline_year", "target_year", "hope_job_keco", "hope_job_year", "hope_job_source", "job_group"]],
    )
