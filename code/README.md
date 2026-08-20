# code — YP2021 공통 분석 코드

**무엇**: 원자료를 Person-Period 데이터셋으로 만들고, Global/Local 모델을 같은 조건에서 실행하는 팀 공용 코드다.

**왜**: 각자가 Notebook을 마지막에 합치는 대신, 처음부터 같은 입력·분할·전처리·결과 형식을 사용해 PR만으로 연결하기 위해 만든다.

먼저 [`AGENTS.md`](AGENTS.md)와 [`../plan/details/06-인터페이스.md`](../plan/details/06-인터페이스.md)를 읽는다.

## 구조

| 폴더/파일 | 역할 | 담당자가 채울 부분 |
|---|---|---|
| `pipeline/` | 원자료 읽기, Person-Period, Global/Local, SAMPID split, 실행점 | YP 원문항을 표준 Feature로 바꾸는 source adapter 보완 |
| `preprocess/` | Feature 계약 검증, Train-only 결측·희소범주·인코딩 | 이력형 Feature 누적·특수결측·분기 처리 |
| `model/` | 다섯 공통 모델의 학습·CV 튜닝 | XGBoost fold별 `scale_pos_weight` 처리, 실행 최적화 |
| `evaluation/` | F1 등 공통 지표와 Permutation Importance | OOF 예측·SAMPID bootstrap 95% CI와 Global-vs-Local Δ 지표 |
| `config/` | Feature·KECO·모델 설정 단일 원본 | 팀 합의가 있는 경우에만 갱신 |
| `requirements.txt` | 첫 실행 시 설치할 패키지 | 팀의 실제 실행 환경 확인 후 버전 freeze |

## 실행 흐름

원자료 zip은 Git에 넣지 않는다. 제공받은 `YP2021_EXCEL_*.zip` 경로를 그대로 전달한다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/경로/YP2021_EXCEL_0227.zip"
```

이 명령은 다음 구조 산출물만 만든다.

```text
원자료 → person_period.parquet → global/local_dataset.parquet → split_ids.csv
```

source adapter는 코드북으로 확인된 **기준연도 미취업자 선정·Target·희망직업 이력**을 구현한다. 구직·취업준비 변수는 표본 제한이 아닌 Feature로 남긴다. `features.yaml`의 42개 Feature 매핑은 2026-08-16 기준 전부 완료됐다(`plan/details/12-Global-피처엔지니어링-요약.md` 참고) — `build_features(..., strict=True)`가 이 매핑을 강제하므로, 없는 Feature를 0으로 채워 성능을 내는 상황 자체가 코드로 막혀 있다.

모든 Feature mapping을 마친 지금은 아래처럼 모델을 실행할 수 있다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/경로/YP2021_EXCEL_0227.zip" \
  --run-modeling --model logistic_regression
```

`--tune`은 Train 내부 `StratifiedGroupKFold`만 이용해 공통 탐색 범위를 실행한다. 계산량 때문에 Randomized Search가 필요하면 팀 공통 결정을 먼저 반영한다.

공통 모듈은 다섯 모델을 지원하지만, Global과 Local의 공식 비교에는 `model_config.yaml`의 `official_comparison_models`에 등록된 Logistic Regression과 XGBoost만 사용한다. Global의 실제 실행 순서는 [14번 단계별 실행 흐름](../plan/details/14-Global-모델링-단계별-실행흐름.md)을 따르며, 사람은 단계 사이의 선택을 기록한다.

Stage 0 데이터·split 확인은 [`../notebooks/global/00_modeling_check.ipynb`](../notebooks/global/00_modeling_check.ipynb)에서 한다. 이 Notebook은 저장된 42개 Feature Global Dataset을 읽어 표본·SAMPID 중복·Target·baseline_year·결측률만 확인하며 모델을 학습하거나 결과를 해석하지 않는다.

Stage 1은 [`../notebooks/global/01_first_model.ipynb`](../notebooks/global/01_first_model.ipynb)에서 한다. 이 Notebook은 `baseline_42features`의 고정 Train만 읽어 Logistic Regression·XGBoost의 5-fold F1, OOF 지표와 그래프를 만들고 OOF 확률을 저장한다. 고정 Test Dataset·`n_prior_periods`·`sample_weight`는 사용하지 않는다.

Stage 2는 [`../notebooks/global/02_feature_selection.ipynb`](../notebooks/global/02_feature_selection.ipynb)에서 한다. Stage 1이 저장한 최적 파라미터를 재사용해 GridSearch를 다시 수행하지 않고, Global Train 내부에서 CV Permutation Importance·계수/gain 보조 자료·수치형 상관관계·VIF를 계산한다. 이 단계는 Feature 삭제·추천·최종 목록 생성이나 Test Dataset 사용을 하지 않는다.

Stage 3는 [`../notebooks/global/03_second_model.ipynb`](../notebooks/global/03_second_model.ipynb)에서 한다. 사람이 확정한 `features.yaml`의 `global_stage2_selected_25`만 선택한 뒤, 기존의 공통 Global CV 함수로 LR/XGBoost를 처음부터 다시 튜닝한다. Stage 1의 최적 파라미터는 재사용하지 않으며, 저장된 Stage 1 결과와 Train 내부 CV·OOF 수치만 비교한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 분석 기준은 사용자가 제공한 프로토콜에서 가져왔으며, 구현 상태 설명은 AI가 작성했다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 구조·실행 안내 | AI가 공통 코드 뼈대를 설명 | ⬜ 미검토 |
| Person-Period·분할·전처리·평가 기준 | **사용자 제공 YP2021 공통 전처리·모델링 프로토콜 v1.3** | ✅ 2026-08-14 검토 완료 |
| Global·Local 공식 LR/XGBoost 비교 대상과 Global 단계별 실행 순서 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 모델링 흐름** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 1 42개 Feature Train 내부 비교·OOF 보관 조건 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 1차 모델링 조건** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 2 Train 내부 Feature 분석·사람의 Feature 선택 경계 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 요청** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 3 선택 25개 Feature·재튜닝·1차/2차 비교 조건 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-21 요청** | ✅ 2026-08-21 Kim ByungKyu |
| OOF·bootstrap·저장 Dataset/split 점검·Stage 0 Notebook | 사용자 제공 모델링 준비 요구사항을 AI가 구현 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
