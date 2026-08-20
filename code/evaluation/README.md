# evaluation — 공통 평가·중요도

F1을 주 지표로 Accuracy, Precision, Recall, ROC-AUC와 혼동행렬을 함께 계산한다. Importance는 Test Dataset의 원 Feature 단위 Permutation Importance로 통일한다.

`generate_oof_predictions()`은 Train 내부 `StratifiedGroupKFold`로 OOF 예측을 만들고, `calculate_binary_metrics()`은 threshold=0.5의 Accuracy·Precision·Recall·F1·ROC-AUC·혼동행렬을 확률 예측에서 계산한다. `bootstrap_confidence_intervals()`은 고정 Test 예측을 SAMPID 단위로 1,000회 복원추출해 95% 신뢰구간을 계산한다. 이 함수들은 정해진 단계의 결과표·진단 자료를 만드는 기능이다.

Test 성능을 보고 모델·파라미터를 다시 고르지 않는다.

`feature_analysis.py`는 Global Stage 2 전용의 Train 내부 분석을 제공한다. `run_cv_feature_analysis()`는 Stage 1의 고정 최적 파라미터로 SAMPID 5-fold를 다시 학습하고, 각 validation fold에서 원 Feature 단위 F1 Permutation Importance를 계산한다. Logistic Regression 계수와 XGBoost gain/weight는 전처리 후 dummy 열을 원 Feature로 묶은 보조 자료다. `numeric_correlation_analysis()`와 `calculate_numeric_vif()`도 Global Train만 받고, VIF는 One-Hot 범주형·이진/저변동 변수를 기계적으로 포함하지 않는다. 어떤 함수도 Feature 삭제나 모델 선택을 수행하지 않는다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 | AI가 사용자 제공 프로토콜의 평가 규칙을 모듈 역할로 정리 | ⬜ 미검토 |
| OOF·SAMPID bootstrap 기능 | 사용자 제공 모델링 준비 요구사항을 AI가 코드 인터페이스로 구현 | ⬜ 미검토 |
| Stage 1 OOF 지표·고정 파라미터 OOF 조건 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 1차 모델링 조건** | ✅ 2026-08-20 Kim ByungKyu |
| Stage 2 Train 내부 Feature 분석·사람의 Feature 선택 경계 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 요청** | ✅ 2026-08-20 Kim ByungKyu |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
