# 2026-08-18 major_group 백필 버그 수정 + 오버샘플링 완화 방안 논의

- 도구/모델: Claude Code / Sonnet 5
- 브랜치: feat/wjdwlsah-major-group-backfill

## 지침 (내가 시킨 것)
- `major_group` 백필 버그(983명 유실) 원인 분석 요청.
- 로컬에 남아있던 미완료 `git revert`(`62eb88f` 되돌리기 시도)를 발견 — 실수로 merge 후 revert를 눌러서 생긴 상황이라고 확인, "이 상황도 모두 없었던 상황으로 되돌리고 싶어"라고 원복 지시.
- `_backfill_group_a` 수정 방향 확정: "가장 최근에 확인된 실제 전공을 쓴다"는 정의로 가기로 함(2026-08-18) → `needs_fill = filled[column].isna() | filled[column].eq("NotApplicable")`로 수정 지시.
- 미사용 로컬 브랜치 정리 + 브랜치명에 쓸 GitHub 아이디를 `wjdwlsah`로 정정 지시(처음엔 `jungjinmo`로 잘못 지시했다가 본인 아이디가 아님을 확인).
- 오버샘플링 문제(Global: 세 baseline_year 모두 등장 2,947명=41.3%가 전체 행의 59.3% 차지 / Local: 2개 이상 기간 등장 1,504명=53.0%) 완화 방안 논의 — 정정된 데이터셋을 두 벌로 복사해 ① `n_prior_periods` feature 추가 ② `sample_weight`(`1/사람당 행 수`) 가중치 적용, 두 갈래로 각각 다른 처리를 하기로 결정. 시간 부족으로 근본 해결(1인 1행만 남기기, 생존분석/혼합효과 모델)은 배제하고 완화 방안으로 감.
- `sample_weight`를 `scale_pos_weight`처럼 fold-aware로 계산해야 하는지 질문 → "sample_weight는 개인 단위 통계량이라 충돌 없지 않냐"는 반론 제기.
- 구조 정리 지시: 버그 수정은 먼저 별도로 커밋해서 분리하고, 오버샘플링 작업은 새 브랜치에서 시작.

## AI가 한 일
- 로컬 클론(`C:\Users\USER\Documents\KHUDA_10기\10th-toy-team1`)에서 진행 중이던 `git revert` 충돌 발견 → 사용자 확인 후 `git revert --abort`로 원복(다른 팀원 세션 로그 4개·`sandbox/choi-1110` CSV 2개가 삭제될 뻔한 것 방지).
- 미사용 로컬 브랜치 `revert/pr-3-cert-training-workexp` 삭제(`git branch -D`, 원격에 없던 로컬 전용 브랜치).
- `code/pipeline/build_person_period.py`의 `_backfill_group_a`(69~91행) 수정: `needs_fill` 조건에 `NotApplicable` 케이스 추가, docstring을 실제 동작·근거로 갱신.
- 브랜치명 `feat/jungjinmo-major-group-backfill` → `feat/wjdwlsah-major-group-backfill`로 정정(`git branch -m`).
- `code/pipeline/split.py`를 읽고, outer train/test·inner CV 모두 SAMPID 단위로 그룹 분할되어(한 사람의 행이 fold 사이에 쪼개지지 않음) `sample_weight`(개인 단위 통계량)가 전체 데이터셋에서 1회 계산해도 `scale_pos_weight`(집단 통계량)와 달리 fold 간 정보 누수가 없음을 코드로 확인.
- `code/config/yp2021_missing_rules.json`을 읽고 `gender`·`education_level`이 현재 규칙상 `NotApplicable`을 만들지 않아 백필 수정의 영향을 안 받음을 확인.

## 검증 (내가 직접 확인한 것)
- `_backfill_group_a` 수정 후 `ast.parse`로 문법 검증 완료(`py -c "import ast; ast.parse(...)"`).
- ⚠️ **raw 데이터로 파이프라인을 실제 재실행해 983명 회복 여부·Person-Period 행 수 불변을 확인하지는 못했다** — 이 세션 환경에 YP2021 원자료가 없어서 불가능했음. **다음 세션 또는 팀원이 로컬에서 직접 재실행 검증 필요.**
- `git revert --abort` 후 `git status`로 working tree clean·`origin/main`과 일치함을 확인.

## 남은 것 / 막힌 것
- GitHub 자체 장애(2026-08-17 13:40 UTC~, Pull Requests·API·Git 작업 전반 영향) 진행 중이라 이 커밋 push·PR 생성은 장애 복구 후 시도해야 함.
- `_backfill_group_a` 수정을 실제 raw 데이터로 재실행해 983명(2022 baseline 345명·2023 baseline 638명) 중 몇 명이 실제로 회복되는지 확인 필요.
- 오버샘플링 완화는 새 브랜치(`feat/wjdwlsah-oversampling-mitigation`)에서 이어서 진행 — `n_prior_periods`는 `code/config/features.yaml`에 numeric으로 등록해야 실제로 모델 입력에 반영됨(`build_features`가 미등록 컬럼은 조용히 버림). `sample_weight`는 Global 1회 계산, Local은 분할 후 각 Local 데이터셋 안에서 재계산 예정. `tune_model`(`code/model/tune.py`)에 `sample_weight_train` 인자 추가 구현 필요.
