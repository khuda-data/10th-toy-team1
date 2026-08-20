# data/result — 실험별 공용 결과물

**통합 코드(`code/`)가 만든 팀 공용 결과물만** 둔다. 개인 실험의 중간 산출물은 자기 `sandbox/<git아이디>/`에 둔다.

원칙: **코드로 다시 만들 수 있을 것** — 원자료와 개인 단위로 연결 가능한 Dataset은 public 저장소에 올리지 않는다.

## 폴더 구조

세 비교 실험은 서로 덮어쓰지 않도록 `data/result/<experiment>/` 아래에 각각 저장된다.

| 실험 폴더 | 조건 | Feature 수 | 학습 가중치 |
|---|---|---:|---|
| `baseline_42features` | 기본값 | 42개 | 미반영 |
| `with_n_prior_periods` | `n_prior_periods` 포함 | 43개 | 미반영 |
| `with_sample_weight` | 기본 Feature | 42개 | `sample_weight` 반영 |

각 실험 폴더는 아래 구조를 가진다.

| 경로 | 내용 | Git 처리 |
|---|---|---|
| `datasets/person_period.parquet` | Person-Period 기본 행 | ignore |
| `datasets/global_dataset.parquet` | Global 모델용 Feature·target·메타데이터 | ignore |
| `datasets/local_dataset.parquet` | 희망직군이 붙은 Local 모델용 행 | ignore |
| `splits/split_ids.csv` | SAMPID 기준 Train/Test 소속 | ignore |
| `metrics/metrics.csv` | 모델·직군별 평가 지표 | 필요 시 공용 결과물로 커밋 |
| `feature_importance/feature_importance.csv` | 원 Feature 단위 Permutation Importance | 필요 시 공용 결과물로 커밋 |
| `models/best_params.json` | CV가 고른 공통 파라미터 | 필요 시 공용 결과물로 커밋 |
| `models/*.joblib` | 학습된 모델 객체 | ignore |
| `modeling/stage_1/<model>_oof_predictions.parquet` | Global Stage 1 Train 내부 OOF 확률·fold·SAMPID | ignore |
| `modeling/stage_1/first_stage_summary.csv`, `best_params.json` | Stage 1 비교표와 Stage 2 재사용용 최적 파라미터 | ignore |
| `modeling/stage_1/fold_f1.json` | Stage 1 모델별 5개 CV fold F1 | ignore |
| `modeling/stage_2/*.csv` | Global Train 내부 Feature 분석표·상관·VIF·종합표 | ignore |
| `modeling/stage_3/<model>_oof_predictions.parquet`, `second_stage_summary.csv`, `best_params.json`, `fold_f1.json`, `selected_features.csv` | Global Stage 3의 25개 Feature CV·OOF·파라미터·선택 목록 | ignore |

파일별 컬럼·타입은 [`../../plan/details/06-인터페이스.md`](../../plan/details/06-인터페이스.md)가 정본이다.

## 재생성 방법

원자료 zip은 Git에 넣지 않는다. 제공받은 로컬 `YP2021_EXCEL_*.zip`의 경로만 전달한다.

세 실험의 구조 산출물만 만들려면 아래를 실행한다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/로컬/경로/YP2021_EXCEL_0227.zip" \
  --compare-oversampling-mitigation
```

세 실험 모두를 학습·평가까지 실행하려면 `--run-modeling`을 추가한다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/로컬/경로/YP2021_EXCEL_0227.zip" \
  --run-modeling \
  --compare-oversampling-mitigation
```

명령은 원자료를 한 번만 읽고 위 표의 세 폴더를 순서대로 만든다. `--compare-oversampling-mitigation`은 `--use-n-prior-periods`, `--use-sample-weight`와 함께 쓸 수 없다. 두 옵션을 개별로 지정할 때는 해당 조건 하나만 실행한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 기존 코드의 실제 결과 경로와 사용자 요청에 맞춰 보관·실행 안내를 정리했다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 실험별 경로·생성 파일 | PR #5 코드 계약을 AI가 문서화 | ⬜ 미검토 |
| 공개 저장소 보관 규칙 | 기존 저장소 규칙을 AI가 새 경로에 적용 | ⬜ 미검토 |
| 세 실험 실행 명령 | PR #5 CLI 동작을 AI가 문서화 | ⬜ 미검토 |
| `modeling/stage_1/` Train OOF 보관 경로 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 1차 모델링 조건** | ✅ 2026-08-20 Kim ByungKyu |
| `modeling/stage_2/` Train 내부 Feature 분석 보관 경로 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 요청** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 3 25개 Feature 재튜닝 산출물 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-21 요청** | ✅ 2026-08-21 Kim ByungKyu |

- 세션 로그: `작업기록/hanliyagi/20260819-PR5-충돌해결-결과경로-정리.md`
