# local_group3 — Local 직군 `교육·법률·사회·공공` 모델링 Notebook

## 무엇

Local 직군 6개 중 `교육·법률·사회·공공`(그룹3) 하나만 뽑아, Global에서 이미 확정한 Stage 1~4 흐름을 그대로 재현하는 Notebook 3개를 둔다.

- `03_second_model_local.ipynb` — Global Train에서 이 직군 행만 걸러낸 뒤, `global_stage2_selected_25`(사람이 확정한 25개 Feature)로 Logistic Regression·XGBoost를 처음부터 재튜닝한다(Stage 3와 같은 절차, 대상만 직군 하나로 축소).
- `03_5_final_tuning.ipynb` — 위 Stage 3 결과의 `selected_features.csv`·`best_params.json`을 기준선으로, 제한된 LR/XGBoost 조합(725 CV fits)을 탐색하고 refined Train OOF의 threshold 민감도를 확인한다.
- `04_model_comparison.ipynb` — 네 고정 후보(LR/XGB × 튜닝 전/후)를 고정 Test Dataset에서 한 번만 평가하고, SAMPID bootstrap·paired bootstrap·Permutation Importance를 만든다.

세 Notebook 모두 원본은 `notebooks/global/`의 같은 이름 Notebook을 복사해 직군 필터(`job_group == '교육·법률·사회·공공'`)만 추가한 것이라, Global Notebook과 같은 Test 미사용·자동 해석 금지 경계를 그대로 따른다.

## 왜

Global에서 확정한 42개→25개 Feature 선택이 **직군별로도 그대로 유효한지**는 Global Train 전체로는 확인할 수 없다. 직군 하나씩 같은 절차로 돌려서 Global 모델과 비교하기 위해 만들었다.

## 규칙

- 결과 산출물은 `data/result/baseline_42features/modeling/stage_3_local_group3/`, `stage_3_5_local_group3/`, `stage_4_local_group3/`에 저장된다. 다른 직군을 같은 방식으로 돌릴 때는 이 Notebook을 복사해 직군 이름과 `group3` 표기(폴더명·파일명·변수명)를 전부 새 직군에 맞게 바꿔야 한다 — Notebook 안에 그룹명이 여러 곳(폴더 경로·저장 파일명·`target_group` 변수)에 개별적으로 하드코딩돼 있어 한 곳만 바꾸면 나머지와 어긋난다.
- `04_model_comparison.ipynb`는 고정 Test Dataset을 실제로 평가하는 단계다. 실행한 뒤에는 Feature·Hyperparameter·Threshold를 바꾸지 않는다(Notebook 안 경고 문구 참고).
- Stage 4 Test 지표(`data/result/.../stage_4_local_group3/final_test_summary.csv`)가 이 직군에 대해 무엇을 말해주는지의 해석은 여기 포함되어 있지 않다 — 담당자가 직접 판단해서 남겨야 한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. **⬜ 항목은 사람 검토 전이므로 확정된 내용이 아니다.**

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 폴더 역할·Notebook별 절차 설명 | Notebook 안 markdown·주석을 AI가 요약 | ⬜ 미검토 |
| `교육·법률·사회·공공` 직군 선정, Global 25개 Feature를 Local에 그대로 적용하는 방법론 | **사람(choi-1110)이 직접 작성한 Notebook 코드** | ⬜ 미검토 |

- 세션 로그: `작업기록/choi-1110/20260823-로컬그룹3모델링-환경정리및PR준비.md`
