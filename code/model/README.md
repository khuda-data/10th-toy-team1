# model — 공통 모델 학습·튜닝

Logistic Regression, Decision Tree, Random Forest, XGBoost, LightGBM을 `model_config.yaml` 범위 안에서 학습한다.

튜닝은 SAMPID 기준 `StratifiedGroupKFold`로만 한다. 개별 직군이 탐색 범위나 CV fold 수를 바꾸면 안 된다.

Global과 Local의 공식 비교에는 `model_config.yaml`의 `official_comparison_models`에 등록된 Logistic Regression과 XGBoost만 사용한다. Global은 [14번 단계별 실행 흐름](../../plan/details/14-Global-모델링-단계별-실행흐름.md)의 1차·2차 비교를 먼저 수행하며, Decision Tree·Random Forest·LightGBM은 공통 모듈이 지원하더라도 공식 결과에 섞지 않는다.

XGBoost의 `scale_pos_weight=train_negative_positive_ratio` 후보는 `GridSearchCV`의 각 Train fold에서 해당 fold의 negative/positive 비율로 계산된다. 전체 Train 비율 하나를 재사용하지 않는다.

`run_first_stage_modeling()`은 42개 Feature Global Train만 받아 GridSearchCV와 고정 최적 파라미터의 SAMPID 5-fold OOF 예측을 실행한다. Test Dataset과 `sample_weight` 입력을 받지 않는다. `save_first_stage_artifacts()`은 모델별 OOF 확률뿐 아니라 비교 요약과 최적 파라미터를 함께 저장하며, Stage 2는 `load_first_stage_best_params()`로 이를 복원해 GridSearch를 다시 실행하지 않는다.

`run_global_cv_modeling()`은 같은 GridSearchCV·Train-fold-only 전처리·고정 파라미터 OOF 로직을 선택된 Global Feature set에도 재사용한다. Stage 3는 이 함수를 호출해 사람이 확정한 25개 Feature로 새로 튜닝한다. `save_modeling_artifacts()`은 단계별 OOF·summary·best_params·fold F1을 저장한다.

Stage 3.5의 `final_tuning.py`는 기본 탐색 범위를 바꾸지 않고 사람이 지정한 제한 Grid만 `tune_model(param_grid=..., estimator_params=...)`으로 실행한다. XGBoost는 GridSearchCV를 병렬화할 때 내부 `n_jobs=1`을 적용하고, 매 fit fold에서 `scale_pos_weight=train_negative_positive_ratio` marker를 기존 방식으로 계산한다. `threshold.py`는 Train OOF 확률만 받아 threshold별 지표를 계산하며 threshold를 자동으로 바꾸지 않는다.

`final_evaluation.py`는 Stage 1/3.5 artifact에서 네 고정 후보를 복원하고, Stage 4 Notebook 실행 시에만 Train 전체 fit·고정 Test 예측·결과 저장을 수행한다. Test 결과를 이용한 재튜닝·재선택 기능은 제공하지 않는다.

`locked_sensitivity.py`는 Stage 3.5 `final_refined_params.json`의 LR/XGBoost parameter를 변경 없이 읽어 반복관측 sensitivity의 Train OOF를 만든다. 새 tuning과 Test 접근은 하지 않으며, C 방식의 `sample_weight`는 각 CV fold의 fit에만 전달하고 OOF 평가는 비가중으로 계산한다.

`run_weighted_class_locked_oof()`는 C-old를 바꾸지 않는 C-revised 전용 opt-in helper다. 매 CV fold의 training rows만 사용해 `W_pos`·`W_neg`를 계산하고, LR에는 weighted-mass `class_weight` dictionary를, XGBoost에는 weighted-mass `scale_pos_weight`를 적용한다. validation 행의 target·weight·분포는 이 계산에 포함하지 않는다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 | AI가 사용자 제공 프로토콜의 모델 규칙을 모듈 역할로 정리 | ⬜ 미검토 |
| Global·Local 공식 LR/XGBoost 비교 대상과 Global 단계별 실행 순서 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 모델링 흐름** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 1의 42개 Feature·Train-only·OOF 비교 조건 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 1차 모델링 조건** | ✅ 2026-08-20 Kim ByungKyu |
| XGBoost fold별 `scale_pos_weight` 구현 | 사용자 요구사항을 AI가 재사용 모듈로 구현 | ⬜ 미검토 |
| Stage 1 artifact 저장·Stage 2 고정 파라미터 재사용 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 요청** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 3 선택 Feature 재튜닝·1차/2차 비교 조건 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-21 요청** | ✅ 2026-08-21 Kim ByungKyu |
| Stage 3.5 제한 LR/XGB refinement와 OOF threshold 민감도 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-21 요청** | ✅ 2026-08-21 Kim ByungKyu |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
