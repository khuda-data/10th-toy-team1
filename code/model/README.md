# model — 공통 모델 학습·튜닝

Logistic Regression, Decision Tree, Random Forest, XGBoost, LightGBM을 `model_config.yaml` 범위 안에서 학습한다.

튜닝은 SAMPID 기준 `StratifiedGroupKFold`로만 한다. 개별 직군이 탐색 범위나 CV fold 수를 바꾸면 안 된다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 | AI가 사용자 제공 프로토콜의 모델 규칙을 모듈 역할로 정리 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
