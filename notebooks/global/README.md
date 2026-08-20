# global — Global 모델링 실행 Notebook

## 무엇

전체 미취업 청년 Person-Period를 사용하는 Global 모델의 단계별 확인 Notebook을 둔다.

## 왜

Global 모델은 [14번 단계별 실행 흐름](../../plan/details/14-Global-모델링-단계별-실행흐름.md)에 따라 사람의 확인을 거쳐 다음 단계로 넘어간다. 각 Notebook이 어느 단계의 확인인지 분명히 남기기 위해 분리한다.

## 규칙

- `00_modeling_check.ipynb`는 Stage 0의 데이터·split 확인용이며 모델 학습·선택·결과 해석을 하지 않는다.
- `01_first_model.ipynb`는 Stage 1의 42개 Feature Train 내부 LR·XGBoost 비교용이다. 고정 Test Dataset은 읽지 않으며, OOF 예측·수치·그래프만 만들고 모델 선택·Feature 제거·결과 해석은 하지 않는다.
- `02_feature_selection.ipynb`는 Stage 1의 고정 최적 파라미터와 Global Train만 사용해 CV Permutation Importance, LR coefficient, XGBoost gain/weight, 수치형 상관관계, VIF를 보여 준다. Feature 삭제·추천·최종 목록 생성과 Test Dataset 사용은 하지 않는다.
- `03_second_model.ipynb`는 사람이 확정한 `global_stage2_selected_25` 25개 Feature로 LR/XGBoost를 새로 튜닝하고, 저장된 Stage 1 결과와 CV·OOF 수치만 비교한다. Test 사용이나 최종 모델 선택은 하지 않는다.
- `03_5_final_tuning.ipynb`는 Stage 3 `selected_features.csv`의 같은 25개 Feature와 저장된 Stage 3 파라미터를 기준선으로, 사람이 지정한 제한 LR/XGBoost refinement 및 refined Train OOF threshold 민감도를 실행한다. Test를 읽지 않고, 모델·threshold를 자동 선택하지 않는다.
- 이후 Notebook도 `code/` 공용 함수를 import하며, Test를 Feature·모델 선택에 사용하지 않는다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 폴더 역할·Stage 0 경계 | 사용자 제공 Global 모델링 준비 요구사항을 AI가 폴더 규칙으로 구조화 | ⬜ 미검토 |
| Stage 1 Train 내부 LR·XGBoost 비교 경계 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 1차 모델링 조건** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 2 Feature 분석·사람의 Feature 선택 경계 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 요청** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 3 25개 Feature 재튜닝·1차/2차 비교 조건 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-21 요청** | ✅ 2026-08-21 Kim ByungKyu |
| Stage 3.5 제한 refinement·threshold 민감도·Test 미사용 경계 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-21 요청** | ✅ 2026-08-21 Kim ByungKyu |

- 세션 로그: `작업기록/hanliyagi/20260820-Global-모델링-준비구현.md`
