# 2026-08-23 로컬 직군별 모델링 완전 분석 결과서 작성

- 도구/모델: Antigravity / Claude Sonnet 4.6 (Thinking)
- 브랜치: main (문서 분석 작업)

---

## 지침 (내가 시킨 것)

1. `data/result/baseline_42features/modeling` 경로에서 stage_4 로컬 직군 모델 group1~6 결과값이 유의미한지 확인해줘
2. 어떻게 성능을 올릴 수 있을까? 하이퍼파라미터랑 다시 조절해봐야 할까?
3. region_5가 뭔지 설명해줘
4. 성별이랑 거주지역을 피처에서 빼야 하는 거 아니야?
5. 그룹별 직군 정보 제공 (cepil 직접 입력):
   - Group 1: 경영·사무·금융 (KECO 0)
   - Group 2: 연구·공학·산업기술 (KECO 1,7,8)
   - Group 3: 교육·법률·사회·공공 (KECO 2)
   - Group 4: 보건·의료 (KECO 3)
   - Group 5: 예술·디자인·방송·스포츠 (KECO 4)
   - Group 6: 서비스·영업·판매·운송 (KECO 5,6,9)
6. 그룹별 결과 기반 분석문 작성해줘
7. 최대한 자세하게 분석 결과서 작성해줘

---

## AI가 한 일

### 파일 읽기
- `stage_4_local_group1~6/final_test_summary.csv` — 성능 수치 수집
- `stage_4_local_group1~6/final_test_bootstrap_ci.csv` — Bootstrap 95% CI
- `stage_4_local_group1~6/final_test_pairwise_bootstrap.csv` — stage 간 유의성
- `stage_4_local_group1~6/xgboost_final_permutation_importance.csv` — XGB feature importance (6개 그룹 전부)
- `stage_4_local_group1~6/logistic_regression_final_permutation_importance.csv` — LR feature importance (6개 그룹 전부)
- `stage_4_local_group1~6/final_test_confusion_matrices.json` — confusion matrix (6개 그룹 전부)
- `code/config/features.yaml` — 피처 정의 확인
- `code/config/model_config.yaml` — 하이퍼파라미터 탐색 범위 확인
- `code/pipeline/source_adapter.py` — region_5 원자료 매핑 확인
- `code/config/yp2021_missing_rules.json` — region_5 코딩 규칙 확인

### 생성 아티팩트
- `local_group_modeling_analysis.md` — 그룹별 성능 요약 + CI + pairwise 판정
- `performance_improvement_plan.md` — 성능 향상 전략
- `local_group_result_analysis_draft.md` — 완전 분석 결과서 (confusion matrix, feature importance 전부 포함)

---

## 주요 발견 사항

### 성능 요약

| 그룹 | 직군 | 최고 F1 | ROC-AUC | CI 하한 |
|------|------|--------|---------|---------|
| Group 1 | 경영·사무·금융 | 0.449 | 0.541 | 0.359 |
| Group 2 | 연구·공학·산업기술 | 0.554 | 0.706 | 0.417 |
| Group 3 | 교육·법률·사회·공공 | 0.488 | 0.548 | 0.344 |
| Group 4 | 보건·의료 | 0.661 | 0.743 | 0.558 |
| Group 5 | 예술·디자인·방송·스포츠 | 0.684 | 0.663 | 0.521 |
| Group 6 | 서비스·영업·판매·운송 | 0.655 | 0.628 | 0.519 |

### 핵심 인사이트

1. **성능 격차의 원인은 하이퍼파라미터가 아님** — stage_1 vs stage_2 개선이 전 그룹 유의하지 않음
2. **Group 4 (보건·의료)**: `major_group` importance 압도적 1위(0.061) — 전공→면허→취업 구조가 명확
3. **Group 3 (교육·법률·공공)**: `currently_preparing_exam` importance -0.018 (음수) — 임용고시·공무원 시험 장기 준비 구조 반영. 시험 준비 중 = 아직 합격 전
4. **Group 2 (연구·공학)**: LR과 XGB의 중요 피처가 완전히 다름 — 선형/비선형 관계 혼재
5. **Group 6**: 25개 피처 중 2개만 양수, 나머지 음수 또는 0 — 표본 과소(n=53) + 피처 신호 없음
6. **gender, region_5 제거 비권장** — Group 4에서는 gender가 rank 3위(0.032)로 중요. 일부 그룹에서 음수인 것은 해당 직군 구조의 문제이지 피처 자체의 문제가 아님

---

## 검증 (내가 직접 확인한 것)

⬜ 미검토 — 수치 및 해석 전부 AI 초안. 사람이 실제 파일과 대조 필요

---

## 남은 것 / 막힌 것

- [ ] 분석 결과서 해석 문장 검토 및 확정 (현재 전부 〔AI 제안〕 상태)
- [ ] Group 2 (연구·공학) LR vs XGB 중요 피처 차이 원인 추가 분석
- [ ] n_prior_periods 피처 추가 실험 여부 팀 결정
- [ ] Group 6 처리 방안 팀 결정

---

## 🖊 작성 출처

| 구간 | 주체 | 검토 |
|---|---|---|
| 수치 수집 전체 | AI가 파일 읽고 정리 | ⬜ 미검토 |
| 직군 분류 | **cepil이 직접 제공** | ✅ 2026-08-23 cepil |
| 해석 및 인사이트 | AI 초안 | ⬜ 미검토 |
| 지침 원문 | 사람(cepil)이 직접 입력 | ✅ 원문 그대로 |

### 시각화 차트 추가
- **프롬프트**: 노트북으로 내가 바로 볼 수 있게, PPT에 넣을 수 있게 Apple 디자인 적용해줘.
- **한 일**: sandbox/cepil/figures/에 Apple 디자인 토큰을 반영한 성능/Feature Importance/Confusion Matrix 차트 6종 생성 및 저장. sandbox/cepil/local_group_viz.ipynb 및 파이썬 스크립트 작성.

### 결과 분석 대본 추가
- **프롬프트**: 발표에 쓸 수 있게 차트 결과 분석해주고 sandbox에 푸시해줘.
- **한 일**: sandbox/cepil/presentation_analysis_script.md 작성 및 저장.
