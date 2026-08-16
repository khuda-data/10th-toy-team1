# 12. Global 모델 피처 엔지니어링 요약 (2026-08-14~15)

> 목적: "피처 엔지니어링을 해야 한다"는 이야기가 나온 뒤 실제로 짠 코드를 팀원들이 한눈에 볼 수 있게 정리한 문서.
> 세부 세션 로그: `작업기록/choi-1110/20260814-글로벌전처리-자격증훈련일경험-구현.md`, `작업기록/choi-1110/20260815-분석대상-필터-제거.md`

## 뭘 했나 — 한 줄 요약

Global 모델(청년패널2021 기반 취업 예측)에 쓸 feature(예측에 넣을 입력 변수) 목록 중 구현이 안 돼 있던 27개 + 이번에 새로 발견한 결측 처리 버그 2건을 전부 고쳤다. 지금은 `plan/details/11-YP2021-공통-전처리-모델링-프로토콜.md`에 정의된 feature 목록이 전부 실제 값을 가진 상태다.

## 어디에 있나

| 코드 | 역할 |
|---|---|
| `code/pipeline/source_adapter.py` | 원자료(YP2021 설문 원본 컬럼)를 feature로 바꾸는 핵심 로직. 이번 작업의 대부분이 여기 |
| `code/config/yp2021_missing_rules.json` | feature별 결측 처리 규칙(특수 결측 코드 → `Missing`/`NotApplicable` 등) |
| `code/config/features.yaml` | feature 목록·타입(수치형/범주형) 정의 |
| `code/preprocess/build_features.py` | feature를 모델 학습용 행렬로 바꾸는 단계(scikit-learn 연동) |

## 구현한 feature — 그룹별

**자격증 (5개)**: `has_certificate`(자격증 보유 여부), `certificate_count`(개수), `has_major_related_certificate`(전공 관련 자격증 여부), `has_employment_certificate`(취업 관련 자격증), 관련 개수·시간류

**직업훈련 (3개)**: `has_vocational_training`(직업훈련 경험 여부), `vocational_training_count`(횟수), `vocational_training_hours`(총 시간)

**일경험 (2개, 한계 있음 — 아래 "확인 필요" 참조)**: `ever_worked_before`(경험일자리 유무), `past_job_count`(개수), `school_work_experience`(재학중 일경험 유형), `past_work_months`(총 근무개월)

**나머지 22개**: `major_group`(전공계열), `months_since_graduation`(졸업 후 개월 수), 취업준비 노력 12개(`prep_effort_01~12` — 자격증 준비/어학연수/공모전 등 준비 항목별 예·아니오), 시험준비(`exam_prep_experience` 등 3개), 졸업 전후 준비·구직 경험 2개 등

원자료 문항(설문 코드) 대응은 코드북·매핑표(`YP2021…코드북_0227.xlsx`)를 AI가 직접 대조해 확인했다.

## 어떻게 만들었나 — 핵심 규칙 2가지

1. **조사 차수마다 문항이 다르다**: YP2021은 1~4차(2021~2024년) 조사인데, 자격증·훈련 관련 문항은 2~4차에만 있고 1차엔 없다. 이런 경우 1차 행은 "문항 자체가 없음" → 결측으로 남긴다(추정으로 채우지 않음). 반대로 `c720`(취업준비 스펙_자격증)처럼 1~4차 전부 있는 문항을 찾아 대체 경로로 쓴 경우도 있다(`has_employment_certificate`).
2. **"없음(0)"과 "질문 자체를 안 받음(결측)"을 구분한다**: 예를 들어 "자격증 있냐"에 "없다"고 답한 사람은 자격증 개수가 논리적으로 0이어야지 결측이면 안 된다. `_conditional_zero()`라는 헬퍼를 새로 만들어 이 규칙(여부=없음 → 하위 수치는 0, 여부 자체가 결측 → 하위 수치도 결측)을 코드로 강제했다.

## 작업 중 발견해서 같이 고친 버그

기존 코드가 범주형 feature(성별·지역·학력·전공계열 등)를 만들 때, "문항 비해당"(`NotApplicable`, 예: 대학생이 아니라 학교유형 질문이 원래 해당 안 되는 경우)과 "진짜 결측"(`Missing`, 응답 거부·모름)을 구분하도록 설계는 돼 있었는데, 실제 호출부 40곳 중 38곳이 그 구분값을 코드에서 그냥 버리고 있었다(`value, _ = ...`처럼 밑줄로 무시). 그 결과 `student_type`·`university_type`·`major_group` 등에서 "비해당"이었던 4,000건 이상이 전부 "결측"으로 뭉개져 있었다. 헬퍼 3개(`_categorical_from_reason`, `_normalize_categorical`, `_merge_categorical_sources`)를 새로 만들어 7개 범주형 feature 전체를 고쳤다.

## 검증

- `python -m compileall -q code` 문법 검사 통과.
- 실제 원자료로 파이프라인을 재실행해 `global_dataset.parquet`의 결측률·값 분포를 직접 확인. 45개 컬럼 중 100% 결측인 컬럼이 27개 → **0개**로 줄어든 것 확인.
- `student_type`(4,716건)·`university_type`(4,331건)이 이제 `NotApplicable`로 정상 표기됨을 직접 확인(수정 전엔 전부 `NaN`).

## 확인 필요 — 사람 판단 남은 지점 〔AI 제안 · 사람 검토 필요〕

AGENTS.md 대원칙에 따라, 아래는 AI가 코드를 짜면서 편의상 정한 것이지 팀이 확정한 기준이 아니다. `회의기록/안건.md`에도 등록돼 있다.

1. **`major_group`(전공계열) 결측 사유** — 결측 31.8%를 전부 `Missing`으로 분류했는데, 전공 없는 사람(비대학 진학자 등)이 있다면 `NotApplicable`이어야 할 수도 있음. 코드북에 `a413`이 `[공통]`(전원 대상) 태그만 있어 확정 못 함.
2. **`has_major_related_certificate` 임계값** — 전공 관련도 문항(1~4점)에서 3점 이상을 "관련 있음"으로 AI가 임의로 정함. 4점만 인정하는 등 다르게 볼 여지 있음.
3. **`school_work_experience`·`past_work_months` 설계 한계** — 상위 게이팅 문항(예/아니오로 먼저 걸러주는 질문)을 코드북에서 못 찾아 각각 89~97%·96.6% 결측으로 매우 희소함. `past_work_months`는 여러 일자리 총합이 아니라 첫 번째 일자리 기간만 계산한 것.

## 별개로 전달된 이슈 (전처리 스코프 밖, 모델 담당자용)

`build_preprocessor`의 `SimpleImputer`가 `TypeError: boolean value of NA is ambiguous`로 실패한다. pandas의 nullable 타입(`Int64`/`Float64`)을 scikit-learn이 못 받아들여서 생기는 문제로 추정. `build_features.py`에서 숫자형은 `.astype("float64")`, 범주형은 `.astype(object)`로 변환하면 풀릴 것으로 보임(AI 추정, 미검증).

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. **⬜ 항목은 사람 검토 전이므로 확정된 내용이 아니다.**

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| "뭘 했나"·"어디에 있나"·"구현한 feature" | AI가 코드·세션 로그 사실 발췌 | ⬜ 미검토 |
| "어떻게 만들었나"·"발견해서 같이 고친 버그" | AI 구현 내용 요약 (choi-1110 지시로 진행) | ⬜ 미검토 |
| "검증" | choi-1110이 직접 파이프라인 재실행해 확인 | ✅ 2026-08-14~15 choi-1110 |
| "확인 필요" 3건 | AI 제안, 임의 기준 — 아직 팀 확정 안 됨 | ⬜ 미검토 |
| "별개로 전달된 이슈" | AI 추정 원인, 미검증 | ⬜ 미검토 |

- 세션 로그: `작업기록/choi-1110/20260814-글로벌전처리-자격증훈련일경험-구현.md`, `작업기록/choi-1110/20260815-분석대상-필터-제거.md`
