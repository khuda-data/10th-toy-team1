# 2026-08-19 Global Model Train/Test 분할 실데이터 검증 + Windows cp949 크래시 수정

- 도구/모델: Claude Code / Sonnet 5
- 브랜치: feat/wjdwlsah-global-split-verification (main에서 분기, PR #4·#5 머지 이후 최신 main 기준)

## 지침 (내가 시킨 것)
1. PR #4·#5가 머지된 최신 main 기준으로 Local Model 데이터셋을 어떻게 만드는지 팔로업 요청 → 기존 `code/pipeline/build_local.py`·`run_pipeline.py`가 이미 구현돼 있음을 확인하고 실제 raw 데이터로 재검증하기로 함.
2. 이후 논의에서: Local 6개 직군 데이터셋 크기가 Global과 꼭 일치할 필요는 없고, 대신 **Global Model 데이터셋을 먼저 §15 규칙(80:20)대로 train/test로 나눈 결과를 독립적인 PR로 올려달라**는 지시.

## AI가 한 일
- 실제 YP2021 raw 데이터(`Toy_project/데이터셋/YP 1~4차 통합 데이터(엑셀).zip`)로 `python -m code.pipeline.run_pipeline --raw-zip ... --run-modeling` 전체 파이프라인을 두 번 실행(1차: 크래시 발견, 2차: 수정 후 정상 완료 재확인).
- **버그 발견·수정**: 1차 실행이 `run_pipeline.py:272`의 완료 안내 `print(f"[{name}] 완료 — ...")`에서 `UnicodeEncodeError`로 죽음 — Windows 콘솔 기본 코드페이지(cp949)가 em dash(`—`, U+2014)를 인코딩 못 함. 실제로는 이 print 직전에 모든 산출물(dataset·split·model·metrics)이 이미 저장 완료된 뒤라 실질적 피해는 없었지만, 스크립트가 실패한 것처럼 보이는 문제였음. `code/pipeline/run_pipeline.py` 상단에 `sys.stdout/stderr.reconfigure(encoding="utf-8")`를 추가해 수정, 2차 실행에서 크래시 없이 끝까지 정상 완료됨을 확인.
- **Global Train/Test 분할 실측 검증**: `code/pipeline/split.py`의 `build_split_ids()`(`StratifiedGroupKFold(n_splits=5, random_state=42)`, `outer_fold=0` 고정 test)를 실제로 실행해 산출된 `split_ids.csv`를 직접 집계.

## 검증 (내가 직접 확인한 것)
- SAMPID(사람) 기준: **Train 5,737명 / Test 1,406명 (80.3% / 19.7%)** — `11-...프로토콜.md` §15 기존 기록치와 정확히 일치.
- Person-Period 행 기준: **Train 12,012행 / Test 2,894행 (80.6% / 19.4%)**.
- Train·Test 사람 집합 교집합 = 0명(겹침 없음) — SAMPID 단위 분할이 실제로 사람 단위로 배타적임을 직접 확인.
- 분할 로직 자체(`split.py`)는 이번에 코드 변경 없음 — 기존 구현이 §15 규칙과 정확히 일치함을 raw 데이터 실행으로 재확인한 것.
- 산출물(`data/result/baseline_42features/` 하위 datasets·splits·models·metrics)은 전부 `.gitignore` 대상이라 이 커밋에는 없음 — 로컬에만 있음.

## 남은 것 / 막힌 것
- 이 작업 다음에 Local Model 6개 직군 데이터셋의 train/test 분할(Global 분할을 그대로 상속받아 리키지 없는지) 검증이 이어짐 — 처음엔 별도 PR로 계획했으나, 최종적으로 `feat/wjdwlsah-local-split-verification` 브랜치 하나에 커밋 2개(이 커밋 → Local 검증 커밋)로 합쳐 PR 1개로 올림. 상세: `작업기록/wjdwlsah/20260819-Local-train-test-분할-실데이터검증.md`.

## 🖊 작성 출처
| 구간 | 작성 주체 | 검토 상태 |
|---|---|---|
| 전체 | AI(Claude Code) — raw 데이터 직접 실행·집계 | ⬜ 미검토 |
