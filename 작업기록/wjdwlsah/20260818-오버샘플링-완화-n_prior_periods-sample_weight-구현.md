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

## 추가 (같은 세션, 이어서)
- `업데이트.md` 최상단에 이 작업 항목 추가, `회의기록/안건.md`에 `sample_weight` scoring 반영 여부(AGENTS.md §2-7 — 팀 결정 필요 사안) 등록(AGENTS.md §13, pre-push 훅 통과 요건).

## 추가 (2026-08-18, 같은 날 이어서) — n_prior_periods·sample_weight 독립 분리 + raw 데이터 실 검증

### 지침 (내가 시킨 것)
- 위 구현은 `n_prior_periods`(Feature)와 `sample_weight`(학습 가중치)가 항상 같이 켜지는 구조였는데, "①기존 42개 Feature만(가중치 X) ②+n_prior_periods만(가중치 X) ③+sample_weight만(Feature X)" 세 조건을 다른 건 전부 고정한 채 비교·대조하고 싶다고 요청. PR #4(major_group 백필)까지 머지된 상태를 전제로, 두 장치를 서로 독립적으로 켜고 끌 수 있게(예: `use_n_prior_periods`/`use_sample_weight`) 고쳐 달라고 지시. `n_prior_periods`가 그냥 `features.yaml`의 `features:`에 있으면 기존 42개 모델도 자동으로 43개가 돼버리니, 기본 42개 모델의 재현성을 반드시 지키라고 명시. 세 모델은 산출물을 독립적으로 취급하고 이름으로 구분해 달라고 요청.

### AI가 한 일
- `code/config/features.yaml`: `n_prior_periods`를 `features:`에서 빼서 별도 `optional_features:` 섹션으로 이동 — 명시적으로 요청하지 않으면 X에 안 들어감.
- `code/preprocess/build_features.py`: `feature_columns()`/`feature_columns_by_type()`/`build_features()`에 `extra_features` 인자 추가. 기본값(`None`)은 기존 42개와 완전히 동일, `extra_features=["n_prior_periods"]`로 명시했을 때만 43개로 확장.
- `code/preprocess/preprocess.py`: `build_preprocessor()`의 numeric/categorical 컬럼 목록을 `X_train.columns`에 실제로 있는 것만 쓰도록 변경 — `train_model`/`tune_model`에 별도 플래그를 안 넘겨도 X의 실제 컬럼 구성에 자동으로 맞춰짐.
- `code/pipeline/build_global.py`, `code/pipeline/build_local.py`: `use_n_prior_periods: bool = False` 인자 추가, `build_features(..., extra_features=...)`로 라우팅.
- `code/pipeline/run_pipeline.py`: 전면 개편 —
  - `experiment_name(use_n_prior_periods, use_sample_weight)`로 네 조합(`baseline_42features`/`with_n_prior_periods`/`with_sample_weight`/`with_n_prior_periods_and_sample_weight`) 이름 결정.
  - `_fit_model(..., use_sample_weight: bool = False)` — 기본값이 `False`로 바뀌어, 명시적으로 켜지 않으면 `sample_weight_train=None`(가중치 없이 학습).
  - 결과 저장 경로를 `data/result/` → `data/result/<experiment>/`로 전부 분리(datasets/splits/metrics/feature_importance/models).
  - `joblib.dump`로 Global/직군별 Local 학습 Pipeline을 `<experiment>/models/*.joblib`에 저장 — 이전엔 best_params.json만 있고 실제 모델 객체는 저장 안 됐음(이번에 새로 추가).
  - `--use-n-prior-periods`/`--use-sample-weight`/`--compare-oversampling-mitigation`(raw를 한 번만 읽어 세 실험을 순서대로 다 실행) CLI 옵션 추가.
  - metrics.csv/feature_importance.csv/best_params.json에 `experiment` 컬럼 추가.
- `code/requirements.txt`: `joblib` 추가(모델 직렬화용, 실제로는 scikit-learn 종속으로 이미 설치돼 있었음).
- `plan/details/06-인터페이스.md`: 파일 경로를 `<experiment>` 하위 구조로 전부 갱신, §3 함수 계약에 `use_n_prior_periods`/`use_sample_weight`/`experiment_name`/`_fit_model` 추가, 변경 이력·작성 출처 표 갱신(이번 분리는 AI 제안이 아니라 **사용자가 직접 설계·지시**했음을 명시).

### 검증 (내가 직접 확인한 것)
- 수정한 6개 Python 파일 전부 `ast.parse` 문법 검증 통과.
- **이번엔 raw 데이터가 있었다** — `C:\Users\USER\Documents\KHUDA_10기\Toy_project\데이터셋`에서 발견, PR #4 검증 때 이미 `YP2021_w01~w04.xlsx` 표준화 결과를 캐싱해둠. PR #4(`feat/wjdwlsah-major-group-backfill`)를 로컬에서만 이 브랜치에 병합한 임시 테스트 브랜치로 실제 raw 데이터 기준 검증을 진행함 (상세 결과는 아래 별도 기록 참조).
- ⚠️ 이 로그 작성 시점 기준 push는 아직 안 함 — 실 데이터 검증 결과를 사용자에게 보고한 뒤 진행.
