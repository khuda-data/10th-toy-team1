# evaluation — 공통 평가·중요도

F1을 주 지표로 Accuracy, Precision, Recall, ROC-AUC와 혼동행렬을 함께 계산한다. Importance는 Test Dataset의 원 Feature 단위 Permutation Importance로 통일한다.

`generate_oof_predictions()`은 Train 내부 `StratifiedGroupKFold`로 OOF 예측을 만들고, `bootstrap_confidence_intervals()`은 고정 Test 예측을 SAMPID 단위로 1,000회 복원추출해 95% 신뢰구간을 계산한다. 둘 다 모델 선택이 아닌 정해진 단계의 결과표·진단 자료를 만드는 기능이다.

Test 성능을 보고 모델·파라미터를 다시 고르지 않는다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 | AI가 사용자 제공 프로토콜의 평가 규칙을 모듈 역할로 정리 | ⬜ 미검토 |
| OOF·SAMPID bootstrap 기능 | 사용자 제공 모델링 준비 요구사항을 AI가 코드 인터페이스로 구현 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
