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

## 결측률·값 분포 전체 점검 (2026-08-16 추가)

`data/result/datasets/global_dataset.parquet` 기준으로 42개 Feature 전부를 훑었다. 전체 표는 `sandbox/choi-1110/global_feature_profile_20260816_after_fix.csv`(아래 버그 수정 반영 후 최종본), 수정 전 스냅샷은 같은 폴더의 `global_feature_profile_20260816.csv`.

- Person-Period 14,906행·7,143명은 그대로 유지 — Group A/D 보완이 행 수를 바꾸지 않는다는 §2 원칙대로 동작함을 재확인.
- 자격증·훈련·시험준비 계열 8개는 전부 결측 40.32%(6,010건)로 동일 — 1차 조사에 해당 문항이 없어서 생기는 구조적 결측(소스 코드 주석에도 명시)이라 정상.
- `school_work_experience`는 결측 96.36%일 뿐 아니라, **결측이 아닌 나머지 값도 전부 1**이어서(0인 값이 하나도 없음) 사실상 변별력이 없는 상태 — 기존 안건함 항목("설계 한계 검토")을 뒷받침하는 구체 수치.

**발견해서 바로 고친 버그**: `education_level`·`student_status` 두 범주형 Feature에서 같은 코드값이 `"2"`/`"2.0"`처럼 서로 다른 문자열 범주로 쪼개져 있었다. 원인은 원자료 연도별로 결측 유무가 달라 컬럼 dtype이 int64/float64로 들쭉날쭉했는데, `_categorical_from_reason`(`source_adapter.py`)이 이를 그대로 문자열화하면서 표기가 갈린 것 — 예를 들어 `education_level=2`인 11,425명이 모델 입력에서 두 범주로 쪼개져 원-핫 인코딩 신호가 반토막 나는 문제였다. 정수 코드로 캐스팅한 뒤 문자열화하도록 고쳤다(`_categorical_from_reason`은 `gender`·`region_5`·`education_level`·`student_status`·`student_type`·`university_type`·`major_group` 7개 범주형 Feature가 공통으로 거치는 지점이라 한 번에 다 고쳐졌다). 수정 후 전체 파이프라인을 재실행해 중복 카테고리 0건, 행/인원 수 불변을 확인했다 — 정의를 고르는 판단이 아니라 타입 버그라 사람 확인 없이 바로 적용함.

이 재실행 과정에서 `major_group` 결측률이 수정 전 스냅샷(31.76%)에서 수정 후(25.16%)로 달라졌는데, 이건 버그 수정 때문이 아니라 **`data/result/`가 git에 커밋되지 않는 로컬 산출물**이라 이전 스냅샷이 Group A 백필(`ead97c9`)을 반영하지 않은 오래된 로컬 빌드였기 때문이다. 25.16%는 8/16 세션 기록(25.2%)과 일치해 지금 값이 최신 코드를 정확히 반영한 것으로 확인됨.

## 해결됨 (2026-08-16)

1. **`school_work_experience` 게이팅 문항 발견·수정** — 상위 여부 문항(예/아니오로 먼저 걸러주는 질문)을 코드북에서 못 찾아 결측이 97.9%까지 치솟았던 문제. 일반 코드북(`[YP2021]...코드북_0227.xlsx`, 'A(학교생활)' 시트)에서 직접 찾음: 2~4차는 `a172`("[졸|재학중일] 재학 중 일자리 경험 여부", 1=있다/2=없다), 1차는 같은 라벨의 `a601`이 게이트다. `a172=2`(없다)면 하위 문항(`a186_1`)이 원래 안 물어봐서 비어 있던 것이지 결측이 아니었음 — 논리적 0으로 채우도록 `source_adapter.py` 수정. 재실행 검증 결과 결측 **97.9% → 81.3%**(`NaN 12116 / 0(없음) 2247 / 1(있음) 543`)로 줄었다. 남은 81.3%는 이 게이트 문항 자체가 "졸업생 대상"으로 한 번 더 걸러지는 구조라 정상적인 비해당이다. `past_work_months`는 이 게이트와 무관한 별개 문항군(`d503`/`d532`/`d577` 등 경험일자리 시작·종료 시점)을 써서 **이번엔 해결 안 됨** — 기존 "1번째 일자리만 계산" 한계와 `JOBWAVE`/`JOBSEQ` 로스터 데이터 부재 문제가 그대로 유효.
2. **`has_major_related_certificate` 임계값 확정** — 전공 관련도 문항(`e307_1`)의 정확한 척도 문구를 코드북에서 확인: 1=전혀 없다/2=없는 편이다/3=어느 정도 관련이 있다/4=매우 관련 깊다. **AI가 이 문구와 "3점 이상 채택 시 77%(941/1215명), 4점만 채택 시 43%(520/1215명)"라는 비율 차이를 근거로 제시** → choi-1110이 그 근거를 검토해 **3점 이상을 "관련 있음"으로 확정**(2026-08-16). 판단 근거·최종 채택 과정은 `code/pipeline/source_adapter.py`의 `has_major_related_certificate` 계산부 주석 참고.
3. **`major_group`(전공계열) Missing/NotApplicable 재분류** — 통합설문지 PDF 47쪽(문1)에서 `a413`이 "대학교 또는 대학원에 재학 중인 경우"만 응답하는 문항("5-2. 재학생 공통" 섹션)임을 확인. `student_type`이 `NotApplicable`(현재 재학 중 아님)인 사람과 `major_group` 결측이 3733/4716명(79%)으로 크게 겹치는 것을 실제 데이터로 교차검증해, `student_type=NotApplicable`인데 `major_group`도 결측이면 무응답이 아니라 애초에 안 물어본 것으로 보고 `NotApplicable`로 재분류하도록 `source_adapter.py` 수정. 재실행 결과 **`Missing` 3751명 → 18명, `NotApplicable` 4716명(신설)**으로 정리됨(나머지는 원문 근거·데이터 상관관계가 다 확인돼 사람 확인 없이 바로 반영).

## 확인 필요 — 사람 판단 남은 지점 〔AI 제안 · 사람 검토 필요〕

AGENTS.md 대원칙에 따라, 아래는 AI가 코드를 짜면서 편의상 정한 것이지 팀이 확정한 기준이 아니다. `회의기록/안건.md`에도 등록돼 있다.

1. **`past_work_months` 설계 한계** — 여러 일자리 총합이 아니라 첫 번째 일자리 기간만 계산. `JOBWAVE`/`JOBSEQ` 기반 직업력 로스터 데이터가 있어야 정확히 재구성 가능한데 그 파일이 없음(§ 위 "해결됨" 1번 참고).
2. **`major_group` 재분류 후 남은 `Missing` 18명** — `student_type`이 실제 재학 중(1·2·3)인데도 `major_group`이 결측인 소수 사례. 인원이 적어(18명, 전체의 0.12%) 원인을 더 파지 않고 `Missing`으로 남겼는데, 필요하면 개별 확인 가능.

## 별개로 전달된 이슈 (전처리 스코프 밖, 모델 담당자용)

~~`build_preprocessor`의 `SimpleImputer`가 `TypeError: boolean value of NA is ambiguous`로 실패한다.~~ → **해결됨 (2026-08-16)**: 팀원 모델링 착수 전 확인 과정에서 이 버그가 `--run-modeling`을 그대로 막는다는 걸 직접 재현으로 확인 → 전처리팀 스코프 밖이지만 choi-1110 확정 지시로 바로 고침. `build_features.py`에서 숫자형은 `.astype("float64")`, 범주형은 `.astype(object)` 후 `pd.NA`를 `np.nan`으로 치환하도록 수정, `build_preprocessor().fit_transform()` 정상 동작(전체 `--run-modeling` 경로까지) 확인. 상세: `작업기록/choi-1110/20260816-전체피처-결측분포점검.md`.

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
| "결측률·값 분포 전체 점검"·`education_level`/`student_status` 캐스팅 버그 수정 | choi-1110 지시("1번부터 해줘")로 AI가 점검·수정, 타입 버그라 판단 없이 바로 적용. row/인원 수 불변·중복 카테고리 0건은 AI가 데이터로 직접 검증(확인됨) | ⬜ 코드 변경분(`source_adapter.py`) 최종 확인 필요 |
| sklearn nullable-dtype 버그 수정 | choi-1110이 AskUserQuestion으로 "제가 지금 고침" 확정, AI가 수정·검증 | ⬜ 코드 변경분(`build_features.py`) 최종 확인 필요 |
| `school_work_experience` 게이팅 문항 수정 | 코드북·데이터 근거로 AI가 발견, choi-1110이 "확실하면 코드 수정해줘"로 적용 지시 | ⬜ 코드 변경분 최종 확인 필요 |
| `major_group` Missing/NotApplicable 재분류 | 통합설문지 원문 근거 + 데이터 상관관계를 AI가 제시·구현, 판단이 아닌 원문 반영이라 사람 확인 없이 적용(choi-1110의 "어떻게 해결할 수 있을까" 질문에 대한 답으로 진행) | ⬜ 코드 변경분 최종 확인 필요 |
| `has_major_related_certificate` 임계값(3점 이상) | AI가 근거(척도 문구, 3점 이상/4점만 비율 차이) 제시 → **choi-1110이 검토해 확정**, "AI가 판단했다"고 명시하라는 choi-1110 지시대로 기록 | ✅ 2026-08-16 choi-1110 |

- 세션 로그: `작업기록/choi-1110/20260814-글로벌전처리-자격증훈련일경험-구현.md`, `작업기록/choi-1110/20260815-분석대상-필터-제거.md`, `작업기록/choi-1110/20260816-전체피처-결측분포점검.md`
