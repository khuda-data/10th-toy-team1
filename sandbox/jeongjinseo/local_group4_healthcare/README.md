# local_group4_healthcare — 보건·의료 직군 Local 모델링

## 무엇

희망직군 6개 중 **보건·의료**를 담당하는 Local 모델링 Notebook을 둔다. Global이 확정한 25개 Feature(`global_stage2_selected_25`)로 Stage 3(재튜닝) → Stage 3.5(refinement) → Stage 4(고정 Test 평가) → Global 최종 모델과의 비교까지를 다룬다.

## 왜

기존에 `data/result/baseline_42features/modeling/stage_4_local_group4`에 있던 보건·의료 결과는 Test 고유 인원이 78명으로, `wjdwlsah`가 2026-08-19에 실측 검증한 진짜 보건·의료 Test 인원(88명, `작업기록/wjdwlsah/20260819-Local-train-test-분할-실데이터검증.md`)과 맞지 않았다. 이 결과를 만든 Notebook 자체가 레포에 남아있지 않아 원인 추적이 불가능했고, 같은 시기 group1=group3 직군 필터 버그(`작업기록/didwo/20260823-fix-group3-model.md`)가 실제로 있었던 것을 감안하면 group4도 같은 종류의 문제를 안고 있을 가능성이 있었다. 그래서 처음부터 다시 만들었다.

## 확인된 것

- Stage 3~4 전 과정에서 Train 297명·Test 88명이 정확히 재현됨(진짜 값과 일치).
- Local 최종 후보(XGBoost, 25개 Feature, Stage 3.5 refined): Test F1 = 0.610
- Global 최종 모델(XGBoost, 25개 Feature, 전체 학습)을 보건·의료 Test에만 적용: Test F1 = 0.607
- ΔF1 = +0.003 — 두 95% Bootstrap 신뢰구간이 크게 겹쳐 통계적으로 유의미한 차이로 보기 어렵다.

## 규칙

- `03_second_model_local.ipynb` / `03_5_final_tuning.ipynb` / `04_model_comparison.ipynb`는 `code/` 공용 함수를 그대로 사용하며, Global Stage 3/3.5/4 Notebook과 동일한 CV·튜닝·threshold 조건을 따른다(직군 필터만 다름).
- `05_global_vs_local_comparison.ipynb`는 Global이 최종 확정한 모델(XGBoost + 25 Features + Stage 3.5 refined 파라미터)을 Global Train 전체로 다시 학습해 보건·의료 Test에만 적용한다 — Local 결과와 비교하기 위한 것이며 새 모델을 탐색하지 않는다.
- 결과 해석(ΔF1이 뜻하는 바, Feature Importance 해석)은 대원칙상 사람이 직접 쓴다. 이 폴더의 Notebook은 수치와 그래프만 만든다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 재작업 사유("왜") | **사람(정진서)이 직접 확인한 group4 Test 인원 불일치 및 팀 채팅 문의 결과를 바탕으로 판단** | ✅ 2026-08-24 정진서 |
| Stage 3~4 실행·수치 | AI가 실행하고 기록 | ⬜ 미검토 |
| ΔF1 등 결과 해석 | 아직 작성 안 됨 — 다음 세션에서 사람이 직접 작성 예정 | ⬜ 미작성 |

- 세션 로그: `작업기록/jeongjinseo/20260824-보건의료-2차모델링-재작업.md`
