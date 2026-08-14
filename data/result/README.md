# data/result — 팀 공용·최종 결과물

**통합 코드(`code/`)가 만든 팀 공용 결과물만** 둔다. 개인 실험의 중간 산출물은 자기 `sandbox/<git아이디>/`에.
원칙: **코드로 다시 만들 수 있을 것** — 무엇으로 생성했는지 `../README.md` 출처 기록이나 파일명에 남긴다.

`code.pipeline.run_pipeline`은 아래 폴더를 실행 시 생성한다. 큰 parquet·모델 파일은 커밋하지 않고, 재생성 명령과 버전을 작업기록에 남긴다.

| 경로 | 공용 산출물 |
|---|---|
| `datasets/person_period.parquet` | 세 전환을 합친 분석 대상 기본 행 |
| `datasets/global_dataset.parquet` | Global Model용 Feature·target·메타데이터 |
| `datasets/local_dataset.parquet` | 희망직군이 붙은 Local Model용 행 |
| `splits/split_ids.csv` | Global에서 한 번 고정한 SAMPID Train/Test 소속 |
| `metrics/metrics.csv` | 모델·직군별 고정 평가 지표 |
| `feature_importance/feature_importance.csv` | 원 Feature 단위 Permutation Importance |
| `models/best_params.json` | CV가 선택한 공통 최적 파라미터 |

파일별 컬럼·타입은 [`../../plan/details/06-인터페이스.md`](../../plan/details/06-인터페이스.md)가 정본이다.

## 현재 재생성 기준

- 2026-08-14 v1.3 기준으로 원자료에서 다시 생성했다. Global Person-Period는 14,906행·고유 SAMPID 7,143명이고, Local은 4,603행·고유 SAMPID 2,838명이다.
- `datasets/`와 `splits/`의 파일은 아직 원변수 Feature 구현 전 **구조·표본·분할 검증용**이다. 모델 결과(`metrics/`, `feature_importance/`, `models/`)는 모든 Feature mapping이 완료된 뒤 같은 v1.3 split으로 다시 만든다.
- 이 저장소는 public이므로 개인 단위 원자료에서 파생된 `datasets/*.parquet`, `splits/split_ids.csv`는 커밋하지 않는다. `.gitignore`가 이를 막으며, 팀원은 아래 명령으로 자기 로컬에서 다시 생성한다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/로컬/경로/YP2021_EXCEL_0227 (1).zip"
```

필요한 원자료는 한국고용정보원 YP2021 1~4차 통합 Excel zip이며, 팀에 제공된 로컬 `Dataset&manual/` 폴더에서만 읽는다. 원자료와 생성된 개인 단위 Dataset은 public 저장소에 올리지 않는다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 파일명·형식은 사용자가 제공한 프로토콜을 코드 구조에 맞춰 반영했다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 공용 결과물 목록 | **사용자 제공 YP2021 공통 전처리·모델링 프로토콜 v1.3** | ✅ 2026-08-14 검토 완료 |
| 재생성·보관 안내 | AI가 저장소 규칙에 맞춰 정리 | ⬜ 미검토 |
| v1.3 구조 산출물·표본 수 | AI가 원자료를 공통 코드로 재실행 | ⬜ 사람 확인 필요 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
