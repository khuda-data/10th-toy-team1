# YP2021 Global 반복관측 민감도 분석 보고서

## `n_prior_periods`와 `sample_weight`를 이용한 B·C 실험

## 1. 보고서 목적

본 보고서는 YP2021 Person-Period 기반 차년도 취업전환 예측에서 **동일한 사람이 여러 Person-Period 행을 가지는 반복관측 구조가 모델 학습에 어떤 영향을 주는지** 확인하기 위해 수행한 추가 민감도 분석을 정리한 문서이다.

공식 Global Model은 이미 다음 조건으로 확정되어 있었다.

- 예측 대상: 기준연도 미취업 청년의 차년도 취업전환 여부
- Positive class: `employment_transition = 1`
- 공식 Feature set: 최종 25개
- 공식 알고리즘: Logistic Regression, XGBoost 비교 후 XGBoost를 최종 Global Model로 사용
- Train 내부 CV: `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)`
- Group: `SAMPID`
- Primary metric: F1
- Threshold: 0.5
- 동일 `SAMPID`가 Train/Test에 동시에 들어가지 않도록 분리

공식 Global Model을 이하 **A(Baseline)**라고 부른다.

A를 만든 뒤 다음과 같은 추가 질문이 생겼다.

> 한 사람은 Person-Period가 1개일 수도 있고 2개 또는 3개일 수도 있는데, 이를 모두 동일한 행으로 학습하면 반복해서 관찰된 사람이 모델 loss에 더 큰 영향을 주는 것은 아닌가?

이를 확인하기 위해 두 가지 대안을 추가로 실험했다.

- **B:** 과거 eligible Person-Period 관측 횟수인 `n_prior_periods`를 Feature로 추가
- **C:** 한 사람의 전체 학습 기여도가 1이 되도록 `sample_weight = 1 / n_i` 적용

이 분석의 목적은 A를 사후적으로 바꾸는 것이 아니라, **A의 반복관측 처리 방식이 결과를 심하게 왜곡하는지 점검하는 민감도 분석**이었다.

---

# 2. 중요한 분석 시점상의 제약

B와 C 실험은 공식 A 모델의 Stage 4 held-out Test 평가가 이미 끝난 뒤 시작되었다.

따라서 B와 C는 다음 원칙으로 분석했다.

- B/C의 Feature 정의, weighting, hyperparameter tuning은 **Global Train 안에서만 수행**
- 기존 Global Test를 B/C 모델 선택에 다시 사용하지 않음
- B/C 결과가 A보다 높게 나오더라도 공식 Global Model을 교체하지 않음
- 모든 B/C 비교는 Train-CV 및 OOF prediction 기반의 **post-hoc sensitivity analysis**로 해석

즉 가장 이상적인 순서인

```text
A/B/C 사전 설계
→ Train-CV에서 세 모델 개발
→ 모두 동결
→ Test 최초 공개
```

가 아니라,

```text
A 개발
→ A Test 평가 완료
→ B/C 민감도 분석 시작
```

순서였기 때문에 B/C 결과는 공식 Test 성능 비교가 아니라 **반복관측 처리 방식의 안정성 확인**에 사용했다.

---

# 3. 비교 전략

## 3.1 A — Baseline

A는 공식 Stage 3.5에서 동결한 25개 Feature 모델이다.

### Logistic Regression

- Feature: 25개
- `C = 0.3`
- `penalty = l1`
- `class_weight = balanced`
- threshold = 0.5

### XGBoost

- Feature: 25개
- `learning_rate = 0.03`
- `n_estimators = 500`
- `max_depth = 3`
- `min_child_weight = 5`
- `subsample = 1.0`
- `colsample_bytree = 0.8`
- `gamma = 0`
- `reg_alpha = 0`
- `reg_lambda = 1`
- `scale_pos_weight = training fold의 negative / positive row 비율`
- threshold = 0.5

A의 Train OOF 성능은 다음과 같다.

| Model | OOF Precision | OOF Recall | OOF F1 | OOF ROC-AUC | OOF AP |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.4218 | 0.5924 | 0.4928 | 0.7022 | 0.4309 |
| XGBoost | 0.4137 | 0.6576 | **0.5079** | 0.7105 | 0.4412 |

이 A를 B/C 민감도 분석의 기준점으로 사용했다.

---

## 3.2 B — `n_prior_periods` 추가

B에서는 A의 25개 Feature는 그대로 유지하고 다음 Feature 하나만 추가했다.

```text
n_prior_periods
= 현재 Person-Period보다 앞서 존재했던 eligible Person-Period의 수
```

가능한 값은 `0`, `1`, `2`이다.

예를 들어:

```text
2021→2022 관측: n_prior_periods = 0
2022→2023 관측: 이전 eligible 관측이 있다면 1
2023→2024 관측: 이전 eligible 관측이 두 개라면 2
```

따라서 B의 Feature 수는 총 **26개**이다.

B의 목적은 반복관측을 제거하거나 가중치를 낮추는 것이 아니라,

> “이 관측이 해당 개인의 패널 내 몇 번째 eligible 관측인가?”

라는 정보를 모델이 직접 활용할 수 있게 하는 것이었다.

`n_prior_periods`는 현재 시점보다 앞선 eligible observation만 사용하며 미래 정보를 Feature로 직접 입력하지 않는다.

---

## 3.3 C — Person-level equal weighting

C에서는 A와 동일한 25개 Feature를 사용하되, 한 사람이 여러 Person-Period를 가지고 있다는 이유로 전체 loss에서 더 큰 비중을 차지하지 않도록 sample weight를 적용했다.

Global Train에서 한 `SAMPID`가 가지는 eligible Person-Period 수를 `n_i`라고 하면:

```text
sample_weight_i = 1 / n_i
```

로 정의했다.

예를 들어:

| 한 사람의 PP 행 수 | 각 행 weight | 사람 전체의 기본 weight 합 |
|---:|---:|---:|
| 1 | 1.0 | 1.0 |
| 2 | 0.5 | 1.0 |
| 3 | 1/3 | 1.0 |

즉 C의 최초 목적은 **1행을 가진 사람과 3행을 가진 사람의 전체 기본 학습 기여도를 동일하게 맞추는 것**이었다.

---

# 4. 전체 실험 흐름

민감도 분석은 다음 순서로 진행했다.

```text
S1. Audit
    ↓
B: n_prior_periods 생성 검증
C: sample_weight 생성 검증

S2. Locked comparison
    ↓
A의 Stage 3.5 hyperparameter를 그대로 사용
B/C 처리 방식만 바꿔 OOF 성능 비교

C-old 문제 발견
    ↓
weighted sample과 raw-row class balancing의 기준 불일치 점검

C-revised 생성
    ↓
weighted class mass 기준으로 class imbalance correction 수정

S3. Strategy-specific retuning
    ↓
B와 C-revised 각각 Train-CV에서 다시 tuning

S4. Diagnostics
    ↓
B: n_prior_periods PI 및 그룹별 성능
C: row-count 그룹별 성능 및 weighting 구조
SAMPID paired bootstrap
```

Test Dataset은 위 과정에서 사용하지 않았다.

---

# 5. S1 — Audit

## 5.1 B Audit

B에서는 `n_prior_periods`가 Person-Period의 시간 순서를 따라 `0/1/2`로 생성되는지 확인했다.

주요 확인 사항은 다음과 같다.

- 미래 Person-Period를 이용해 현재 값을 계산하지 않는지
- 동일 `SAMPID`의 시간 순서가 유지되는지
- 기존 25개 Feature는 변경되지 않는지
- B에서만 `n_prior_periods`가 26번째 predictor로 추가되는지

Audit assertion은 모두 통과했다.

## 5.2 C Audit

C에서는 다음을 확인했다.

- 1행 SAMPID의 row weight = 1
- 2행 SAMPID의 row weight = 0.5
- 3행 SAMPID의 row weight = 1/3
- 동일 SAMPID의 row weight 합 = 1
- validation 정보를 이용하지 않고 training 쪽 weighting만 model fit에 전달
- 평가 metric은 weighted가 아니라 기존과 동일한 unweighted metric 사용

C 역시 audit assertion을 통과했다.

---

# 6. S2 — A 파라미터를 그대로 사용한 Locked Comparison

S2의 목적은 B/C에 유리하도록 다시 tuning하지 않고 **처리 방식 자체를 바꿨을 때 어떤 변화가 생기는지** 확인하는 것이었다.

따라서 B와 C 모두 A Stage 3.5에서 확정된 model parameter를 그대로 사용했다.

## 6.1 B Locked 결과

| Model | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | ROC-AUC | AP |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR | 0.4953 | 0.0209 | 0.4221 | 0.5988 | **0.4952** | 0.7077 | 0.4462 |
| XGB | 0.5076 | 0.0189 | 0.4155 | 0.6524 | **0.5077** | 0.7174 | 0.4568 |

A와 비교하면:

- LR OOF F1: `0.4928 → 0.4952`
- XGB OOF F1: `0.5079 → 0.5077`

즉 A의 parameter를 그대로 적용했을 때 B는 **LR에서 소폭 상승, XGB에서는 사실상 동일한 수준**이었다.

이 단계만으로 `n_prior_periods`가 유용하거나 불필요하다고 결정하지 않고 B에 맞는 재튜닝을 수행하기로 했다.

---

# 7. C-old — 최초 sample_weight 실험과 문제 확인

초기 C는 person-level `sample_weight`를 적용하면서 기존 A의 class imbalance correction도 그대로 유지했다.

### C-old Logistic Regression

```text
sample_weight = 1 / n_i
+
class_weight = "balanced"
```

scikit-learn에서는 두 weight가 loss에서 함께 반영된다.

### C-old XGBoost

```text
sample_weight = 1 / n_i
+
scale_pos_weight = training fold의 raw negative row / raw positive row
```

## 7.1 C-old Locked 결과

| Model | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| LR | 0.4819 | 0.0206 | 0.4231 | 0.5597 | 0.4819 | 0.6912 |
| XGB | 0.4955 | **0.0104** | **0.3587** | **0.8007** | 0.4955 | 0.7022 |

특히 XGBoost에서 다음 변화가 나타났다.

```text
A XGB Recall       = 0.6576
C-old XGB Recall   = 0.8007

A XGB Precision    = 0.4137
C-old XGB Precision= 0.3587
```

Recall이 크게 증가한 대신 Precision이 급격히 감소했다.

이는 단순히 sample weighting의 효과라고 보기 전에, **person-level weighting으로 학습 population의 유효 분포를 바꾼 상태에서 class imbalance correction은 여전히 raw row count를 기준으로 계산한 영향**을 점검할 필요가 있음을 보여줬다.

---

# 8. C-revised — Weighted class mass 기준으로 수정

C의 본래 목적은 반복관측 횟수에 따른 person-level contribution 차이를 확인하는 것이었다.

따라서 sample weight를 적용했다면 class imbalance correction 역시 그 weight가 반영된 population 기준으로 계산하는 것이 더 일관적이라고 판단했다.

각 CV training fold에서:

```text
W_pos = Σ sample_weight_i  (y_i = 1)
W_neg = Σ sample_weight_i  (y_i = 0)
```

를 계산했다.

Validation fold는 이 계산에 사용하지 않았다.

## 8.1 Logistic Regression

기존 `class_weight="balanced"`를 그대로 쓰지 않고 training fold의 weighted mass로 직접 계산했다.

```text
class_weight_0 = (W_pos + W_neg) / (2 × W_neg)
class_weight_1 = (W_pos + W_neg) / (2 × W_pos)
```

그리고 기존 person-level `sample_weight`와 함께 fit에 전달했다.

## 8.2 XGBoost

기존 raw row ratio 대신:

```text
scale_pos_weight = W_neg / W_pos
```

를 각 training fold에서 계산했다.

## 8.3 실제 class ratio 변화

C diagnostics에서 training fold별 raw ratio와 weighted ratio는 대략 다음 수준이었다.

| 기준 | Negative / Positive ratio |
|---|---:|
| Raw row count | 약 2.826 ~ 2.828 |
| Person weight 반영 후 | 약 **1.713 ~ 1.716** |

즉 sample weight를 적용하는 것만으로 positive class의 effective mass가 raw 약 26% 수준에서 **약 36.8% 수준**으로 커졌다.

따라서 raw row 기준의 class correction을 그대로 적용하면 sample weighting 이후의 실제 effective class balance와 맞지 않을 수 있었다.

---

# 9. C-revised Locked 결과

| Model | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | ROC-AUC | Predicted Positive Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR | 0.4819 | 0.0206 | 0.4231 | 0.5597 | 0.4819 | 0.6912 | 0.3457 |
| XGB | 0.4941 | 0.0233 | **0.4099** | **0.6220** | 0.4941 | 0.7022 | 0.3965 |

XGBoost를 C-old와 비교하면:

| Metric | C-old | C-revised |
|---|---:|---:|
| Precision | 0.3587 | **0.4099** |
| Recall | **0.8007** | 0.6220 |
| F1 | 0.4955 | 0.4941 |
| ROC-AUC | 0.7022 | 0.7022 |

C-old에서 나타났던 매우 높은 Recall과 낮은 Precision의 쏠림이 C-revised에서는 상당 부분 완화되었다.

반면 F1 자체는 개선되지 않았다.

따라서 C-old의 Recall 급증을 person-level weighting의 장점으로 해석하지 않고, 이후 C의 공식 sensitivity 정의는 **C-revised**로 고정했다.

Logistic Regression에서는 C-old와 C-revised의 threshold 0.5 기준 성능 지표가 동일하게 나타났다. 코드 검토 결과 C-revised가 C-old를 재호출하거나 `class_weight="balanced"`를 그대로 사용하는 문제는 없었으므로, 이는 weighting 변경이 최종 0.5 분류 결과를 바꾸지 않았거나 매우 유사한 decision을 만든 결과로 보았다.

---

# 10. S3 — B와 C-revised의 Strategy-specific Retuning

S2에서는 A에 최적화된 hyperparameter를 B/C에 그대로 적용했다.

따라서 다음 가능성을 확인할 필요가 있었다.

> B/C 성능이 낮거나 비슷하게 나온 이유가 처리 방식 자체 때문이 아니라 A의 parameter를 그대로 사용했기 때문은 아닌가?

이를 확인하기 위해 B와 C-revised 각각을 **Global Train의 동일 5-fold grouped CV 안에서 별도로 재튜닝**했다.

Feature set과 threshold는 변경하지 않았다.

- B: 26 Features
- C-revised: 25 Features + person-level weighting
- threshold = 0.5
- Test 사용 없음

---

## 10.1 B Tuned parameter

### Logistic Regression

- `C = 0.15`
- `penalty = l1`
- `class_weight = balanced`

### XGBoost

- `learning_rate = 0.02`
- `n_estimators = 500`
- `max_depth = 4`
- `min_child_weight = 7`
- `subsample = 1.0`
- `colsample_bytree = 1.0`
- `gamma = 0.3`
- `reg_alpha = 0.1`
- `reg_lambda = 1`
- `scale_pos_weight = training fold raw negative / positive ratio`

Search boundary에서 선택된 값이 일부 있었지만 sensitivity analysis에서 동일 CV를 반복적으로 확장 탐색하는 것을 피하기 위해 추가 search space 확장은 수행하지 않았다.

## 10.2 B Tuned 결과

| Model | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | ROC-AUC | AP |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR | 0.4968 | 0.0198 | 0.4241 | 0.5992 | **0.4967** | 0.7081 | 0.4457 |
| XGB | **0.5124** | 0.0168 | 0.4194 | 0.6582 | **0.5124** | **0.7173** | **0.4548** |

A 대비 OOF F1 변화는:

- LR: `0.4928 → 0.4967`, **+0.0039**
- XGB: `0.5079 → 0.5124`, **+0.0045**

B Locked 대비로는:

- LR: 약 `+0.0015`
- XGB: 약 `+0.0047`

즉 B에 맞게 다시 tuning하자 두 모델 모두 F1이 조금 상승했다.

다만 개선 폭 자체는 작기 때문에 이를 큰 성능 향상으로 해석하지 않았다.

---

## 10.3 C-revised Tuned parameter

### Logistic Regression

- `C = 0.05`
- `penalty = l2`
- class correction = `weighted_class_balanced`

### XGBoost

- `learning_rate = 0.03`
- `n_estimators = 400`
- `max_depth = 3`
- `min_child_weight = 5`
- `subsample = 0.8`
- `colsample_bytree = 0.8`
- `gamma = 0.3`
- `reg_alpha = 0.1`
- `reg_lambda = 3`
- `scale_pos_weight = training fold weighted W_neg / W_pos`

## 10.4 C-revised Tuned 결과

| Model | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | ROC-AUC | AP |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR | 0.4831 | 0.0215 | 0.4242 | 0.5610 | **0.4831** | 0.6916 | 0.4256 |
| XGB | 0.4967 | 0.0210 | 0.4109 | 0.6280 | **0.4968** | 0.7044 | 0.4347 |

A 대비 OOF F1 변화는:

- LR: `0.4928 → 0.4831`, **-0.0097**
- XGB: `0.5079 → 0.4968`, **-0.0111**

C-revised Locked 대비 tuning 효과는:

- LR: 약 `+0.0012`
- XGB: 약 `+0.0026`

즉 C에 맞춰 다시 tuning하면 성능이 약간 회복되기는 했지만 A를 따라잡지는 못했다.

따라서 C의 낮은 F1을 단순히 **A에 최적화된 parameter를 그대로 사용했기 때문**이라고 설명하기는 어려워졌다.

---

# 11. S4 — B Diagnostics

B의 최종 질문은 두 가지였다.

1. `n_prior_periods`가 실제로 모델에서 사용되는가?
2. A 대비 F1 상승이 안정적인가?

---

## 11.1 `n_prior_periods` 분포와 Positive rate

| `n_prior_periods` | Rows | Positive count | Positive rate |
|---:|---:|---:|---:|
| 0 | 5,737 | 1,507 | 26.27% |
| 1 | 3,842 | 1,007 | 26.21% |
| 2 | 2,346 | 602 | 25.66% |

세 그룹의 raw positive rate는 거의 유사했다.

따라서 단순히

> `n_prior_periods`가 높을수록 취업률이 크게 낮기 때문에 모델이 그 값을 직접 외웠다.

라고 설명할 수 있는 패턴은 나타나지 않았다.

---

## 11.2 `n_prior_periods` Permutation Importance

B Tuned 모델의 Train-CV validation 기반 permutation importance에서 `n_prior_periods`는 다음 위치에 있었다.

### Logistic Regression

- Rank: **3 / 26**
- Importance mean: **0.02249**
- Positive importance fold: **5 / 5**

상위 Feature:

1. `baseline_year`
2. `student_status`
3. **`n_prior_periods`**
4. `age`
5. `recent_job_search`

### XGBoost

- Rank: **6 / 26**
- Importance mean: **0.00981**
- Positive importance fold: **5 / 5**

상위 Feature:

1. `student_status`
2. `months_since_graduation`
3. `age`
4. `recent_job_search`
5. `major_group`
6. **`n_prior_periods`**

두 모델 모두 5개 fold에서 `n_prior_periods`가 양의 permutation importance를 보여, 단순히 Feature를 추가했지만 모델이 무시한 것은 아니었다.

다만 permutation importance는 **예측 기여도**이며 인과효과로 해석하지 않는다.

또한 `n_prior_periods`는 패널의 시간 진행과 구조적으로 연결되어 있으므로 `baseline_year` 등 시간 관련 변수와의 관계를 분리하지 않은 상태에서 독립적인 사회·경제적 효과처럼 해석하지 않는다.

---

## 11.3 `n_prior_periods`별 예측 난이도

B Tuned XGBoost의 그룹별 결과는 다음과 같다.

| `n_prior_periods` | Precision | Recall | F1 | ROC-AUC |
|---:|---:|---:|---:|---:|
| 0 | 0.4439 | 0.6715 | **0.5345** | **0.7408** |
| 1 | 0.4025 | 0.6475 | 0.4964 | 0.6961 |
| 2 | 0.3909 | 0.6429 | **0.4862** | 0.6872 |

Logistic Regression도 유사한 패턴을 보였다.

| `n_prior_periods` | LR F1 |
|---:|---:|
| 0 | **0.5223** |
| 1 | 0.4764 |
| 2 | 0.4682 |

Positive rate 자체는 세 그룹이 약 26%로 비슷했지만, 반복 eligible observation이 많아질수록 F1과 ROC-AUC가 낮아졌다.

따라서 후속 관측이 많이 남는 집단은 현재 Feature들만으로 차년도 취업전환을 구분하기 더 어려운 집단일 가능성이 있다.

다만 이 패턴이 `n_prior_periods` 자체의 효과인지, 후반 baseline year의 특성 또는 반복해서 미취업 상태에 남아 있는 집단 특성 때문인지는 본 실험만으로 분리할 수 없다.

---

## 11.4 B SAMPID Paired Bootstrap

Train OOF prediction을 이용해 `SAMPID` 단위 paired bootstrap 1,000회를 수행했다.

### Logistic Regression

```text
B Tuned - A ΔF1 = +0.00388
95% bootstrap CI = [-0.00155, 0.00923]
```

### XGBoost

```text
B Tuned - A ΔF1 = +0.00450
95% bootstrap CI = [-0.00130, 0.01063]
```

두 모델 모두 point estimate는 B가 높았지만 CI가 0을 포함했다.

따라서 B 결과는:

> **A보다 비슷하거나 소폭 높은 OOF 성능을 보였지만, A 대비 우위가 반복 resampling에서도 일관되게 양수라고 확인되지는 않았다.**

정도로 해석한다.

XGBoost에서 `B Tuned - B Locked`의 ΔF1은 약 `+0.00469`, 95% CI는 `[0.000002, 0.00908]`로 나타나 B 조건 안에서는 재튜닝이 일정 부분 도움이 된 것으로 보였다.

단, 이 bootstrap은 독립 held-out Test에서의 검정이 아니라 **Train OOF sensitivity 결과의 변동성을 보기 위한 보조 분석**이다.

---

# 12. S4 — C Diagnostics

C의 최종 질문은 다음과 같았다.

1. person-level equal weighting이 실제로 어떤 집단의 기여를 바꾸는가?
2. C의 성능 하락이 특정 row-count 그룹에서 발생하는가?
3. A 대비 성능 하락이 반복 resampling에서도 같은 방향인가?

---

## 12.1 SAMPID별 Person-Period 수와 Positive rate

Global Train에서 한 사람이 최종적으로 가지는 eligible Person-Period 수별 분포는 다음과 같았다.

| 한 SAMPID의 PP 수 | Unique SAMPID | PP Rows | Row별 sample weight | Positive rate |
|---:|---:|---:|---:|---:|
| 1 | 1,895 | 1,895 | 1.0 | **69.23%** |
| 2 | 1,496 | 2,992 | 0.5 | **40.17%** |
| 3 | 2,346 | 7,038 | 1/3 | **8.55%** |

이 결과는 C를 해석할 때 매우 중요했다.

Person-Period 수가 적은 집단과 많은 집단의 target distribution이 크게 달랐다.

프로젝트의 eligibility 정의상 baseline에서 취업 상태가 되면 해당 transition에서는 더 이상 at-risk row가 생성되지 않을 수 있기 때문에, **한 사람이 최종적으로 몇 개의 eligible Person-Period를 가지는지는 그 사람의 이후 패널 trajectory와 강하게 연결될 수 있다.**

따라서 `1 / n_i` weighting은 단순히 중복된 관측의 영향을 줄이는 것에 그치지 않고, 서로 다른 취업전환 trajectory를 가진 집단의 상대적 학습 비중까지 변경할 수 있다.

---

## 12.2 C weighting이 class distribution에 미친 영향

Raw row 기준 training fold의 negative / positive ratio는 약 2.83이었다.

Person-level weight를 적용하면 weighted negative / positive ratio는 약 1.71로 감소했다.

즉 person-level equal weighting은 단순한 scale 조정이 아니라 **모델이 학습하는 effective class composition 자체를 크게 변경했다.**

이 점이 C-old에서 raw row 기반 class balancing과 결합되었을 때 Precision/Recall이 크게 이동한 이유를 설명하는 중요한 단서가 되었다.

---

## 12.3 A vs C — Row-count 그룹별 성능

### XGBoost

| PP Rows per SAMPID | A F1 | C Tuned F1 | ΔF1 |
|---:|---:|---:|---:|
| 1 | 0.7410 | **0.7697** | **+0.0287** |
| 2 | **0.5503** | 0.5271 | **-0.0232** |
| 3 | **0.2844** | 0.2238 | **-0.0606** |

### Logistic Regression

| PP Rows per SAMPID | A F1 | C Tuned F1 | ΔF1 |
|---:|---:|---:|---:|
| 1 | 0.7016 | **0.7288** | **+0.0273** |
| 2 | **0.5197** | 0.5004 | **-0.0193** |
| 3 | **0.2891** | 0.2285 | **-0.0606** |

두 알고리즘에서 방향이 매우 유사했다.

- 1-row 집단에서는 C의 F1이 상승
- 2-row 집단에서는 감소
- 3-row 집단에서는 더 크게 감소

XGBoost 3-row 집단의 Recall도:

```text
A Recall       = 0.7143
C Tuned Recall = 0.5133
```

으로 감소했다.

반면 1-row 집단은:

```text
A Recall       = 0.6837
C Tuned Recall = 0.7233
```

으로 증가했다.

즉 C는 단순히 전체 성능을 일정하게 낮춘 것이 아니라, **1-row 사람에 대한 성능을 높이는 대신 반복 eligible observation을 가지는 사람의 성능을 낮추는 방향으로 학습 기여를 재분배**했다.

---

## 12.4 C SAMPID Paired Bootstrap

### Logistic Regression

```text
C Tuned - A ΔF1 = -0.00972
95% bootstrap CI = [-0.01713, -0.00258]
```

### XGBoost

```text
C Tuned - A ΔF1 = -0.01111
95% bootstrap CI = [-0.01842, -0.00370]
```

두 모델 모두 CI가 0보다 아래에 있었다.

따라서 Train OOF sensitivity 결과에서는 C의 F1 하락이 단순히 한두 fold에서 발생한 우연한 차이보다는 **반복 resampling에서도 일관된 음의 방향**을 보였다.

다만 이 역시 독립 Test 검정이 아니므로 “통계적으로 C가 열등하다”는 식으로 과도하게 표현하지 않는다.

---

# 13. A / B / C 최종 비교

최종적으로 각 전략에서 tuning을 마친 결과를 OOF F1 기준으로 비교하면 다음과 같다.

| Strategy | Feature / Weighting | LR OOF F1 | XGB OOF F1 | XGB ΔF1 vs A |
|---|---|---:|---:|---:|
| **A Baseline** | 25 Features | **0.4928** | **0.5079** | — |
| **B Tuned** | 25 + `n_prior_periods` | **0.4967** | **0.5124** | **+0.0045** |
| **C-revised Tuned** | 25 + person-level sample weighting | **0.4831** | **0.4968** | **-0.0111** |

### B

- 두 모델 모두 A보다 OOF F1 point estimate가 소폭 높음
- XGB에서 ROC-AUC/AP도 소폭 상승
- `n_prior_periods`가 LR 3위, XGB 6위의 permutation importance를 보임
- 두 모델 모두 5/5 fold에서 양의 PI
- 하지만 A 대비 paired bootstrap CI는 0을 포함

따라서:

> **`n_prior_periods`는 모델이 실제로 활용하는 보조 정보로 보이지만, A를 대체할 정도의 뚜렷하고 안정적인 성능 개선은 확인되지 않았다.**

### C

- weighted class correction으로 C-old의 비정상적인 Precision/Recall 쏠림은 완화
- C 전용 재튜닝 후에도 A보다 F1이 낮음
- A 대비 paired bootstrap CI가 음의 방향
- 1-row 집단에서는 성능이 상승했지만 2/3-row 집단에서 성능 감소
- person-level weighting이 effective class distribution과 trajectory group의 상대적 비중을 크게 변경

따라서:

> **현재 Person-Period 데이터에서는 모든 사람의 총 학습 기여를 1로 강제하는 weighting을 적용할 근거가 확인되지 않았다.**

---

# 14. 이 실험에서 얻은 핵심 해석

## 14.1 반복관측은 단순한 복제 행이 아니다

한 사람이 여러 Person-Period를 가지더라도 각 행은 서로 다른 기준연도에서의 **실제 차년도 transition prediction unit**이다.

따라서 한 사람이 3개의 row를 가진다고 해서 같은 observation이 3번 복제된 것으로 볼 수는 없다.

동일 SAMPID가 Train/Validation 또는 Train/Test 양쪽에 동시에 들어가는 leakage 문제는 `SAMPID` grouped split으로 별도로 통제하고 있다.

즉 반복관측의 존재 자체가 곧 sample weighting이 반드시 필요하다는 뜻은 아니다.

## 14.2 B는 “반복관측을 줄이는 방법”이 아니라 이력을 알려주는 방법이다

B는 3행 사람의 영향력을 낮추지 않는다.

대신 현재 observation이 이전 eligible observation을 얼마나 거쳤는지 알려준다.

실험 결과 `n_prior_periods`는 실제로 모델에서 사용되었으며 소폭의 OOF 성능 상승과 연결되었다.

다만 그 개선량은 작고 A 대비 bootstrap CI가 0을 포함했으므로 공식 Feature로 사후 추가하지 않는다.

## 14.3 C의 `1 / n_i`는 예상보다 강한 가정을 만든다

C를 처음 설계할 때는 단순히:

> “한 사람의 총 weight를 같게 만들자.”

는 목적이었다.

하지만 실제 데이터에서는 최종 Person-Period 개수가 target trajectory와 강하게 연결되어 있었다.

따라서 `1 / n_i`는 결과적으로:

- 1-row trajectory에는 큰 row weight
- 3-row trajectory에는 작은 row weight

를 부여하고, raw class distribution까지 크게 바꿨다.

즉 **동일인 반복관측 보정과 trajectory group 재가중이 동시에 일어나는 구조**였다.

이 점 때문에 C를 단순한 “중복 관측 제거용 weighting”으로 해석하는 것은 적절하지 않다.

---

# 15. 최종 결정

이번 민감도 분석을 근거로 공식 Global Model의 반복관측 처리 방식을 다음과 같이 유지한다.

## 공식 모델

```text
A Baseline 유지

XGBoost
+ 최종 25 Features
+ Person-Period를 개별 transition observation으로 사용
+ SAMPID grouped split
+ sample_weight 사용하지 않음
+ n_prior_periods 공식 predictor에 추가하지 않음
+ threshold = 0.5
```

### `n_prior_periods`

실제 추가 예측 정보를 제공할 가능성은 확인했지만:

- 성능 증가폭이 작고
- A 대비 paired bootstrap CI가 0을 포함하며
- 공식 A의 Test가 이미 공개된 뒤 수행한 사후 민감도 분석이므로

공식 Global Model을 변경하지 않는다.

다만 **후속 연구에서 사전에 정의한 predictor 후보**로 검토할 가치는 있다.

### `sample_weight`

Person-level equal weighting은:

- C-revised 및 재튜닝 후에도 A보다 낮은 OOF F1
- 반복관측이 많은 그룹에서 성능 감소
- effective class distribution의 큰 변화

가 나타났으므로 공식 모델에는 적용하지 않는다.

---

# 16. 보고서/발표에서 사용할 수 있는 요약 문장

> 동일 개인이 최대 3개의 Person-Period 관측을 가질 수 있기 때문에 반복관측이 모델 학습에 미치는 영향을 추가로 점검하였다. 기존 25개 Feature 모델을 A로 두고, 과거 eligible 관측 횟수인 `n_prior_periods`를 추가한 B와 SAMPID별 전체 학습 기여도를 동일하게 만든 sample-weighted C를 비교하였다. B는 재튜닝 후 XGBoost OOF F1이 0.5079에서 0.5124로 소폭 상승했으며 `n_prior_periods`도 여러 fold에서 안정적인 예측 기여를 보였지만, A 대비 paired bootstrap CI가 0을 포함해 명확한 우위로 판단하지 않았다. 반면 C는 weighted class correction과 재튜닝을 적용한 이후에도 XGBoost OOF F1이 0.4968로 A보다 낮았고, 특히 반복관측이 많은 집단에서 성능 감소가 나타났다. 이에 따라 반복 Person-Period를 개별 transition observation으로 유지하되 SAMPID 단위 group split으로 leakage를 방지하는 기존 A 설계를 유지하였다.

---

# 17. 해석 시 주의사항

1. **B의 성능 상승을 확정적인 개선으로 표현하지 않는다.**
   XGBoost OOF F1은 약 +0.0045 상승했지만 paired bootstrap CI가 0을 포함한다.

2. **`n_prior_periods`의 permutation importance를 인과효과로 해석하지 않는다.**
   패널 시간 구조 및 `baseline_year`와 연관될 수 있는 보조 예측 정보이다.

3. **C의 결과를 단순히 “sample_weight는 항상 나쁘다”로 일반화하지 않는다.**
   본 결과는 현재 정의인 `1 / 전체 eligible PP 수` weighting과 YP2021 Person-Period 구조에 대한 결과이다.

4. **C-old의 Recall 0.80을 장점으로 해석하지 않는다.**
   person weighting과 raw-row class imbalance correction의 조합으로 Precision/Recall balance가 크게 이동한 결과였고, C-revised에서 이 현상이 완화되었다.

5. **B/C는 공식 held-out Test 모델 선택 실험이 아니다.**
   A의 Test 결과를 이미 본 이후 수행한 post-hoc sensitivity analysis이므로 공식 A를 교체하는 근거로 사용하지 않는다.

6. **OOF paired bootstrap은 독립 Test 검정이 아니다.**
   Train-CV 결과의 resampling 안정성을 확인하기 위한 보조 지표이다.

7. **Person-Period 수별 C subgroup 결과는 trajectory와 연결되어 있다.**
   1/2/3-row 그룹의 target distribution 자체가 크게 다르므로 단순한 그룹 간 성능 비교 이상의 인과적 의미를 부여하지 않는다.

---

# 18. 주요 결과 파일

## A — 공식 Global Baseline

- `stage_3_5/final_tuning_summary.csv`
- `stage_3_5/final_refined_params.json`
- `stage_3_5/refined_logistic_regression_oof_predictions.parquet`
- `stage_3_5/refined_xgboost_oof_predictions.parquet`

## B — `n_prior_periods`

### Locked

- `sensitivity_n_prior_periods/locked_model_summary.csv`
- `sensitivity_n_prior_periods/locked_fold_f1.json`
- `sensitivity_n_prior_periods/locked_*_oof_predictions.parquet`

### Tuning

- `tuning/tuning_summary.csv`
- `tuning/best_params.json`
- `tuning/logistic_regression_search_results.csv`
- `tuning/xgboost_refinement_stage_a.csv`
- `tuning/xgboost_refinement_stage_b.csv`
- `tuning/xgboost_refinement_stage_c.csv`
- `tuning/*_oof_predictions.parquet`

### Diagnostics

- `diagnostics/diagnostics_summary.csv`
- `diagnostics/n_prior_periods_distribution.csv`
- `diagnostics/n_prior_periods_group_metrics.csv`
- `diagnostics/logistic_regression_permutation_importance.csv`
- `diagnostics/xgboost_permutation_importance.csv`
- `diagnostics/paired_bootstrap_oof.csv`

## C — Person-level sample weighting

### C-old

- `sensitivity_sample_weight/locked_model_summary.csv`
- `sensitivity_sample_weight/locked_fold_f1.json`
- `sensitivity_sample_weight/locked_*_oof_predictions.parquet`

### C-revised Locked

- `sensitivity_sample_weight_weighted_class/locked_model_summary.csv`
- `sensitivity_sample_weight_weighted_class/weighted_class_audit.csv`
- `sensitivity_sample_weight_weighted_class/locked_*_oof_predictions.parquet`

### C-revised Tuning

- `tuning/tuning_summary.csv`
- `tuning/best_params.json`
- `tuning/weighted_class_audit.csv`
- `tuning/logistic_regression_search_results.csv`
- `tuning/xgboost_refinement_stage_a.csv`
- `tuning/xgboost_refinement_stage_b.csv`
- `tuning/xgboost_refinement_stage_c.csv`
- `tuning/*_oof_predictions.parquet`

### C Diagnostics

- `diagnostics/diagnostics_summary.csv`
- `diagnostics/sampid_row_count_distribution.csv`
- `diagnostics/row_count_group_metrics.csv`
- `diagnostics/weighted_class_audit_summary.csv`
- `diagnostics/paired_bootstrap_oof.csv`

---

# 19. 최종 요약

이번 실험은 “같은 사람이 여러 Person-Period 행을 가진다는 이유만으로 기존 Global Model이 특정 사람에게 과도하게 끌려가는가?”라는 질문에서 시작했다.

이를 확인하기 위해 기존 A를 기준으로:

- 반복관측 횟수를 예측 정보로 제공하는 B
- 사람별 총 기본 weight를 동일하게 만드는 C

를 순차적으로 비교했다.

B에서는 `n_prior_periods`가 실제 예측에 활용되는 신호임이 확인되었고, 재튜닝 후 OOF F1도 소폭 상승했다. 그러나 상승 폭은 작고 A 대비 bootstrap CI가 0을 포함했기 때문에 기존 모델을 대체할 정도의 근거로 보지는 않았다.

C에서는 초기 class imbalance 처리와 sample weighting의 기준 차이를 수정한 C-revised까지 검토하고 별도 재튜닝을 수행했지만, 최종 OOF F1은 A보다 낮았다. Diagnostics에서는 `1 / n_i` weighting이 단순히 반복관측자의 영향만 줄이는 것이 아니라, 서로 다른 취업전환 trajectory를 가진 집단의 상대적 기여와 effective class distribution까지 크게 변경한다는 점을 확인했다.

따라서 본 프로젝트에서는 **Person-Period를 각각 실제 transition observation으로 유지하고, 동일 인물의 데이터 누수는 SAMPID 단위 grouped split으로 통제하는 A의 기존 설계를 유지**한다.

B와 C 실험은 공식 Global Model을 다시 선택하기 위한 과정이 아니라, **반복관측 처리에 대한 기존 설계가 합리적인지 점검하고 그 선택 근거를 남긴 민감도 분석**으로 정리한다.

---
## 🖊 작성 출처

> 이 보고서 본문은 사용자가 제공한 결과 보고서 원문을 보관한 것이다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 전체 본문·결과 해석·최종 판단 | **사람이 제공한 결과 보고서 원문** | ✅ 2026-08-22 사용자 제공 |
