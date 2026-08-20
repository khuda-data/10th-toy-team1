# 2026-08-21 Global Stage 3.5 Final Hyperparameter Refinement 구현

- 도구/모델: Codex / GPT-5
- 브랜치: `feat/hanliyagi-stage35-final-tuning`

## 지침 (내가 시킨 것)

- Global 모델링의 Stage 3.5로, Test를 전혀 사용하지 않고 Stage 3의 사람이 확정한 25개 Feature와 저장된 최적 파라미터 주변만 제한적으로 재탐색하라고 요청했다.
- LR은 28개 조합, XGBoost는 A(81개) → B(27개) → C(9개) 순서의 세 제한 GridSearch를 수행하고, 고정 SAMPID 5-fold·F1·threshold 0.5·Train-fold-only 전처리·fold별 `scale_pos_weight` 방식을 유지하라고 했다.
- refined 모델 OOF 확률로 0.20~0.80 threshold sensitivity를 계산하되 자동으로 threshold나 최종 모델을 선택하지 말고, 지정 CSV/JSON/OOF parquet과 `03_5_final_tuning.ipynb`를 만들라고 했다.

## AI가 한 일

- `model_config.yaml`에 Stage 1·3 기본 탐색 범위와 분리된 `final_hyperparameter_refinement`를 등록했다. LR 28개, XGB A 81개·B 27개·C 9개 조합만 사용한다.
- `tune_model()`에 단계별 제한 Grid와 탐색하지 않는 고정 모델 파라미터 입력을 추가하고, `final_tuning.py`로 LR 및 XGB A→B→C 순차 탐색·최종 OOF·artifact 저장을 구현했다.
- XGB 외부 GridSearchCV는 `threading`, `n_jobs=-1`로 실행하고 XGB estimator 내부는 `n_jobs=1`로 해 nested parallelism을 피했다. `scale_pos_weight` marker는 기존처럼 각 CV Train fold의 negative/positive ratio로 치환된다.
- `threshold.py`는 refined Train OOF만 받아 0.20~0.80의 Precision·Recall·F1·예측 양성비율과 0.5/OOF F1 최대 threshold 비교표를 계산한다. threshold를 변경하지 않는다.
- `notebooks/global/03_5_final_tuning.ipynb`에 실행 전 점검, Stage 3 기준 파라미터 대조, LR/XGB refinement, 11개 artifact 저장, CV·fold·OOF·threshold 그래프를 추가했다.

## 검증 (내가 직접 확인한 것)

- Python 모듈과 Notebook의 6개 코드 셀이 컴파일됐다. 실제 Global Train의 앞 450 SAMPID/1,007행으로 각 refinement 단계 1개 조합만 남긴 smoke test를 수행해 LR/XGB 순차 탐색, OOF parquet 필수 6개 열, 11개 artifact 생성까지 확인했다. Test는 로드하지 않았다.
- 실제 Global Train 11,925행·5,737 SAMPID·선택 Feature 25개에서 LR 140 fits, XGB A 405 fits, B 135 fits, C 45 fits(핵심 합계 725 fits)를 한 번 실행했다. Stage 3.5 결과는 `data/result/baseline_42features/modeling/stage_3_5/`에만 저장했다.
- 저장 Stage 3 파라미터는 요청서의 LR `C=0.1/l2/balanced`, XGB `depth=3`, `learning_rate=0.03`, `n_estimators=500`, `min_child_weight=5`, `subsample=1.0`, `colsample_bytree=0.8`, fold별 ratio marker와 일치했다.
- 실행 중 sklearn 1.8의 `penalty` deprecation warning이 반복됐지만 GridSearch·OOF·artifact 저장은 완료됐다. 이는 향후 sklearn API 변경 예고이며 이번 지정 `l1/l2` 탐색의 실패가 아니다.

## 남은 것 / 사람 판단 필요

- Stage 3.5 summary와 threshold sensitivity를 보고 Stage 4 후보 또는 threshold 변경 여부를 자동으로 결정하지 않는다. 그 판단 근거와 해석은 담당자가 직접 작성한다.
- 실제 실행 stdout이 경고로 잘려 정확한 초 단위 timer 출력은 보존되지 않았다. 프로세스 관찰 기준 총 실행은 약 1분 내외였으며, 재실행 시 환경 자원에 따라 달라질 수 있다.
