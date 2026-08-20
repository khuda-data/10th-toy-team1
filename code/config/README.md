# config — 팀 공통 분석 설정

**무엇**: Feature 목록, KECO 직군 매핑, 모델·분할·평가 설정을 한 곳에 둔다.

**왜**: Global/Local과 팀원별 구현이 같은 실험 기준을 읽게 하려는 폴더다. 코드 안에 같은 값을 복사하지 않는다.

**규칙**:

- `features.yaml`, `keco_mapping.csv`, `model_config.yaml`의 분석 의미를 바꾸는 값은 팀 합의와 프로토콜 갱신 없이 변경하지 않는다.
- `yp2021_missing_rules.json`은 YP2021 코드북에서 확인한 **변수별** 특수결측 코드와 결측 사유를 둔다. 숫자 범위로 일괄 결측 처리하지 않으며, 새 원변수를 추가할 때는 이 파일에 코드북 근거를 먼저 추가한다.
- 실제 YP2021 문항명·특수결측 코드의 매핑은 코드북을 확인한 source adapter에서 처리한다. 이 폴더의 Feature 이름은 adapter가 만들어 내야 하는 표준 이름이다.
- 하이퍼파라미터 범위 축소가 필요하면 Global과 모든 Local에 같은 변경을 적용하고 이유를 기록한다.
- `model_config.yaml`의 `official_global_models`는 현재 공식 Global 비교 대상만 정한다. 다른 `models:` 항목은 기존 코드 호환성을 위해 유지한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 아래 기준은 사용자가 제공한 프로토콜을 코드 설정 형식으로 옮긴 것이다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 폴더 규칙·설정 파일 역할 | AI가 프로토콜을 코드 구조로 정리 | ⬜ 미검토 |
| `features.yaml` 공통 Feature·전처리 기준, `keco_mapping.csv` 6개 직군 매핑, `model_config.yaml` 모델·평가·분할 설정 | **사용자 제공 YP2021 공통 전처리·모델링 프로토콜 v1.3** | ✅ 2026-08-14 검토 완료 |
| `official_global_models`의 LR·XGBoost 목록 | **사람(Kim ByungKyu)이 직접 지시한 2026-08-20 모델링 준비 결정** | ✅ 2026-08-20 Kim ByungKyu |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
