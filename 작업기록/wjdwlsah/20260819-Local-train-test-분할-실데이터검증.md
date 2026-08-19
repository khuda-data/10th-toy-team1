# 2026-08-19 Local Model 6개 직군 Train/Test 분할 실데이터 검증 (리키지 없음 확인)

- 도구/모델: Claude Code / Sonnet 5
- 브랜치: feat/wjdwlsah-local-split-verification (`feat/wjdwlsah-global-split-verification` 커밋을 포함해서 이어짐 — 처음엔 별도 PR 2개로 계획했다가, 사용자 지시로 **이 브랜치 하나로 통합**해서 PR도 하나만 올림. 커밋은 ①Windows 수정+Global 검증 → ②Local 검증 순서 그대로 유지)

## 지침 (내가 시킨 것)
- Global Model 데이터셋을 §15 규칙(80:20)대로 먼저 train/test로 나눈 뒤, Local Model 6개 직군 데이터셋도 같은 비율로 train/test로 나누되 **Local train은 전부 Global train에만, Local test는 전부 Global test에만 속하도록**(Global test가 Local train에 새어 들어가는 일이 없도록) 만들어달라는 지시.
- 데이터셋 크기 자체가 Global과 Local이 같을 필요는 없다는 점은 이전 대화에서 확인(§12 "유효한 희망직업이 존재하는 행만 Local 후보" 규칙 때문에 Local은 Global의 부분집합).
- 처음엔 Global 검증과 Local 검증을 PR 2개(순차 의존)로 나눠 올렸는데, 이후 "두 PR을 하나로 합칠 수 없냐"는 질문에 **원래 지시한 순서(Global 분할 먼저 → 그 조건대로 Local 분할) 그대로 커밋 2개를 한 PR 안에 유지하는 방식으로 통합**하기로 확정.

## AI가 한 일
- 이 요구사항(같은 비율 + 리키지 없음)은 이미 구현된 코드로 충족됨을 확인 — 새 분할 로직을 만들지 않음:
  - `code/pipeline/split.py`의 `build_split_ids()`가 **Global에서 SAMPID 기준으로 딱 한 번** train/test를 정하고,
  - `code/pipeline/run_pipeline.py`의 `select_split()` 호출(전역 240-241줄, `local_train`/`local_test`)이 직군별 부분집합에도 **동일한 SAMPID→split 매핑을 그대로 적용**함.
  - 즉 한 사람이 Global에서 train이면 그 사람의 모든 Local 행도 train, Global test면 Local도 test로 결정되는 구조라 설계상 리키지가 발생할 수 없음. 이번 세션은 이걸 실제 raw 데이터로 실측 재확인한 것.
- 실제 YP2021 raw 데이터로 Local Dataset(6개 직군, 총 4,603행/2,838명)을 만들고, 앞 PR에서 만든 `split_ids.csv`(Global 기준)를 기준으로 각 직군별 train/test 사람 집합을 집계·대조.

## 검증 (내가 직접 확인한 것)
- **리키지 0건**: Local 전체(4,603행/2,838명) 기준으로 "Local에서 train인데 Global test에도 속한 사람" = 0명, "Local에서 test인데 Global train에도 속한 사람" = 0명.
- **직군별 train/test 분할(사람 수 기준)**:

| 직군 | Train | Test | Train 비율 |
|---|---:|---:|---:|
| 경영·사무·금융 | 657 | 169 | 79.5% |
| 연구·공학·산업기술 | 541 | 139 | 79.6% |
| 교육·법률·사회·공공 | 472 | 104 | 81.9% |
| 보건·의료 | 297 | 88 | 77.1% |
| 예술·디자인·방송·스포츠 | 242 | 55 | 81.5% |
| 서비스·영업·판매·운송 | 197 | 44 | 81.7% |

6개 직군 모두 목표 80:20 근처(77.1%~81.9%)에 들어옴 — 직군별로 별도 stratify를 하지 않고 Global 분할을 그대로 상속받는 구조라 정확히 80.0%은 아니지만, 편차가 ±3%p 이내로 크지 않음을 확인.
- 이 표는 `plan/details/11-...프로토콜.md` §17 최소 표본 기준(정식 비교: 행≥150·사람≥100·양성/음성 각 40 이상)과 대조해도 6개 직군 모두 test 쪽까지 포함해 정식 비교 기준을 충족함(기존 `metrics.csv`의 `comparison_status=formal` 6건과 일치).
- 분할 로직(`split.py`, `run_pipeline.py`의 `select_split` 사용부)은 이번에 코드 변경 없음 — 기존 구현이 요구사항(같은 비율 + 리키지 없음)을 이미 만족함을 raw 데이터로 재확인.
- 산출물(datasets·splits·models·metrics)은 `.gitignore` 대상이라 이 커밋에는 없음.

## 남은 것 / 막힌 것
- 없음 — 이번 요청(Global 분할 → Local 6개 직군 분할, 리키지 없음)은 실측으로 전부 확인 완료.

## 🖊 작성 출처
| 구간 | 작성 주체 | 검토 상태 |
|---|---|---|
| 전체 | AI(Claude Code) — raw 데이터 직접 실행·집계 | ⬜ 미검토 |
