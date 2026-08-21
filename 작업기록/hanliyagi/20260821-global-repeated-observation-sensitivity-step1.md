# 2026-08-21 Global 반복관측 Sensitivity Analysis Step 1

- 도구/모델: Codex / GPT-5
- 브랜치: main (Notebook·공용 감사 보조 코드 작업)

## 지침 (내가 시킨 것)

- "[Global Repeated-Observation Sensitivity Analysis — Step 1]" 지시: 공식 Global Stage 1~4 결과는 변경하지 않고, 기존 Stage 3의 `selected_features.csv` 25개를 source of truth로 삼아 B(`n_prior_periods`)와 C(`sample_weight`) 데이터 구성을 점검하는 Notebook 두 개를 분리해 작성.
- 실제 Notebook 실행·실제 데이터 결과 확인·모델 fit/CV/Test 접근·Test 예측 및 metric 계산은 하지 않으며, 사람만 실행·판단.

## AI가 한 일

- `notebooks/global/05_1B_n_prior_periods_audit.ipynb` 생성: 고정 Train SAMPID만 대상으로 25개 Stage 3 Feature + `n_prior_periods`(26개) 구조, 분포·사람별 반복행 관계·연대기 사례·assertion을 준비.
- `notebooks/global/05_1C_sample_weight_audit.ipynb` 생성: 25개 Stage 3 Feature를 유지하고 Global Train 안의 SAMPID별 `1 / n_i` 가중치 분포·합계·target class별 raw/weighted total·assertion을 준비.
- `code/pipeline/audit.py` 추가: 저장된 Global Dataset을 기존 split으로 Train만 선택하고, Stage 3 `selected_features.csv`를 읽고, Person-Period의 기존 `n_prior_periods`를 행 키로 연결하며, Train 기준 sample weight를 계산하는 공통 함수 제공.
- GitHub 최신 `main`(`b55c33f`)을 fast-forward로 동기화했다. 이에 따라 기존 Global Stage 0~4 Notebook과 공식 Stage 3 `selected_features.csv`가 로컬에 반영됐다.
- 최신 main의 `code.pipeline.saved_results.load_saved_global_train()`을 audit 보조 함수가 재사용하도록 연결했다. Test DatasetBundle은 만들지 않는다.
- Notebook 생성 직후 코드 셀의 줄바꿈이 문자 `\\n`으로 저장된 문제를 수정했다. 두 Notebook의 모든 코드 셀을 Python AST로 문법 검사했으며, 이 검사는 셀을 실행하지 않는다.
- 수정 커밋 푸시 시 팀 훅이 업데이트 알림을 요구해 `업데이트.md`에 오류 수정 안내를 추가했다.
- 두 Audit Notebook의 모든 Markdown·코드 셀을 정상 줄바꿈으로 다시 정리하고, 입력·Feature 계약·분포·사람별 점검·assertion 순서의 Markdown 구분선을 추가해 가독성을 높였다. Notebook 실행 없이 JSON·Python AST 검증만 수행했다.
- Step 2 요청에 따라 `05_2B_n_prior_periods_locked_model.ipynb`, `05_2C_sample_weight_locked_model.ipynb`와 `code/model/locked_sensitivity.py`를 추가했다. Stage 3.5 `final_refined_params.json`을 동결 parameter source of truth로 읽고, 새 tuning 없이 Train Group OOF·비가중 지표·전용 결과 저장·A 비교표/그래프를 준비한다.
- 05_2B 실행 중 최신 pandas의 Categorical 열에 희소 범주 `Other`를 대입할 때 `LossySetitemError`가 발생한 것을 확인했다. `RareCategoryGrouper.transform()`이 대입 전 해당 열을 object로 바꾸도록 수정했으며, 합성 범주형 DataFrame으로만 함수 단위 검증했다. 실제 Global 데이터·모델 fit·CV는 실행하지 않았다.
- ROC 비교 그래프 셀에서 설치된 scikit-learn이 직접 `color=` 인자를 지원하지 않아 발생한 `TypeError`를 확인했다. 두 Step 2 Notebook에서 지원되는 `curve_kwargs={"color": ...}` 방식으로 변경하고 저장된 실행 output·traceback을 제거했다. Notebook은 다시 실행하지 않았다.
- Step 2C Revised 요청에 따라 `notebooks/global/05_2C_sample_weight_weighted_class_locked_model.ipynb`를 새로 만들었다. 기존 C-old Notebook과 결과 경로는 수정하지 않는다. 이 Notebook은 Global Train의 같은 SAMPID-level `1 / n_i` sample weight를 사용하되, 각 `StratifiedGroupKFold` training fold 안에서만 `W_pos`·`W_neg`를 계산한다.
- `code/model/locked_sensitivity.py`에 C-revised 전용 opt-in helper를 추가했다. LR은 `W_total/(2*W_neg)`, `W_total/(2*W_pos)` dictionary로 기존 `class_weight="balanced"`를 대체하고, XGBoost는 `W_neg/W_pos`으로 기존 raw-row `scale_pos_weight`를 대체한다. 두 모델 모두 training fold fit에만 SAMPID sample weight를 전달하며, validation/OOF metric은 비가중으로 남긴다.
- C-revised 전용 저장 경로와 summary·fold F1·weight audit·OOF·confusion matrix 파일 생성을 Notebook에 준비했다. 실제 Notebook, 실제 Global Train CV, OOF 생성, Test 접근은 실행하지 않았다.
- C-revised 비교 셀에서 A `final_tuning_summary.csv`에 Stage 3와 Stage 3.5가 함께 있어 모델명이 중복되는 경우를 처리하도록 수정했다. A 비교 행은 명시적으로 `stage_3_5`만 선택하며, 중복이 남으면 오류를 내도록 했다.

## 검증 (내가 직접 확인한 것)

- 두 `.ipynb` 파일 JSON 형식 검증 통과.
- `code/pipeline/audit.py` Python 문법 컴파일 및 import 수준 검증 통과.
- C-revised 공용 helper 문법 컴파일·import와 합성 `y`/`sample_weight`의 weighted class mass 함수 단위 검증만 수행했다.
- Notebook 실행, 실제 데이터 읽기, assertion 실행, 모델 fit/CV, Test 예측·metric 계산은 하지 않았다.

## 남은 것 / 막힌 것

- 사람이 각 Audit Notebook을 실행해 실제 분포와 assertion 결과를 확인하고 판단해야 한다.
- 사람이 C-revised Notebook을 실행해 C-old와의 비교표·fold별 class-weight audit을 확인하고 결과를 판단해야 한다.
