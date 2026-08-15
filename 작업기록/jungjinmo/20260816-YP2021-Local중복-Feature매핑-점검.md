# 2026-08-16 YP2021 Local 데이터셋 중복·Feature 매핑 점검

- 도구/모델: Claude Code / Sonnet 5
- 브랜치: main (문서 작업, 코드 변경 없음 — 원자료 실행 산출물은 `.gitignore`로 로컬에만 존재)

## 지침 (내가 시킨 것)

세션 안에서 순서대로 요청한 내용:

1. 원래 3,921행이 업데이트된 GitHub 문서상 4,603행으로 늘어난 걸로 집계됐는데, 문서에 명시된 수치가 있는지 + AI가 직접 계산해서도 확인.
2. (파이프라인 실행 후) 실제로 수치가 맞는지 확인.
3. 앞으로는 신버전(v1.3) 계획 기준으로 진행할 것 확인 + 산출물 parquet 파일 저장 위치 제시.
4. Local Model 전처리는 `code/pipeline/build_local.py` 기반으로 진행할 것.
5. `strict=False`로 Local 전처리 시 최소 표본 기준을 통과하는 직군이 몇 개인지 미리 파악.
6. 247명 중복이 나타난 원인과, 그대로 두면 생기는 리스크 설명.
7. `C:\Users\USER\Documents\KHUDA_10기\Toy_project\YP2021_Global_Local_데이터셋_전처리_업무안내.md` 추가 숙지.
8. 247명 중복 원인·리스크를 더 구체적으로 재설명.
9. "4,816명" 수치의 출처 확인, 3,185명과의 관계 정리.
10. 이 중복 수치가 Local Model 데이터셋을 만드는 과정에서 나온 수치가 맞는지 확인.
11. 247명 수치가 문서에 어떤 근거로 명시됐는지 + 새로 계산한 값이 나온 조건과 비교 설명.
12. 247명의 근거였던 "공식 파이프라인 검증치"가 타당한 검증치인지 평가.
13. 매핑 안 된 31개 Feature에 대한 지침이 GitHub 저장소 안에 있는지 확인.
14. (지금) 이 내용을 `작업기록/jungjinmo`에 커밋·푸쉬.

## AI가 한 일

- 로컬 클론(`C:\Users\USER\Documents\KHUDA_10기\10th-toy-team1`)에서 실제 원자료 zip(`Toy_project/데이터셋/YP 1~4차 통합 데이터(엑셀).zip`)을 찾아 `code.pipeline.run_pipeline`을 처음부터 끝까지 직접 실행해 `person_period.parquet`(14,906행)·`global_dataset.parquet`·`local_dataset.parquet`(4,603행)을 로컬에 재생성했다.
- 생성된 parquet을 직접 집계해 Global/Local 행수·고유인원·직군별 표본을 `data/result/README.md`, `plan/details/11-YP2021-공통-전처리-모델링-프로토콜.md` 기록치와 전부 대조해 일치를 확인했다.
- `strict_features=False/True`가 표본 크기에 영향을 주지 않음을 코드(`build_global.py`, `build_local.py`)로 확인하고, `run_pipeline.py`의 `_local_status()` 판정 기준을 6개 직군에 직접 적용해 전부 formal 통과함을 확인했다.
- `git log`와 커밋 diff(`8afc601` 등)로 "247명" 수치의 유래를 추적했다 — choi-1110이 8/14 20:22에 원자료를 직접 스크립트로 돌려 계산한 값(구간1∩구간3, `job_seeker`/`recent_employment_prep` 조건 포함)이며, 비교 대상이던 "hanliyagi 검증치(1,444/884/950)"는 같은 날 16:44 v1.3 정책 변경(구직조건 제거)으로 이미 폐기된 스냅샷이었음을 커밋 타임스탬프로 확인했다.
- `person_period.parquet`/`local_dataset.parquet`을 직접 `groupby`해 현재 공식 정의(v1.3, 구직조건 없음) 기준 중복 규모를 재계산했다.
- `code/config/features.yaml`(42개 Feature)과 `local_dataset.parquet` 컬럼 결측률을 전수 대조하고, `code/config/yp2021_missing_rules.json`·`plan/details/11-...프로토콜.md` §6·§28·`plan/details/06-인터페이스.md`를 대조해 미매핑 Feature 현황과 관련 지침 유무를 확인했다.

## 검증 (내가 직접 확인한 것)

**Global/Local 표본 재현**
- Global: 14,906행 / 고유 7,143명 (전환별 6,010 / 4,916 / 3,980), Local: 4,603행 / 고유 2,838명(취업 1,633 / 미취업 2,970) — 원자료 재실행 결과가 저장소 문서와 정확히 일치.
- 6개 직군(경영·사무·금융 1,282행/826명, 연구·공학·산업기술 1,038행/680명, 교육·법률·사회·공공 902행/576명, 보건·의료 593행/385명, 예술·디자인·방송·스포츠 446행/297명, 서비스·영업·판매·운송 342행/241명) 전부 formal 최소표본기준(행≥150, 고유SAMPID≥100, 취업·미취업 각 ≥40) 통과 — exploratory·제외 0개.

**247명 중복 재검증**
- "247명"은 `job_seeker`/`recent_employment_prep` 조건이 걸린 v1.2 정의 기준값. 현재 v1.3(구직조건 없음, `build_person_period.py`가 실제 구현) 기준으로 같은 대상(2021년·2023년 baseline 동시 등장)을 재계산하면:
  - **Global** 2021∩2023 = 3,185명 (247명의 직접 정정치), 2021∩2022 = 4,241명, 2022∩2023 = 3,284명, 세 구간 전부 = 2,947명, 2개 이상 등장 합집합 = **4,816명**(고유 7,143명의 67%).
  - **Local**(4,603행/2,838명 기준, Local Model 데이터셋 자체의 수치) 2021∩2023 = **304명**, 2021∩2022 = 468명, 2022∩2023 = 1,254명, 세 구간 전부 = 261명, 2개 이상 등장 합집합 = **1,504명**(고유 2,838명의 53%).
- 커밋 타임스탬프 대조: hanliyagi v1.3 반영(2026-08-14 16:44, 커밋 `eaf207d`) → choi-1110 247명 계산(19:28~20:22, 커밋 `ab7a972`/`8afc601`) 순서로, choi-1110이 참조한 "공식 파이프라인 검증치(1,444/884/950)"는 그 시점 기준 이미 3~4시간 전에 main에서 폐기된 값이었음을 확인. 즉 247명은 검증 방법론 자체는 정상이었으나, 검증 대상이 이미 팀이 채택하지 않기로 한 정의였다는 한계가 있음.

**Feature 매핑 현황**
- 42개 중 8개 완료(`gender`, `age`, `region_5`, `baseline_year`, `education_level`, `student_status`, `nonemployment_type`, `recent_job_search`), 3개는 결측사유 재확인 필요(`student_type` 46.0%, `university_type` 38.7%, `recent_employment_prep` 34.6% 결측 — 실제결측/비해당 구분 미확인), 31개는 100% 결측(`source_adapter.py`에 관련 코드 자체 없음, `yp2021_missing_rules.json`에도 항목 없음).
- `plan/details/11-...프로토콜.md` §6·§28에 "무엇을 만들지"는 문서화돼 있으나, "원자료 어느 컬럼(코드)인지"는 `features.yaml:30`의 `prep_effort`용 주석(`y**c701a~c`) 1건 외에는 저장소 어디에도 없음을 확인.

## 남은 것 / 막힌 것

- **247명 표기 정정 필요**: `작업기록/choi-1110/20260814-글로벌모델-전처리-설계.md`에 정정치로 남아있는 247명은 이미 폐기된 v1.2 기준값 — 현재 v1.3 기준 정확한 값(Global 3,185명/4,816명, Local 304명/1,504명)을 팀에 공유하고 필요하면 문서를 다시 정정해야 함.
- **중복 처리 방침 미확정**: SAMPID 그룹 분할(`split.py`)로 Train/Test 누수는 막혀 있으나, 통계적 독립성 위반·특정 인물군(세 구간 모두 등장하는 장기 미취업자 성향) 과대표집 문제는 choi-1110 작업기록에도 "사용자 판단 대기"로 남아있고 아직 팀 결정이 없음. 실제 규모(Local 1,504명, 53%)가 기존에 알려진 것보다 훨씬 크다는 점을 팀에 알려야 함.
- **31개 미매핑 Feature 원변수 매핑**: 전공 대계열, 자격증 4개, 직업훈련 3개, 시험준비 3개, 일경험 4개, 취업준비 활동유형 등 15개 — 코드북(`청년패널2021 1-4차 조사 코드북_0227(1).xlsx`/`매핑표_0227(1).xlsx`) 대조가 전혀 안 된 상태. `--run-modeling` 실행 전 필수 선행 작업(`build_features.py`가 strict 모드에서 이 컬럼들이 없으면 실행 자체를 막음).
- `student_type`/`university_type`/`recent_employment_prep` 결측치가 "진짜 결측"인지 "비해당"인지 코드북 재대조 필요.
- 이 세션에서 로컬에 재생성한 `data/result/datasets/*.parquet`, `data/result/splits/split_ids.csv`는 `.gitignore` 규칙(공개 저장소 개인 파생 데이터 비커밋)에 따라 이 커밋에 포함하지 않음 — 이 세션 로그 md 파일만 커밋.

---

## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 지침(질문 목록) | **사람(jungjinmo)이 직접 제시** | ✅ 2026-08-16 jungjinmo |
| Global/Local 표본·중복 재계산 수치 | AI가 실제 원자료로 공식 코드(`code.pipeline.run_pipeline`)를 직접 실행해 산출 — 재현 가능 | ⬜ 팀 최종 확인 필요 |
| 247명 검증치 타당성 평가(커밋 타임스탬프 대조) | AI가 `git log` 사실관계만 대조 — 해석·판단은 사실 기반이나 팀 논의 필요 | ⬜ 팀 확인 필요 |
| Feature 매핑 현황·미매핑 목록 | AI가 코드(`source_adapter.py`, `yp2021_missing_rules.json`)와 산출물 결측률 대조로 확인 | ⬜ 담당자 확인 필요 |
| 남은 것 항목의 우선순위·처리 방침 | AI는 사실만 나열, 결정은 사람 몫 | ⬜ 팀 판단 대기 |

- 세션 로그: 이 파일 자체가 세션 로그임
