# 세션 로그 — 글로벌 모델 단계별 모델링 PPT 구성

- **날짜**: 2026-08-23
- **작업자**: Cepil
- **AI**: Antigravity (Claude Sonnet 4.6 Thinking)

---

## ① 지침 (프롬프트 요지)

> "글로벌 모델 모델링 한거 단계별로 어떻게 했는지 정리 좀 해주라 내꺼 폴더 파일 뒤져보면서"
> "그거 흐름대로 ppt 만들고 싶은데 정리 좀 해줘"
> "ppt는 내가 만들테니깐 ppt 흐름이랑 내용만 구성만 해줘"

---

## ② AI가 한 일

- `data/result/baseline_42features/modeling/` 하위 stage_1~4 결과 파일 전수 조회
- `plan/details/14-Global-모델링-단계별-실행흐름.md` 및 `sandbox/cepil/engineering/README.md` 참조
- 단계별 수치(CV F1, OOF F1, 파라미터, Confusion Matrix, Bootstrap CI) 추출
- PPT 8장 구성안 작성

---

## ③ 글로벌 모델 단계별 모델링 PPT 구성안

> `〔AI 제안 · 사람 검토 필요〕`
> 수치는 실제 파일에서 추출한 값이지만, **각 단계의 결정 이유·최종 모델 선정 이유는 사람이 직접 써야 함.**

---

### 슬라이드 1 — 타이틀

**제목:** 글로벌 모델 단계별 모델링
**부제:** baseline_42features · YP2021 · SAMPID 기준 Train/Test 분할

---

### 슬라이드 2 — 분석 설계

**제목:** 분석 설계 및 데이터 구성

**내용:**
- **분석 대상:** 전체 미취업 청년 Person-Period 데이터 (YP2021)
- **피처 수:** 42개 (baseline_42features)
- **분할 기준:** SAMPID 단위 Train / Test 분할 → 동일인이 학습·평가에 겹치지 않음
- **모델 후보:** Logistic Regression(LR), XGBoost(XGB)
- **평가 기준:** F1 Score (threshold=0.5), ROC-AUC

**핵심 규칙:**
> Test는 Stage 4 전까지 절대 열지 않음 → Leakage 방지

**시각 제안:** Train/Test 분리 다이어그램 (박스 2개 + SAMPID 기준 화살표)

---

### 슬라이드 3 — Stage 1: 1차 모델 (42개 피처 전체)

**제목:** Stage 1 — 42개 피처로 1차 모델 구축

**성능 비교:**

| 모델 | CV F1 평균 | CV F1 std | OOF F1 | OOF ROC-AUC |
|---|---|---|---|---|
| Logistic Regression | 0.491 | 0.023 | 0.491 | 0.702 |
| **XGBoost** | **0.505** | **0.015** | **0.505** | **0.711** |

**fold별 F1 (5-fold):**
- LR: [0.475, 0.515, 0.461, 0.521, 0.483]
- XGB: [0.491, 0.526, 0.494, 0.522, 0.494]

**최적 하이퍼파라미터:**
- LR: `C=1, class_weight=balanced, penalty=L1`
- XGB: `lr=0.03, max_depth=3, min_child_weight=5, n_estimators=500`

**시각 제안:** LR vs XGB CV F1 막대그래프 + fold별 꺾은선

---

### 슬라이드 4 — Stage 2: 피처 분석 및 선택

**제목:** Stage 2 — 피처 중요도 분석 → 25개 선택

**내용:**
- Train 내부에서만 계산 (Test 미사용)
- 분석 기준: Permutation Importance, LR coefficient, XGBoost built-in importance
- 수치형 피처: Pearson/Spearman 상관관계 + VIF(분산팽창계수)
- **42개 → 25개 선택** (2026-08-21 사람이 직접 확정)

**선택된 25개 피처:**

| 카테고리 | 피처 |
|---|---|
| 인구통계 | gender, age, region_5, baseline_year |
| 학력·학적 | education_level, student_status, student_type, university_type, major_group |
| 졸업·취업 경험 | months_since_graduation, nonemployment_type, recent_job_search, recent_employment_prep, graduation_prep_experience, graduation_job_search_experience, ever_worked_before |
| 준비 노력 | prep_effort_03, prep_effort_04, prep_effort_08, prep_effort_12 |
| 자격·시험 | has_certificate, has_employment_certificate, has_major_related_certificate, exam_prep_experience, currently_preparing_exam |

**시각 제안:** 42개 → 25개 화살표 다이어그램 or 선택 피처 카테고리별 표

> `〔사람 확정 필요〕` **왜 이 25개를 골랐는지·제외한 피처의 이유는 직접 써야 함**

---

### 슬라이드 5 — Stage 3: 2차 모델 (25개 피처)

**제목:** Stage 3 — 선택 25개 피처로 2차 모델 재학습

**1차 vs 2차 비교:**

| | **1차 (42개)** | **2차 (25개)** |
|---|---|---|
| LR CV F1 | 0.491 | **0.512** |
| LR OOF F1 | 0.491 | 0.514 |
| XGB CV F1 | 0.505 | 0.506 |
| XGB OOF F1 | 0.505 | 0.507 |

**파라미터 변화:**
- LR: `C: 1 → 0.1` (정규화 강화)
- XGB: `min_child_weight: 5 → 1`, `n_estimators: 500 → 200`

**시각 제안:** 1차 vs 2차 그룹 막대그래프 (LR/XGB 각각)

---

### 슬라이드 6 — Stage 3.5: 하이퍼파라미터 미세 조정

**제목:** Stage 3.5 — 제한적 Refinement + Threshold 민감도

**Refinement 결과:**

| 모델 | Stage 3 CV F1 | Stage 3.5 CV F1 | 변화 |
|---|---|---|---|
| LR | 0.493 | 0.493 | `C: 0.1 → 0.3, L2 → L1` (소폭 조정) |
| XGB | 0.508 | 0.508 | 변화 없음 (Stage 3 이미 최적) |

**XGB 탐색 순서:** Stage A (기본 grid) → Stage B (+ gamma) → Stage C (+ reg_alpha, reg_lambda)

**Threshold 민감도 (Train OOF 기준):**

| 모델 | Default (0.5) F1 | OOF Best threshold | Best F1 |
|---|---|---|---|
| LR | 0.493 | 0.44 | 0.500 |
| XGB | 0.508 | 0.47 | 0.509 |

> Test는 이 단계에서도 열지 않음 — threshold 자동 선택 없음

**시각 제안:** threshold vs F1 꺾은선 (0.20~0.80 범위)

---

### 슬라이드 7 — Stage 4: 최종 Test 평가

**제목:** Stage 4 — 고정 Test 최초 공개 평가

**Test 세트:** 2,981행 / 1,406명 (SAMPID) / 양성률 26.2%

**4개 후보 비교:**

| 후보 | 피처 | Test F1 | 95% CI | ROC-AUC | Precision | Recall |
|---|---|---|---|---|---|---|
| LR Stage1 | 42개 | 0.501 | [0.472, 0.531] | 0.709 | 0.435 | 0.590 |
| LR Stage2 | 25개 | 0.492 | [0.464, 0.522] | 0.711 | 0.427 | 0.581 |
| XGB Stage1 | 42개 | 0.512 | [0.484, 0.539] | 0.722 | 0.422 | 0.650 |
| **XGB Stage2** | **25개** | **0.515** | **[0.489, 0.542]** | **0.722** | 0.421 | 0.663 |

**Confusion Matrix — XGB Stage2 (threshold=0.5):**

|  | 미취업 예측 | 취업 예측 |
|---|---|---|
| **실제 미취업** | TN: 1,490 | FP: 711 |
| **실제 취업** | FN: 263 | **TP: 517** |

Precision = 0.421 / Recall = **0.663**

**시각 제안:** 4개 후보 Test F1 막대그래프 + 95% CI 에러바 / Confusion Matrix 히트맵

---

### 슬라이드 8 — 결론: 최종 모델

**제목:** 최종 글로벌 모델 선정

**선정 모델: XGBoost · 25개 피처 (Stage 2)**

| 지표 | 값 |
|---|---|
| Test F1 | **0.515** |
| 95% Bootstrap CI | [0.489, 0.542] |
| ROC-AUC | **0.722** |
| Recall (취업자 탐지율) | **66.3%** |
| Precision | 42.1% |

**단계별 성능 흐름:**
`
Stage 1 XGB  →  Stage 3 XGB  →  Stage 3.5 XGB  →  Stage 4 XGB Stage2
CV F1: 0.505    CV F1: 0.506    CV F1: 0.508       Test F1: 0.515
`

> `〔사람 확정 필요〕` **왜 XGB Stage2를 최종 선정했는지, 이 모델로 말할 수 있는 것과 없는 것은 직접 써야 함**

---

### 슬라이드 순서 한눈에 보기

`
[1] 타이틀
[2] 분석 설계 (데이터 구성 / Test 봉인 규칙)
[3] Stage 1 — 42개 피처 1차 모델 (LR vs XGB)
[4] Stage 2 — 피처 분석 → 25개 선택
[5] Stage 3 — 25개 피처 2차 모델 (1차 vs 2차 비교)
[6] Stage 3.5 — 미세 조정 + Threshold 민감도
[7] Stage 4 — 최종 Test 공개 평가 (4개 후보 비교)
[8] 결론 — 최종 모델 선정
`

---

## ④ 검증

- stage_1~4 결과 CSV/JSON 파일 직접 읽어 수치 추출 확인
- plan/details/14번 문서 및 engineering/README.md 교차 확인

---

## ⑤ 남은 것 / 막힌 것

- 슬라이드 4 (피처 선택 이유), 슬라이드 8 (최종 모델 선정 이유·해석) → 사람이 직접 작성 필요

---

## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 수치 (F1, CI, 파라미터 등) | AI가 실제 결과 파일에서 추출 | ⬜ 미검토 |
| 슬라이드 구성·순서 | AI 제안 | ⬜ 미검토 |
| 피처 선택 이유 | `〔사람 확정 필요〕` | ⬜ 미작성 |
| 최종 모델 선정 이유·해석 | `〔사람 확정 필요〕` | ⬜ 미작성 |
