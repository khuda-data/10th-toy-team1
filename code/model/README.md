# model — 공통 모델 학습·튜닝

Logistic Regression, Decision Tree, Random Forest, XGBoost, LightGBM을 `model_config.yaml` 범위 안에서 학습한다.

튜닝은 SAMPID 기준 `StratifiedGroupKFold`로만 한다. 개별 직군이 탐색 범위나 CV fold 수를 바꾸면 안 된다.

Global과 Local의 공식 비교에는 `model_config.yaml`의 `official_comparison_models`에 등록된 Logistic Regression과 XGBoost만 사용한다. Global은 [14번 단계별 실행 흐름](../../plan/details/14-Global-모델링-단계별-실행흐름.md)의 1차·2차 비교를 먼저 수행하며, Decision Tree·Random Forest·LightGBM은 공통 모듈이 지원하더라도 공식 결과에 섞지 않는다.

XGBoost의 `scale_pos_weight=train_negative_positive_ratio` 후보는 `GridSearchCV`의 각 Train fold에서 해당 fold의 negative/positive 비율로 계산된다. 전체 Train 비율 하나를 재사용하지 않는다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 | AI가 사용자 제공 프로토콜의 모델 규칙을 모듈 역할로 정리 | ⬜ 미검토 |
| Global·Local 공식 LR/XGBoost 비교 대상과 Global 단계별 실행 순서 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 모델링 흐름** | ✅ 2026-08-20 Kim ByungKyu |
| XGBoost fold별 `scale_pos_weight` 구현 | 사용자 요구사항을 AI가 재사용 모듈로 구현 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
