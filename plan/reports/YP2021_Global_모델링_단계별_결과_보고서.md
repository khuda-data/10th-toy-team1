# YP2021 Global 취업전환 예측 모델링 단계별 결과 보고서

## 1. 보고서 목적

본 보고서는 YP2021 Person-Period 데이터를 이용한 **차년도 취업전환 예측 Global Model**의 모델링 과정을 단계별로 정리한 문서이다.  
단순히 각 단계의 성능만 나열하는 것이 아니라, **왜 해당 결정을 내렸는지**, 다음 단계로 어떤 이유로 넘어갔는지를 함께 기록하는 것을 목적으로 한다.

본 분석의 핵심 원칙은 다음과 같다.

- 예측 대상: 기준연도 미취업 청년의 **차년도 취업전환 여부**
- Positive class: `employment_transition = 1`
- 동일 인물이 Train/Test에 동시에 들어가지 않도록 `SAMPID` 단위 분리
- Train 내부에서는 `StratifiedGroupKFold(5)` 사용
- Primary metric: **F1**
- Classification threshold: **0.5**
- Feature selection 및 hyperparameter tuning은 **Train/CV에서만 수행**
- Test Dataset은 최종 단계에서 한 번만 사용
- Test 확인 이후 Feature, hyperparameter, threshold를 다시 수정하지 않음

특히 Positive 비율이 약 26%인 불균형 데이터이므로 Accuracy만으로는 모델을 평가하기 어렵다.  
모든 사람을 미취업으로 예측해도 높은 Accuracy가 나올 수 있기 때문에, 실제 취업자를 얼마나 잘 찾아내는지와 그 예측의 정확성을 함께 보는 **F1을 주평가지표로 사용했다.**

---

# 2. 1단계 — 전체 42개 Feature 기반 1차 모델

## 2.1 목적

Feature selection을 수행하기 전에 전체 42개 Feature를 사용해 Logistic Regression과 XGBoost의 기본 성능을 확인했다.

이 단계의 목적은 바로 하나의 모델을 최종 선택하는 것이 아니라,

1. 두 알고리즘의 기본적인 예측 성능을 확인하고
2. 이후 Feature 분석에서 두 모델의 관점을 함께 활용할 가치가 있는지 판단하는 것이었다.

## 2.2 결과

| Model | Features | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | OOF ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 42 | 0.4911 | 0.0233 | 0.4204 | 0.5899 | 0.4909 | 0.7023 |
| XGBoost | 42 | **0.5054** | **0.0152** | 0.4123 | **0.6531** | **0.5055** | **0.7106** |

### Best parameters

**Logistic Regression**

- `C = 1`
- `penalty = l1`
- `class_weight = balanced`

**XGBoost**

- `learning_rate = 0.03`
- `n_estimators = 500`
- `max_depth = 3`
- `min_child_weight = 5`
- `subsample = 1.0`
- `colsample_bytree = 1.0`
- `scale_pos_weight = Train fold의 negative / positive 비율`

## 2.3 판단

**1단계 결과:** XGBoost가 현재 1차 모델 중 약간 더 유망하지만, 차이가 크지는 않다고 판단했다.

XGBoost는 LR보다:

- CV/OOF F1이 약 0.0145 높았고
- fold 간 F1 표준편차가 더 작았으며
- Precision은 유사한 수준인 반면
- Recall이 약 0.653으로 LR의 약 0.590보다 높았다.

즉 XGBoost가 실제 취업자를 더 많이 찾아내는 모습을 보였지만, 이 차이만으로 이 시점에서 모델을 확정하기에는 충분하지 않다고 보았다.

따라서 **LR과 XGBoost를 모두 유지한 상태로 Feature 분석 단계로 이동**했다.

이 결정은 두 알고리즘이 Feature를 활용하는 방식이 다르기 때문이다.

- LR: 비교적 선형적인 관계를 중심으로 학습
- XGBoost: 비선형 관계와 Feature 간 상호작용을 활용 가능

한 모델의 중요도만 보고 Feature를 제거하면 다른 알고리즘에서 유용한 변수를 놓칠 수 있으므로, Feature selection 단계에서도 두 모델의 결과를 함께 보기로 했다.

---

# 3. 2단계 — Feature Selection

## 3.1 목적

42개 Feature 모두를 무조건 유지하기보다,

- 예측에 실제로 기여하는가
- 다른 Feature와 거의 같은 정보를 담고 있지 않은가
- 연구적으로 해석 가능한가
- 현재 변수 생성 방식이 의도한 개념을 제대로 표현하는가

를 함께 검토해 최종 Feature set을 결정했다.

Feature importance 하나만을 기준으로 자동 삭제하지 않고, **모델 결과 + 변수 의미 + 중복성 + 데이터 구축 과정**을 같이 판단했다.

## 3.2 Feature 선택 원칙

최종적으로 Feature 제거 이유는 단순히 “importance가 낮다”가 아니라 다음 네 범주 중 하나 이상으로 설명할 수 있도록 했다.

1. **예측 기여가 거의 없음**
   - LR/XGBoost에서 permutation importance가 거의 0이거나 음수
   - 여러 fold에서 안정적인 기여가 나타나지 않음

2. **다른 변수와 사실상 중복**
   - 거의 동일한 정보를 담는 변수 쌍은 둘 다 유지하지 않음
   - 이 경우 해석하기 쉬운 대표 변수를 유지

3. **해석이 불명확**
   - 값은 존재하지만 실제로 어떤 행동이나 상태를 의미하는지 명확히 설명하기 어려움

4. **데이터/변수 구축상의 측정 한계**
   - 설문 분기 자체를 학습할 위험이 크거나
   - 현재 생성된 값이 원래 의도한 개념 전체를 제대로 대표하지 못함

추가로 두 가지 원칙을 명시적으로 적용했다.

- **중요도가 낮더라도 연구적으로 의미가 분명하면 유지**
- **중복 변수 중 하나를 제거하면 대표 변수는 남김**

## 3.3 최종 사용 Feature — 25개

### 인구통계 및 기준 시점

1. `gender`
2. `age`
3. `region_5`
4. `baseline_year`

### 교육

5. `education_level`
6. `student_status`
7. `student_type`
8. `university_type`
9. `major_group`
10. `months_since_graduation`

### 미취업 상태 및 구직·취업준비

11. `nonemployment_type`
12. `recent_job_search`
13. `recent_employment_prep`
14. `prep_effort_03`
15. `prep_effort_04`
16. `prep_effort_08`
17. `prep_effort_12`
18. `graduation_prep_experience`
19. `graduation_job_search_experience`

### 자격증

20. `has_certificate`
21. `has_employment_certificate`
22. `has_major_related_certificate`

### 시험 준비

23. `exam_prep_experience`
24. `currently_preparing_exam`

### 과거 일경험

25. `ever_worked_before`

## 3.4 제거 Feature — 17개

### 예측 기여가 매우 낮거나 불안정

- `prep_effort_01`
- `prep_effort_02`
- `prep_effort_05`
- `prep_effort_06`
- `prep_effort_07`
- `prep_effort_09`
- `prep_effort_10`
- `prep_effort_11`

### 의미가 불명확

- `prep_effort_other`

`prep_effort_other`는 기타 취업노력이라는 사실만 알 수 있고 실제 어떤 행동을 했는지 특정하기 어려워, 낮은 중요도와 함께 해석 가능성 문제를 고려해 제거했다.

### 중복 정보를 줄이기 위해 제거

- `certificate_count`
- `vocational_training_count`
- `exam_prep_count`
- `past_job_count`
- `has_vocational_training`

대표적인 중복 관계는 다음과 같았다.

- `has_certificate` ↔ `certificate_count`: Spearman 약 0.999
- `exam_prep_experience` ↔ `exam_prep_count`: Spearman 약 0.999
- `ever_worked_before` ↔ `past_job_count`: Spearman 약 0.99995
- `has_vocational_training` ↔ `vocational_training_count`: 거의 완전한 중복

자격증, 시험준비, 과거 일경험은 각각 `has_certificate`, `exam_prep_experience`, `ever_worked_before`를 대표 변수로 남겼다.

직업훈련 계열의 경우에는 대표 변수를 억지로 남기지 않았다. 훈련 여부/횟수의 예측 신호가 약했고, 훈련시간 변수도 아래의 측정 문제가 있었기 때문이다.

### 변수 생성 또는 설문 구조상의 한계로 제거

- `vocational_training_hours`
- `school_work_experience`
- `past_work_months`

**`vocational_training_hours`**

설문에는 여러 직업교육훈련별 시간이 존재하지만, 현재 구현은 전체 훈련시간이 아니라 첫 번째 훈련시간을 중심으로 생성되는 한계가 있었다. 따라서 이를 “누적 직업훈련량”으로 해석하기 어렵다고 판단했다.

**`school_work_experience`**

연구적으로는 의미가 있지만 구조적 미관측이 매우 많았다. 이 경우 모델이 “재학 중 일경험”이라는 원래 개념보다 **해당 설문 분기의 응답 대상이었는지 여부**를 학습할 가능성이 있어 제거했다.

**`past_work_months`**

현재 데이터 구조에서 정확한 전체 누적 근로개월을 완전히 복원하기 어렵다는 구현상의 한계가 있어 제거했다.

## 3.5 2단계 결론

**42개 → 25개 Feature로 축소했다.**

중요한 점은 Feature 수를 줄이는 것 자체가 목적이 아니었다는 것이다.

최종 Feature set은:

- 안정적인 예측 신호가 있는 변수
- 연구적으로 의미가 있는 변수
- 중복 변수군을 대표할 수 있는 변수

를 중심으로 유지했고,

- 기여가 거의 없는 변수
- 중복성이 지나치게 높은 변수
- 해석하기 어려운 변수
- 현재 생성 방식에 측정 한계가 있는 변수

를 제거했다.

또한 LR과 XGBoost에 서로 다른 Feature set을 주지 않고 **동일한 25개 Feature를 사용하기로 결정했다.**

그 이유는 이후 두 모델의 성능 차이를 비교할 때 Feature set까지 달라지면,

> 알고리즘 차이 때문에 성능이 달라졌는지  
> Feature 선택 차이 때문에 달라졌는지

분리하기 어려워지기 때문이다.

동일 Feature set을 사용하는 원칙은 이후 **Global Model과 Local Model을 공정하게 비교하기 위해서도 유지**하기로 했다.

---

# 4. 3단계 — 선택된 25개 Feature로 2차 모델 재학습

## 4.1 목적

2단계에서 사람이 확정한 25개 Feature만 사용하여 LR과 XGBoost를 처음부터 다시 학습하고, 42개 Feature 모델과 비교했다.

Feature를 줄인 뒤 기존 모델을 그대로 사용하는 것이 아니라, **새로운 Feature set에 맞춰 hyperparameter search도 다시 수행**했다.

Test Dataset은 여전히 사용하지 않았다.

## 4.2 결과

| Model | Features | CV F1 Mean | CV F1 Std | OOF Precision | OOF Recall | OOF F1 | OOF ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR 1차 | 42 | 0.4911 | 0.0233 | 0.4204 | 0.5899 | 0.4909 | 0.7023 |
| LR 2차 | 25 | **0.4926** | 0.0225 | **0.4212** | **0.5927** | **0.4925** | 0.7014 |
| XGB 1차 | 42 | 0.5054 | **0.0152** | 0.4123 | 0.6531 | 0.5055 | **0.7106** |
| XGB 2차 | 25 | **0.5079** | 0.0160 | **0.4137** | **0.6576** | **0.5079** | 0.7105 |

### Feature selection 전후 OOF F1 변화

- LR: `0.4909 → 0.4925` 약 **+0.0015**
- XGBoost: `0.5055 → 0.5079` 약 **+0.0024**

## 4.3 판단

두 모델 모두 17개 Feature를 제거했음에도 CV/OOF 성능이 감소하지 않았고 오히려 F1이 소폭 증가했다.

다만 개선 폭은 매우 작기 때문에,

> “Feature selection으로 예측 성능이 크게 향상됐다”

라고 해석하지 않기로 했다.

대신 이 단계의 핵심 결과는:

> **Feature를 약 40% 줄였음에도 Train-CV 기준 예측 성능을 유지했다.**

는 것이다.

따라서 단순성과 해석 가능성을 고려해 **25개 Feature를 후속 공식 Feature set으로 고정**했다.

XGBoost는 여전히 LR보다 F1이 높았지만, Test를 확인하기 전까지 최종 일반화 성능을 확정하지 않았다.

---

# 5. 3.5단계 — 최종 Hyperparameter Refinement 및 Threshold 점검

## 5.1 목적

Stage 4에서 Test를 사용하기 전에 마지막으로 Train/CV 안에서 현재 best parameter 주변을 정밀하게 탐색했다.

이 단계에서는:

- Feature는 25개로 고정
- 새로운 Feature selection 금지
- 동일 `StratifiedGroupKFold(5)` 유지
- Primary metric은 F1 유지
- Test 사용 금지

원칙을 유지했다.

이미 Stage 3에서 대략적인 최적점이 확인되었으므로 넓은 범위를 다시 탐색하지 않고 **현재 best 주변만 제한적으로 refinement**했다.

## 5.2 LR 결과

### Stage 3

- `C = 0.1`
- `penalty = l2`
- `class_weight = balanced`
- OOF F1 = **0.4925**

### Stage 3.5

- `C = 0.3`
- `penalty = l1`
- `class_weight = balanced`
- OOF F1 = **0.4928**
- OOF ROC-AUC = **0.7022**

성능은 아주 조금 상승했지만 차이는 매우 작았다.

따라서 LR은 새로운 parameter를 사용할 수는 있지만, 이를 큰 성능 개선으로 해석하지 않았다.

## 5.3 XGBoost 결과

Stage A/B/C로 나누어 다음 영역을 추가 탐색했다.

- learning rate / estimators / depth / child weight
- subsample / colsample / gamma
- L1/L2 regularization

최종적으로 선택된 값은:

- `learning_rate = 0.03`
- `n_estimators = 500`
- `max_depth = 3`
- `min_child_weight = 5`
- `subsample = 1.0`
- `colsample_bytree = 0.8`
- `gamma = 0`
- `reg_alpha = 0`
- `reg_lambda = 1`
- `scale_pos_weight = Train fold의 negative / positive 비율`

이었다.

Stage 3의 XGBoost와 사실상 같은 설정이 다시 선택되었고,

- CV F1 = **0.5079**
- OOF F1 = **0.5079**

로 성능도 동일했다.

## 5.4 Hyperparameter refinement에 대한 판단

XGBoost는 주변 search space를 추가로 탐색했음에도 기존 Stage 3 설정이 다시 선택되었다.

따라서:

> **기존 XGBoost parameter가 탐색 부족 때문에 우연히 선택된 것이라기보다는, 현재 Train/CV 범위 안에서 비교적 안정적인 최적점이라는 근거가 강화되었다.**

고 판단했다.

이 시점부터는 더 넓은 search space를 반복적으로 탐색할 경우 같은 CV에 과적합할 위험이 있기 때문에 추가 hyperparameter tuning을 중단했다.

---

## 5.5 Threshold sensitivity

Positive 비율이 약 26%이므로 threshold를 0.5보다 낮추면 Recall을 높일 가능성이 있었다.

다만 양성 비율이 26%라고 해서 threshold를 0.26으로 설정하는 것은 아니며, threshold는 OOF prediction을 이용해 실제 Precision/Recall/F1 변화를 확인해야 한다.

### Logistic Regression

| Threshold | Precision | Recall | F1 |
|---|---:|---:|---:|
| 0.50 | 0.4218 | 0.5924 | 0.4928 |
| OOF best = 0.44 | 0.3915 | 0.6913 | **0.4999** |

F1 개선량: 약 **+0.0071**

### XGBoost

| Threshold | Precision | Recall | F1 |
|---|---:|---:|---:|
| 0.50 | 0.4137 | 0.6576 | 0.5079 |
| OOF best = 0.47 | 0.3985 | 0.7047 | **0.5092** |

F1 개선량: 약 **+0.0013**

## 5.6 Threshold 결정

XGBoost에서는 threshold를 0.47로 낮추면 Recall은 약 65.8%에서 70.5%로 상승했지만 Precision이 감소했고, 최종 F1 증가는 약 0.0013에 불과했다.

LR은 F1이 약 0.0071 증가했지만, 모델별로 서로 다른 threshold를 사용하면 이후 Global/Local 비교의 조건이 복잡해질 수 있다.

따라서 공식 분석에서는:

> **모든 모델에 threshold = 0.5를 유지**

하기로 했다.

Threshold tuning 자체가 잘못된 것은 아니지만, 현재 프로젝트에서는 얻는 이득보다 **비교 조건의 일관성 및 해석의 단순성**을 더 중요하게 판단했다.

Stage 3.5를 마지막으로 Feature, hyperparameter, threshold를 모두 동결하고 Stage 4로 이동했다.

---

# 6. 4단계 — Held-out Global Test 최종 평가

## 6.1 목적

Stage 1~3.5에서는 Test Dataset을 사용하지 않았다.

Stage 4에서 처음으로 고정된 Global Test Dataset을 열어,

> Train/CV에서 선택한 모델 사양이 실제로 보지 못한 데이터에서도 유지되는가?

를 평가했다.

Test 결과를 확인한 이후에는 모델을 다시 수정하지 않는다는 원칙을 적용했다.

## 6.2 Test Dataset

- Test Person-Period rows: **2,981**
- Test unique SAMPID: **1,406**
- Positive: **780**
- Negative: **2,201**
- Positive rate: **26.17%**
- Train/Test SAMPID overlap: **0**

## 6.3 최종 Test 성능

| Model | Features | Test Accuracy | Precision | Recall | F1 | ROC-AUC | Average Precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| LR 1차 | 42 | **0.6924** | **0.4352** | 0.5897 | 0.5008 | 0.7095 | 0.4252 |
| LR 2차 | 25 | 0.6863 | 0.4270 | 0.5808 | 0.4921 | 0.7106 | 0.4209 |
| XGB 1차 | 42 | 0.6753 | 0.4218 | 0.6500 | 0.5116 | **0.7218** | **0.4472** |
| XGB 2차 | 25 | 0.6733 | 0.4210 | **0.6628** | **0.5149** | 0.7217 | 0.4406 |

Primary metric인 F1 기준으로는 **XGBoost 2차가 0.5149로 가장 높았다.**

## 6.4 CV와 Test 비교

네 모델 모두 Test F1이 Train/CV 성능에서 크게 무너지지 않았다.

특히 XGBoost 2차는:

- CV F1 약 **0.5079**
- Test F1 약 **0.5149**

로 Test에서 오히려 약간 높은 값을 보였다.

따라서 Train/CV에서 관찰된 예측 성능이 held-out Test에서 크게 붕괴하는 현상은 나타나지 않았다.

---

# 7. Feature Selection의 실제 Test 효과

## 7.1 Logistic Regression

- LR 1차 F1: **0.5008**
- LR 2차 F1: **0.4921**
- ΔF1: **-0.0087**

SAMPID paired bootstrap 95% CI:

**[-0.0175, -0.0008]**

즉 LR에서는 25개 Feature로 줄인 모델이 Test F1에서 오히려 낮아졌다.

혼동행렬도 같은 방향을 보였다.

### LR 1차

- TN = 1604
- FP = 597
- FN = 320
- TP = 460

### LR 2차

- TN = 1593
- FP = 608
- FN = 327
- TP = 453

따라서:

> **Feature selection이 모든 알고리즘의 예측성능을 개선했다고 주장하지 않는다.**

LR에서는 Feature 제거가 Test 성능 감소로 이어졌다.

## 7.2 XGBoost

- XGB 1차 F1: **0.5116**
- XGB 2차 F1: **0.5149**
- ΔF1: **+0.0033**

SAMPID paired bootstrap 95% CI:

**[-0.0043, 0.0127]**

0을 포함하기 때문에 XGB 2차가 XGB 1차보다 명확하게 우수하다고 말하기는 어렵다.

하지만 XGB에서는:

> **42개에서 25개로 Feature를 약 40% 줄였음에도 Test 성능이 유지되었다.**

는 점이 핵심이다.

### XGB 1차 혼동행렬

- TN = 1506
- FP = 695
- FN = 273
- TP = 507

### XGB 2차 혼동행렬

- TN = 1490
- FP = 711
- FN = 263
- TP = 517

2차 모델은:

- 실제 취업자를 10명 더 찾아냈고
- 놓친 취업자는 10명 줄었으며
- 대신 False Positive는 16명 증가했다.

그 결과 Precision은 거의 동일하면서 Recall이:

**0.6500 → 0.6628**

로 상승했고 F1도 소폭 증가했다.

따라서 XGBoost에서는 Feature selection을:

> “성능을 크게 향상시킨 과정”

보다는

> **“성능을 유지하면서 변수 수와 모델 복잡도를 줄인 과정”**

으로 해석한다.

---

# 8. Bootstrap을 이용한 일반화 성능 불확실성

SAMPID 단위 bootstrap 1,000회로 Test F1의 95% confidence interval을 계산했다.

같은 사람이 여러 Person-Period 행을 가지므로 행 단위가 아니라 **SAMPID 단위로 함께 resampling**했다.

| Model | Test F1 | 95% CI |
|---|---:|---:|
| LR 1차 | 0.5008 | [0.4718, 0.5314] |
| LR 2차 | 0.4921 | [0.4638, 0.5224] |
| XGB 1차 | 0.5116 | [0.4840, 0.5391] |
| XGB 2차 | **0.5149** | **[0.4894, 0.5420]** |

개별 모델의 CI는 상당 부분 겹친다.

따라서 단순히 point estimate만 보고 큰 성능 차이가 있다고 해석하지 않고, 동일 bootstrap sample에서 모델 차이를 계산하는 paired bootstrap도 함께 확인했다.

---

# 9. 최종 25개 Feature에서 LR과 XGBoost 비교

최종 Feature set이 같은 두 모델을 비교하면:

- LR 2차 F1 = **0.4921**
- XGB 2차 F1 = **0.5149**
- ΔF1 = **+0.0228**

Paired bootstrap 95% CI:

**[0.0056, 0.0393]**

즉 동일한 25개 Feature와 동일한 Test Dataset을 사용했을 때 XGBoost의 F1이 더 높았고, bootstrap resampling에서도 차이가 일관되게 양의 방향으로 나타났다.

두 모델의 Precision은:

- LR 2차: **0.4270**
- XGB 2차: **0.4210**

으로 큰 차이가 없었지만,

Recall은:

- LR 2차: **0.5808**
- XGB 2차: **0.6628**

로 XGBoost가 높았다.

즉 XGBoost의 F1 우위는 주로 **Precision을 크게 희생하지 않으면서 실제 취업자를 더 많이 찾아낸 것**에서 발생했다.

---

# 10. 최종 Permutation Importance

최종 25개 Feature 모델에 대해서만 held-out Test에서 permutation importance를 계산했다.

Permutation importance는 Feature를 섞었을 때 F1이 얼마나 감소하는지 측정한 것으로, **인과효과가 아니라 예측 기여도**로만 해석한다.

## 10.1 LR 상위 Feature

| Rank | Feature | Importance Mean |
|---|---|---:|
| 1 | `student_status` | 0.0477 |
| 2 | `recent_job_search` | 0.0104 |
| 3 | `months_since_graduation` | 0.0101 |
| 4 | `university_type` | 0.0074 |
| 5 | `age` | 0.0070 |
| 6 | `recent_employment_prep` | 0.0068 |
| 7 | `ever_worked_before` | 0.0047 |

## 10.2 XGBoost 상위 Feature

| Rank | Feature | Importance Mean |
|---|---|---:|
| 1 | `student_status` | 0.0357 |
| 2 | `months_since_graduation` | 0.0245 |
| 3 | `age` | 0.0212 |
| 4 | `major_group` | 0.0142 |
| 5 | `gender` | 0.0107 |
| 6 | `recent_job_search` | 0.0106 |
| 7 | `university_type` | 0.0105 |
| 8 | `ever_worked_before` | 0.0058 |
| 9 | `has_certificate` | 0.0036 |

두 모델에서 공통적으로 비교적 중요한 신호로 나타난 것은 다음과 같다.

- 학생 상태
- 졸업 후 경과기간
- 연령
- 최근 구직 경험
- 대학/전공 등 교육 배경
- 과거 근로경험

다만 이는 **취업의 원인**을 의미하지 않는다.

예를 들어 `student_status`의 importance가 높다는 결과는 현재 모델에서 학생 상태 정보가 예측에 유용했다는 뜻이지, 학생 여부가 취업전환을 직접적으로 유발하거나 방해했다는 뜻은 아니다.

---

# 11. 최종 Global Model 판단

지금까지의 결과를 종합하면 **XGBoost 2차 모델(25 Features)**을 최종 Global Model로 사용하는 것이 가장 타당하다고 판단했다.

선택 이유는 단순히 네 모델 중 Test F1이 가장 높았기 때문만은 아니다.

1. **Train/CV에서 LR보다 높은 F1을 지속적으로 보였다.**
2. **Stage 3.5 추가 탐색에서도 기존 XGBoost parameter가 다시 선택되어 설정이 안정적이었다.**
3. **Test에서도 CV 성능이 유지되었다.**
4. **동일한 25개 Feature를 사용한 LR보다 Test F1이 높았으며 paired bootstrap에서도 차이가 양의 방향이었다.**
5. **42개 XGBoost와 비교해 Test 성능을 유지하면서 Feature를 25개로 줄였다.**
6. **이후 Local Model에서도 동일한 25개 Feature를 사용하기 쉬워 Global/Local 비교 조건을 통일할 수 있다.**

따라서 최종 Global Model은:

> **XGBoost + 최종 25 Features + threshold 0.5**

로 동결한다.

최종 Test 성능은:

- Accuracy: **0.6733**
- Precision: **0.4210**
- Recall: **0.6628**
- F1: **0.5149**
- ROC-AUC: **0.7217**
- F1 95% CI: **[0.4894, 0.5420]**

이다.

이 수치에서 F1 0.5149는 “전체 사람 중 51.49%를 맞혔다”는 의미가 아니다.

현재 XGBoost 2차는:

- 모델이 취업한다고 예측한 사람 중 약 **42.1%**가 실제 취업했고
- 실제 취업자 중 약 **66.3%**를 찾아냈으며
- 이 Precision과 Recall을 종합한 F1이 약 **0.515**

라는 의미이다.

---

# 12. Global → Local Model로 넘어갈 때의 원칙

Local Model에서도 Global에서 확정한 **동일한 25개 Feature를 공식 입력 Feature set으로 사용**하는 것을 원칙으로 한다.

Local마다 다시 Feature selection을 수행해 서로 다른 Feature set을 사용할 경우:

- 학습 데이터를 직군별로 제한한 효과
- Feature를 직군별로 다르게 선택한 효과

가 섞여 Global vs Local의 성능 차이를 명확히 해석하기 어렵다.

따라서 공식 비교에서는:

```text
Global Model
동일 25 Features
→ 전체 Global Train에서 학습

Local Model
동일 25 Features
→ 해당 희망직군 Train에서 학습

둘 모두
→ 동일 직군 Test subset에서 평가
```

하는 구조를 사용한다.

이렇게 하면 Global과 Local의 차이는 주로:

> **전체 미취업 청년을 함께 학습했는가, 특정 희망직군만 별도로 학습했는가**

로 제한할 수 있다.

Local에서도 Feature Importance는 별도로 확인할 수 있지만, 이는 **직군별로 어떤 Feature가 상대적으로 중요하게 활용되는지 해석하기 위한 분석**으로 사용하며 공식 Feature set을 다시 변경하는 용도로 사용하지 않는다.

---

# 13. 단계별 의사결정 요약

| 단계 | 주요 결과 | 다음 결정 |
|---|---|---|
| 1단계 | XGB가 LR보다 F1·Recall이 조금 높고 fold 변동도 작음 | 차이가 크지 않아 둘 다 유지하고 Feature 분석 진행 |
| 2단계 | 중요도·중복·해석·측정 한계를 함께 검토 | 42개 → 25개 Feature 확정 |
| 3단계 | 25개로 줄여도 두 모델 CV/OOF 성능 유지 또는 소폭 증가 | 25개를 공식 Feature set으로 고정 |
| 3.5단계 | XGB는 기존 최적 parameter가 다시 선택됨. Threshold tuning 이득은 작음 | XGB parameter 동결, threshold=0.5 유지 |
| 4단계 | XGB 2차 Test F1=0.5149, LR 2차 대비 높은 Recall/F1. 42개 XGB와는 유사한 성능 | XGB 2차를 최종 Global Model로 사용 |
| 이후 Local | Global/Local 비교에서 Feature 차이의 영향을 제거할 필요 | 모든 Local에도 동일한 25개 Feature 적용 |

---

# 14. 해석 시 주의사항

1. **F1은 Accuracy가 아니다.**  
   F1 0.515를 “취업 여부를 51.5% 맞힌다”고 표현하지 않는다.

2. **Feature importance는 인과효과가 아니다.**  
   어떤 Feature의 importance가 높아도 그것이 취업을 유발한다는 뜻은 아니다.

3. **Feature selection이 모든 모델의 성능을 개선한 것은 아니다.**  
   LR에서는 Test F1이 감소했고, XGBoost에서는 성능을 유지하면서 변수 수를 줄이는 효과가 나타났다.

4. **XGB 2차와 XGB 1차의 Test F1 차이는 매우 작다.**  
   XGB 2차의 장점은 “확실한 성능 향상”보다는 **25개 Feature로 단순화하면서 성능을 유지했다는 점**에 있다.

5. **Test 결과 확인 이후 모델 사양을 수정하지 않는다.**  
   Stage 4 Test는 최종 일반화 성능 확인용이며 추가 tuning을 위한 validation data로 사용하지 않는다.

---

# 15. 사용한 주요 결과 파일

- Stage 1
  - `first_stage_summary.csv`
  - `best_params.json`
  - `fold_f1.json`

- Stage 2
  - `feature_selection_summary.csv`
  - permutation importance / correlation / VIF 결과
  - 최종 Feature 선정 검토표

- Stage 3
  - `second_stage_summary.csv`
  - `selected_features.csv`
  - `fold_f1.json`
  - OOF prediction parquet

- Stage 3.5
  - `final_tuning_summary.csv`
  - `final_refined_params.json`
  - `threshold_summary.csv`
  - refinement search 결과

- Stage 4
  - `final_test_summary.csv`
  - `final_model_comparison.csv`
  - `final_test_bootstrap_ci.csv`
  - `final_test_pairwise_bootstrap.csv`
  - `final_test_confusion_matrices.json`
  - `*_final_permutation_importance.csv`
  - `final_test_predictions.parquet`

---

## 최종 요약

이번 Global Model 개발에서는 단순히 가장 높은 CV 점수를 찾는 방식으로 진행하지 않았다.

**전체 Feature로 기본 모델 비교 → 두 모델을 활용한 Feature 진단 → 연구적 의미와 데이터 품질을 함께 고려한 Feature 선택 → 동일 Feature set으로 재학습 → 최종 hyperparameter refinement → threshold sensitivity 점검 → held-out Test 최초 평가**의 순서로 모델 개발과 평가를 분리했다.

최종적으로 XGBoost 2차 모델은 42개에서 25개로 Feature를 줄였음에도 Test F1을 유지했고, 동일 25개 Feature의 Logistic Regression보다 높은 F1과 Recall을 보였다.

따라서 Global Model은 **25개 Feature를 사용하는 XGBoost**로 동결하며, 이후 Local Model에서도 같은 Feature set과 평가 원칙을 유지하여 Global과 Local의 차이를 비교한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 본문은 사용자가 제공한 결과 보고서 원문이며 AI가 결과 해석·모델 판단을 수정하거나 새로 작성하지 않았다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 전체의 결과 해석·Feature 선택·threshold 정책·최종 모델 판단 | **사람(hanliyagi)이 제공한 원문 보고서** | ✅ 2026-08-21 hanliyagi |

- 세션 로그: `작업기록/hanliyagi/20260821-Global-Stage4-Test평가-코드준비.md`
