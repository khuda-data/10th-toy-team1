# 2026-08-18 오버샘플링 완화 — n_prior_periods·sample_weight 구현

- 도구/모델: Claude Code / Sonnet 5
- 브랜치: feat/wjdwlsah-oversampling-mitigation

## 지침 (내가 시킨 것)
- 오버샘플링 문제(Global: 세 baseline_year 모두 등장 2,947명=41.3%가 전체 행의 59.3% 차지, 그중 5,894행=39.5%가 구조적으로 강제된 0라벨 / Local: 2개 이상 기간 등장 1,504명=53.0%) 제시 → 진단이 타당한지, 데이터셋을 두 벌(feature용/가중치용)로 나눠 각각 다른 처리를 하는 게 괜찮은지 판단 요청.
- 근본적으로 오버샘플링을 "제거"하려면 어떤 방법이 있는지 질문 → 시간 부족으로 근본 해결(1인 1행, 생존분석/혼합효과 모델)은 배제하고 완화 방안(feature 추가 + 가중치)으로 가기로 확정.
- "두 데이터셋으로 나눠서 비교하는 게 의미 있냐"는 질문에 답하며, `n_prior_periods`(무엇을 반영할지)와 `sample_weight`(얼마나 반영할지)가 서로 대체재가 아니라 보완재라는 논리로 **하나의 데이터셋에 둘 다 적용**하기로 최종 확정.
- `n_prior_periods`를 Local에서 재계산할지 질문 → "희망직업 미응답으로 Local에서 특정 연도 행이 빠지면 재계산 시 이력이 왜곡된다"는 근거로 **Global 이력 기준 1회 계산 후 그대로 유지**하기로 확정(사용자 직접 판단).
- `sample_weight`를 fold-aware로 계산해야 하는지 질문 → "개인 단위 통계량이라 사람 간 정보가 안 섞인다"는 반론 제기 → `split.py`의 SAMPID 그룹 분할 구조를 근거로 fold-aware 불필요함을 확인.
- 구현 계획(8개 파일) 제시 후 진행 승인 → 실행.

## AI가 한 일
- `code/pipeline/build_person_period.py`: `build_person_period_dataset()` 끝에 `n_prior_periods`(`groupby("SAMPID").cumcount()`) 컬럼 추가.
- `code/config/features.yaml`: `n_prior_periods`를 `numeric` Feature로 등록(`panel_history` 그룹).
- `code/contracts.py`: `DatasetBundle`에 `sample_weight: pd.Series` 필드 추가, `to_frame()`에도 포함.
- `code/pipeline/build_global.py`: `sample_weight = 1 / person_period.groupby("SAMPID")["SAMPID"].transform("size")` 계산해 bundle에 포함.
- `code/pipeline/build_local.py`: `build_global_dataset(local, ...)` 재사용 구조 덕분에 Local 부분집합 자체 기준으로 자동 재계산됨을 확인, `sample_weight` 필드 전달만 추가.
- `code/pipeline/split.py`: `select_split()`이 `sample_weight`도 같이 슬라이싱하도록 수정.
- `code/pipeline/run_pipeline.py`: `_subset_bundle()`(직군별 분할)에서도 그 직군 부분집합 기준으로 `sample_weight` 재계산 추가(구현 중 발견 — Local 전체 기준 값을 그대로 슬라이싱하면 직군별 실제 학습 단위와 안 맞는 문제). `_fit_model()`이 `bundle.sample_weight`를 `tune_model`/`train_model`에 전달하도록 수정.
- `code/model/tune.py`, `code/model/train.py`: `sample_weight_train` 인자 추가, `model__sample_weight`로 라우팅.
- `plan/details/06-인터페이스.md`: `person_period.parquet`(`n_prior_periods`)·`global_dataset.parquet`/`local_dataset.parquet`(`sample_weight`) 스키마, §3 함수 계약, 변경 이력 표, 작성 출처 표를 전부 갱신(AGENTS.md §10 연동 체크).

## 검증 (내가 직접 확인한 것)
- 수정한 8개 Python 파일 전부 `ast.parse`로 문법 검증 통과.
- `code/contracts.py`에서 `DatasetBundle` 생성 지점을 `grep`으로 전수 조사해 4곳(`build_global.py`, `build_local.py`, `split.py`, `run_pipeline.py`) 모두 `sample_weight` 필드를 채우도록 수정했음을 확인.
- ⚠️ **raw 데이터로 파이프라인을 실제 재실행하지 않았다** — 로컬에 YP2021 원자료가 없어 이번 세션에서는 불가능. `n_prior_periods`/`sample_weight` 실제 값 분포, `--run-modeling` 전체 경로 동작은 검증되지 않음.

## 남은 것 / 막힌 것
- **raw 데이터 있는 환경에서 `python -m code.pipeline.run_pipeline --raw-zip ... --run-modeling --tune` 재실행 필요** — 특히 `sample_weight`가 `model__sample_weight`로 정상 라우팅되는지, `n_prior_periods`가 `features.yaml` 등록으로 실제 X에 들어가는지 확인.
- `tune_model`의 `sample_weight_train`이 GridSearchCV 검증 fold 채점(scoring)에는 반영되지 않는다는 점 — 학습에만 적용할지, scoring까지 가중치 반영할지는 아직 팀이 확정하지 않음(`06-인터페이스.md`에 ⬜ 표시해둠).
- 이 브랜치(`feat/wjdwlsah-oversampling-mitigation`)와 `feat/wjdwlsah-major-group-backfill` 둘 다 push 전 — GitHub 장애(2026-08-17)는 복구 확인함, push·PR 생성은 다음 단계.
