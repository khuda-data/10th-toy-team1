# YP2021 Person-Period 기반 전처리 설계안

> 목적: Global/Local 데이터셋을 동일한 기준으로 전처리하기 위한 방법론 설계다. 구현 코드를 제공하지 않으며, 실제 원변수 매핑·코드 작성·검증은 담당자가 수행한다.
>
> 함께 볼 문서: `10-YP2021-직군별-취업예측-계획.md`, `11-YP2021-공통-전처리-모델링-프로토콜.md`, `06-인터페이스.md`, `code/config/features.yaml`, `code/config/yp2021_missing_rules.json`, YP2021 코드북·변수 매핑표

## 1. 분석 단위와 포함 조건

분석 단위는 Person-Period다. 한 행은 한 사람의 기준연도 상태·이력과 다음연도 취업전환 여부를 연결한다.

| 구간 | Feature 기준시점 | Target 시점 |
|---|---:|---:|
| 2021 → 2022 | 2021 | 2022 |
| 2022 → 2023 | 2022 | 2023 |
| 2023 → 2024 | 2023 | 2024 |

한 사람은 조건을 만족하는 만큼 1~3행을 가질 수 있다. 각 구간은 기준연도·다음연도 응답이 유효하고, 기준연도 `ECOACT ∈ {2,3}`, 다음연도 `ECOACT ∈ {1,2,3}`일 때만 만든다.

```text
다음연도 ECOACT = 1     → employment_transition = 1
다음연도 ECOACT = 2, 3  → employment_transition = 0
```

현재 구직·취업준비 여부는 표본을 거르는 조건이 아니라 Feature다.

## 2. 시간·결측 처리 원칙

모든 Feature에는 해당 구간의 baseline year까지 실제로 알 수 있었던 정보만 사용한다. 미래 차수로 과거 Feature 결측을 채우는 future backfill은 금지한다.

결측은 코드북·설문 분기를 대조해 유효 응답, 논리적 0, 비해당(`NotApplicable`), 실제 결측(`Missing` 또는 수치형 `NaN`)으로 구분한다. 특수결측 코드는 변수별 코드북을 확인해 `yp2021_missing_rules.json`에 반영한다. Feature 결측만으로 Person-Period 행을 삭제하지 않는다.

과거 최신값 보완은 모든 Feature에 일괄 적용하지 않는다.

| Feature 성격 | 처리 원칙 |
|---|---|
| 고정·준고정 정보 | baseline 값 우선, 실제 결측이면 과거 최신 유효값 사용 가능 |
| 기준연도 현재 상태 | 이전 상태를 현재값으로 단순 복사하지 않음; 계산 가능하면 재계산 |
| 최근·현재 행동 | 과거값으로 보완하지 않음 |
| 과거 누적 이력 | 단순 복사 대신 baseline까지 관측 이력으로 재구성 |

보완 방향은 `2021→2022`는 2021만, `2022→2023`은 2022 우선 후 2021, `2023→2024`는 2023 우선 후 2022→2021이다.

## 3. 42개 Feature 그룹

| 그룹 | Feature | 처리 핵심 |
|---|---|---|
| A. 고정·준고정 | `gender`, `education_level`, `major_group` | baseline 우선, 실제 결측이면 과거 최신 유효값 |
| B. 현재 상태 | `age`, `region_5`, `student_status`, `student_type`, `university_type`, `months_since_graduation`, `nonemployment_type` | baseline 값; 비해당과 실제 결측 구분 |
| C. 최근·현재 행동 | `recent_job_search`, `recent_employment_prep`, `prep_effort_01~12`, `prep_effort_other`, `currently_preparing_exam` | 과거값 대체 금지; 논리적 0·비해당·실제 결측 구분 |
| D. 과거 누적 이력 | `graduation_prep_experience`, `graduation_job_search_experience`, 자격증·훈련·시험준비·일경험 Feature | baseline까지 이력 재구성, 반복 보고는 가능한 범위에서 중복 제거 |
| E. 시간·구간 | `baseline_year` | Person-Period 생성값; 결측 불가 |

Group C의 `prep_effort_01~12`, `prep_effort_other`는 취업준비 활동을 Multi-Hot으로 바꾼다. 활동 선택은 1, 부모 문항상 활동 없음이 확정되면 0, 비해당은 `NotApplicable`, 실제 응답 누락은 `Missing`으로 처리한다.

Group D에서는 과거에 확실한 경험이 한 번이라도 있으면 경험 여부형 변수는 이후에도 1로 유지할 수 있다. 다만 과거 0과 현재 실제 결측만으로 현재도 0이라고 단정하지 않는다. 횟수·시간·개수는 episode 단위 중복 제거 후 누적하며, 재구성이 불가능하면 수치형 결측으로 유지한다.

## 4. 모델 입력 직전 처리

- 범주형 실제 결측은 `Missing`, 비해당은 `NotApplicable`으로 보존한다. 둘은 희소 일반 범주를 합친 `Other`에 포함하지 않는다.
- 수치형 실제 결측은 모델 Pipeline에서 Train fold median으로만 대체한다. Validation/Test 값으로 median을 계산하지 않는다.
- 상관분석만으로 개별 결측값을 직접 결정하지 않는다. 모델 기반 대체가 필요하면 Train 내부에서만 학습하는 별도 실험으로 기본 분석과 분리한다.

## 5. Global·Local 데이터셋 생성

```text
YP2021 1~4차 원자료
  → 코드북·설문분기·특수결측 확인
  → 기준연도 미취업자 Person-Period 3개 구간 생성
  → 42개 Feature를 A~E 원칙으로 생성
  → 실제 결측·비해당·논리적 0 구분
  → Global Dataset
  → baseline까지 희망직업 이력 결합
  → KECO 6개 직군 분리
  → Local Dataset 6개
```

Local은 Global을 독립적으로 다시 전처리하지 않는 부분집합이다. 희망직업은 각 baseline까지의 정보만 사용하고, 여러 응답이 있으면 최신 실제 응답을 쓴다. 같은 연도에 둘 다 있으면 `c773z`를 `a244z`보다 우선한다. `hope_job_keco`, `hope_job_year`, `hope_job_source`, `job_group`은 메타데이터이며 모델 입력 Feature가 아니다.

한 사람이 여러 행을 가질 수 있으므로 Train/Test는 반드시 `SAMPID` 단위로 그룹 분할한다. Global에서 만든 split을 Local에도 그대로 사용한다.

## 6. 담당자 확인 순서

1. 원자료 문항과 차수 대응 변수를 코드북으로 대조한다.
2. 특수결측·설문 분기·논리적 0을 확인한다.
3. 해당 Feature의 A~E 그룹 원칙을 적용한다.
4. baseline 이후 정보가 섞이지 않았는지, 이력형 중복이 없는지 확인한다.
5. 생성 Feature의 결측률·값 분포를 점검한다.
6. 과거값 사용, 비해당의 0 처리, 이력 중복, 대표 원문항 선택, Feature 삭제처럼 의미를 바꿀 판단은 팀과 공유한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 사용자가 작성한 설계안의 전처리 원칙과 Feature 분류를 팀 문서 경로로 옮겼다. 방법론 판단은 사용자가 정한 내용이며, AI는 저장소 형식에 맞춰 구조화했다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| §1~§6 Person-Period·결측·42개 Feature·Global/Local 전처리 원칙 | **사람(Kim ByungKyu)이 직접 작성한 설계안** | ✅ 2026-08-16 Kim ByungKyu |
| 저장소 경로·상호 문서 링크 | AI가 저장소 형식에 맞춰 정리 | ⬜ 담당자 확인 필요 |

- 원본: `/Users/hanliyagi1/Downloads/YP2021_PersonPeriod_전처리_설계안.md`
- 세션 로그: `작업기록/hanliyagi/20260816-전처리-설계안-푸시.md`
