# 2026-08-23 로컬 직군 모델(group1~6) 성능 분석 및 향상 전략

- 도구/모델: Antigravity / Claude Sonnet 4.6 (Thinking)
- 브랜치: main (문서 분석 작업)

---

## 지침 (내가 시킨 것)

1. `data/result/baseline_42features/modeling` 경로에서 stage_4 로컬 직군 모델 group1~6 결과값이 유의미한지 확인해줘
2. 어떻게 성능을 올릴 수 있을까? 하이퍼파라미터랑 다시 조절해봐야 할까?

---

## AI가 한 일

### 파일 읽기
- `stage_4_local_group1~6/final_test_summary.csv` — 6개 그룹 전부 F1, ROC-AUC, Accuracy 등 지표 수집
- `stage_4_local_group1~6/final_test_bootstrap_ci.csv` — 그룹별 Bootstrap 95% CI 수집
- `stage_4_local_group1~6/final_test_pairwise_bootstrap.csv` — stage_1 vs stage_2 개선 유의성 검정 결과
- `stage_4_local_group1,3,4/xgboost_final_permutation_importance.csv` — 성능 높은 그룹(4)과 낮은 그룹(1,3) feature importance 비교
- `code/config/model_config.yaml` — 현재 하이퍼파라미터 탐색 범위 확인
- `code/model/tune.py`, `final_tuning.py` — 현재 튜닝 구조 파악
- `code/pipeline/build_local.py` — `use_n_prior_periods` 파라미터 존재 확인

### 분석 결과 정리 (아티팩트)
- `local_group_modeling_analysis.md` — 그룹별 성능 요약, CI, pairwise 유의성 판정
- `performance_improvement_plan.md` — 성능 향상 전략 (피처 우선 / 하이퍼파라미터 조건부 / 구조 검토)

---

## 주요 발견 사항

### 그룹별 성능 판정

| 그룹 | 최고 F1 | ROC-AUC | 판정 |
|------|--------|---------|------|
| Group 1 | 0.449 | 0.541 | ⚠️ 낮음 |
| Group 2 | 0.554 | 0.706 | ✅ 보통 |
| Group 3 | 0.488 | 0.548 | ⚠️ 낮음 |
| Group 4 | 0.661 | 0.743 | ✅ 양호 |
| Group 5 | 0.684 | 0.663 | ✅ 양호 |
| Group 6 | 0.655 | 0.628 | ⚠️ n=53 과소 |

### 핵심 인사이트
- **Stage_1 vs Stage_2 개선이 통계적으로 유의하지 않음** (전 그룹) → 하이퍼파라미터 무차별 재탐색은 효과 기대 낮음
- **Group 1/3의 낮은 성능 원인**: feature importance에서 `region_5(-0.028)`, `gender(-0.010)`, `currently_preparing_exam(-0.018)` 등 음수 importance 다수 → 해당 직군에서 현재 피처들이 noise로 작용
- **Group 4 잘 되는 이유**: `major_group` importance가 0.061로 압도적 1위 (Group 1에서는 0.019로 낮음)
- **`build_local.py`에 `use_n_prior_periods=True` 파라미터 이미 존재** → 즉시 실험 가능

### 권장 우선순위
1. `n_prior_periods` 피처 추가 실험 (코드에 이미 있음)
2. Group 1/3 EDA — feature importance 낮은 원인 파악
3. Group 1/3만 더 강한 정규화 방향 재탐색 (max_depth 낮추기, reg_lambda 강화)
4. Group 6 통합 여부 팀 결정

---

## 검증 (내가 직접 확인한 것)

⬜ 미검토 — AI가 파일을 읽고 수치를 정리한 것이므로, 수치가 실제 파일과 일치하는지 사람이 확인 필요

---

## 남은 것 / 막힌 것

- [ ] `n_prior_periods` 실험을 실제로 돌릴 것인지 팀 결정 필요
- [ ] Group 1/3의 성능 저하가 구조적 한계(직군 특성)인지, 피처 엔지니어링으로 해결 가능한지 EDA 필요
- [ ] Group 6 통합 여부 — 직군 분류 설계 의도와 연관되므로 팀 회의 필요
- [ ] Dummy baseline 대비 비교 수치 추가 (발표 설득력)

---

## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. **⬜ 항목은 사람 검토 전이므로 확정된 내용이 아니다.**

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 수치 수집 (F1, CI, pairwise) | AI가 파일 읽고 정리 | ⬜ 미검토 |
| 성능 판정 기준 | AI 초안 (사람 판단 필요) | ⬜ 미검토 |
| 향상 전략 방향 | AI 제안 | ⬜ 미검토 |
| 지침 원문 | 사람(cepil)이 직접 입력 | ✅ 원문 그대로 |
