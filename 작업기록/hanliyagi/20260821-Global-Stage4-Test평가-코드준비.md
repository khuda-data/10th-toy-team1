# 2026-08-21 Global Stage 4 최종 Test 평가 코드 준비

- 도구/모델: Codex / GPT-5
- 브랜치: `feat/hanliyagi-stage4-test-evaluation`

## 지침 (내가 시킨 것)

- Stage 4 최종 Test 평가를 실행할 수 있는 공용 코드와 `04_model_comparison.ipynb`만 작성하고, Codex는 실제 Notebook 실행·Test 예측·Test metric·bootstrap·permutation importance·결과 파일 생성을 절대 하지 말라고 요청했다.
- Stage 1의 42개 Feature/파라미터와 Stage 3.5의 25개 Feature/동결 파라미터를 source of truth로 사용해 LR/XGB 네 후보를 준비하고, threshold는 0.5로 고정하라고 했다.
- SAMPID 단위 bootstrap, paired bootstrap, 25개 원 Feature 단위 held-out Test permutation importance와 지정 결과 파일 저장 코드를 만들되 실제 실행은 사람이 하도록 요청했다.

## AI가 한 일

- `final_evaluation.py`에 Stage 1/3.5 artifact 기반 네 후보 복원, Train-only 최종 fit, Notebook 실행 시의 Test 예측·요약·CV F1 결합·결과 파일 저장 함수를 추가했다.
- 공용 평가에 Average Precision을 추가하고, SAMPID 단위 F1 bootstrap의 bootstrap mean과 paired F1 difference bootstrap을 구현했다. PI에는 original feature별 positive repeat count를 추가했다.
- `04_model_comparison.ipynb`에 audit → fit → prediction → metrics → bootstrap → paired bootstrap → PI → 저장 → 그래프/최종표 순서를 작성했다. 모든 output은 비어 있다.

## 검증 (내가 직접 확인한 것)

- 실제 Global Test Dataset·Test label·Test 예측에는 접근하지 않는다. 문법/import, 결과 artifact 경로·스키마 정적 확인, synthetic dummy data 단위 검증만 수행한다.
- Python 모듈과 Notebook의 코드 셀 문법 검사를 통과했다. synthetic 6행·3 SAMPID 데이터로 metric/individual bootstrap/paired bootstrap 반환 스키마만 검증했다. 실제 Global Test loader·예측·지표·결과 파일은 실행하지 않았다.

## 남은 것 / 사람 판단 필요

- 사람은 Notebook을 위에서 아래로 한 번 실행해 최초 Test 결과를 확인하고, 이후 Feature·파라미터·threshold·모델을 바꾸지 않는다. 최종 판단과 해석은 사람이 직접 기록한다.

## 이후 사람 제공 결과 보고서

- 사용자가 제공한 `YP2021_Global_모델링_단계별_결과_보고서.md`는 사람의 결과 해석·최종 판단 문서로 원문을 수정하지 않고 `plan/reports/`에 보관한다.
