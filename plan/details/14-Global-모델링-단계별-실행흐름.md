# 14. Global 모델링 단계별 실행 흐름

> 이 문서는 Global 모델을 **한 번에 결론내지 않고**, 단계마다 사람이 결과를 확인하고 다음 단계로 넘어가기 위한 실행 순서다. 분석대상·42개 기본 Feature·SAMPID 기준 분할 등 고정 조건은 [11번 공통 프로토콜](11-YP2021-공통-전처리-모델링-프로토콜.md)을 따른다.

## 1. 역할 분리

| 담당 | 맡는 일 | 맡지 않는 일 |
|---|---|---|
| `.py` | 재사용 가능한 데이터 확인·학습·교차검증(CV)·평가·그래프용 결과표 계산 | 결과를 보고 Feature나 최종 모델을 고르는 판단 |
| `.ipynb` | `.py` 기능을 실제 실행하고, 표·그래프를 만들어 결과를 관찰 | 같은 계산 로직을 Notebook마다 따로 구현하거나 Test를 보고 재선택하는 일 |
| 사람 | 단계별 결과 해석, 사용할 Feature 선택, 최종 Global 모델 판단 | — |

- 공통으로 재사용할 기능은 `code/model/`, `code/evaluation/` 등 공용 모듈에 둔다. 개인 실행 Notebook과 중간 그림·표는 `sandbox/<git아이디>/`에서 만든다.
- Notebook에는 실행 날짜, 사용한 Feature 목록, 모델명, 결과 파일 경로를 남긴다. 그래야 다음 사람이 같은 조건으로 다시 실행할 수 있다.
- 결과 해석, Feature를 포함·제외한 이유, 모델을 선택한 이유는 대원칙상 **사람이 직접 작성**한다.

## 2. 공통 보호 규칙

- 기준 실험은 `baseline_42features`, 즉 현재 42개 기본 Feature를 사용한다. `n_prior_periods`나 `sample_weight` 같은 별도 실험은 이 1차·2차 비교와 섞지 않는다. 포함 여부는 사람이 별도로 결정한 뒤 독립 실험으로 기록한다.
- 고정 Test는 Stage 4 전까지 열어 보지 않는다. Stage 1~3의 CV, Feature Importance, 상관계수, VIF는 모두 **Train 데이터 내부**에서 계산한다.
- CV의 fold, 전처리 fit, 튜닝은 [11번 프로토콜](11-YP2021-공통-전처리-모델링-프로토콜.md)과 `code/config/model_config.yaml`의 고정 조건을 따른다. 같은 `SAMPID`가 학습과 검증에 겹치지 않아야 한다.
- Stage 4 결과를 보고 Feature·하이퍼파라미터·모델을 다시 고르지 않는다. 다시 고르려면 새 실험으로 돌아가 Stage 1부터 진행한다.

## 3. 단계별 실행

```text
[0] 환경·프로토콜 정리
          ↓
[1] 1차 모델 (LR / XGBoost, 42 Feature) → CV 시각화 → 사람 판단
          ↓
[2] 주요 Feature·공선성 분석 → 시각화 → 사람의 Feature 선택
          ↓
[3] 2차 모델 (선택 Feature) → 1차 vs 2차 CV 비교 → 사람의 후보 판단
          ↓
[4] 고정 Test 최종 비교 → 진단 그래프·Bootstrap CI → 사람의 최종 Global 모델 판단
```

### [0] 모델링 환경·프로토콜 정리

**`.py` / `.ipynb`에서 할 일**

- Global Dataset, 42개 Feature 목록, `SAMPID` 기준 Train/Test split, random seed와 결과 저장 경로를 확인한다.
- Logistic Regression(LR)과 XGBoost의 공통 학습·CV 입력 및 출력 형식을 맞춘다.
- 어떤 결과표와 그래프를 각 단계에서 낼지 Notebook에 준비한다.

**사람 확인 후 다음으로 넘어갈 것**

- 이 단계의 기준 데이터·분할·42개 Feature가 현재 프로젝트의 정본과 일치하는지 확인한다.

### [1] 1차 모델 구축 — 전체 42 Feature

**실행**

- Logistic Regression과 XGBoost를 같은 42개 Feature로 학습·CV한다.
- Notebook에서 모델별 CV 성능 분포와 fold별 점수를 표·그래프로 보여 준다.

**사람 판단 지점**

- CV 결과가 정상적으로 비교 가능한지, 다음 Feature 분석을 진행할지 직접 판단한다.
- 이 시점에는 Test 성능을 보지 않는다.

### [2] 주요 Feature 선정 + 공선성 분석

**실행**

- Train 내부 CV 결과를 이용해 Permutation Importance, LR coefficient, XGBoost built-in importance를 정리한다.
- 수치형 Feature의 Correlation과 VIF(분산팽창계수)를 계산해 공선성 후보를 표시한다.
- Notebook에서 중요도·계수·상관관계·VIF를 함께 관찰할 수 있게 시각화한다. 범주형 One-Hot 결과를 원 Feature 단위로 어떻게 묶었는지도 표에 명시한다.

**사람 판단 지점**

- 어떤 Feature를 2차 모델에 쓸지, 서로 강하게 겹치는 Feature 중 무엇을 유지·제외할지 사람이 결정한다.
- 선택 이유와 제외한 대안의 한계는 사람이 직접 기록한다. 이 문서는 그 판단을 대신하지 않는다.

### [3] 2차 모델 재학습 — 선택 Feature

**실행**

- 사람이 선택한 Feature만으로 Logistic Regression과 XGBoost를 같은 CV 조건에서 다시 학습한다.
- 1차(42 Feature)와 2차(선택 Feature)의 CV 성능을 같은 표와 그래프에서 비교한다.
- 2026-08-21 사람 확정 입력은 `code/config/features.yaml`의 `feature_sets.global_stage2_selected_25` 25개다. 이 목록은 `YP2021_Stage2_42features_최종_선정표.xlsx`의 사용 목록을 그대로 옮긴 것이며 코드가 추가·제거하지 않는다.

**사람 판단 지점**

- 성능, 안정성, 단순성 등을 직접 보고 Stage 4에 올릴 최종 후보를 판단한다.
- 이 판단 뒤에는 Feature 집합과 후보 모델을 고정한다.

### [4] 최종 Test 성능 비교

**실행**

- 고정 Test에서 다음 네 후보를 같은 기준으로 평가한다.

  | 모델 | Feature 집합 |
  |---|---|
  | LR 1차 | 전체 42 Feature |
  | LR 2차 | 사람이 선택한 Feature |
  | XGB 1차 | 전체 42 Feature |
  | XGB 2차 | 사람이 선택한 Feature |

- 각 후보의 Confusion Matrix, ROC curve, PR curve, 고정 지표와 SAMPID 단위 Bootstrap 95% 신뢰구간을 만든다.
- 최종 후보의 Feature Importance를 정리한다. Importance는 예측에 사용된 상대적 정보일 뿐, 원인 효과를 뜻하지 않는다.

**사람 판단 지점**

- 네 후보의 Test 결과와 진단 그래프를 보고 최종 Global 모델을 결정한다.
- 최종 해석에서는 말할 수 있는 예측 범위와 말할 수 없는 인과적 해석의 경계를 사람이 직접 쓴다.

## 4. 단계 완료 기록

각 Stage가 끝날 때 Notebook 결과와 함께 다음 네 가지를 남긴다.

1. 실행한 코드 버전·데이터셋·Feature 목록
2. 결과표와 그래프의 저장 위치
3. 사람이 내린 판단 원문과 판단 날짜
4. 다음 Stage에 넘긴 고정 입력값

이 기록이 없는 상태에서 다음 Stage로 넘어가지 않는다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 모델 선택·Feature 선택·결과 해석은 사람이 담당한다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| §1~§4의 단계·역할 분리·사람 판단 순서 | **사람(Kim ByungKyu)이 직접 지시** — “모델링 작업은 한 번에 작업을 진행하지 않고 전체 구조에 나와있는 것처럼 각 단계별로 사람의 판단을 하고 나서 다음 단계로 넘어간다.” | ✅ 2026-08-20 Kim ByungKyu |
| §3 Stage 2 선택 Feature 25개 | **사람(Kim ByungKyu)이 제공한 `YP2021_Stage2_42features_최종_선정표.xlsx`의 사용 목록** | ✅ 2026-08-21 Kim ByungKyu |
| 저장소 경로 연결·재현성 기록 형식 | AI가 저장소 규칙에 맞춰 구조화 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260820-Global-모델링-단계별-프로토콜.md`
