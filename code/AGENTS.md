# code/ — YP2021 공통 개발 규칙

루트 `AGENTS.md`에 더해, 이 폴더에서는 아래 규칙을 지킨다.

1. `code/config/`을 유일한 공통 설정 원본으로 사용한다. Feature·KECO 매핑·분할·평가·모델 후보를 코드에 따로 복사하지 않는다.
2. `build_person_period_dataset()`에는 기준연도 데이터와 다음연도의 `ECOACT`만 전달한다. 다음연도의 다른 변수는 어떤 Feature에도 합치지 않는다.
3. Global/Local은 같은 `features.yaml`, `build_preprocessor()`, `model_config.yaml`, `split_ids.csv`를 사용한다. Local만의 임의 Feature·분할·평가 변경은 금지한다.
4. `split_ids.csv`는 Global Dataset에서 SAMPID 기준으로 한 번 만들며, 이후 다시 생성하지 않는다. 모든 Local Dataset은 같은 SAMPID 소속을 따른다.
5. Train에서만 전처리 fit과 튜닝을 한다. Test는 최종 성능·Permutation Importance를 한 번 계산할 때만 쓴다.
6. 원자료 문항 매핑·특수결측·설문 분기는 코드북 대조 전에는 0 또는 유효 범주로 추정하지 않는다. 누락 Feature가 있으면 모델 실행을 막고 담당자에게 드러낸다.
7. 실험은 `sandbox/<git아이디>/`에서 한다. 공통 코드 반영은 모듈별 담당 폴더에 작은 PR로 한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 분석 규칙은 사용자가 제공한 프로토콜을 구현 규칙으로 옮긴 것이다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 1~7 개발 규칙 | AI가 프로토콜을 코드 작업 규칙으로 정리 | ✅ 2026-08-14 팀장 검토 |
| 분석 기준의 원문 | **사용자 제공 YP2021 공통 전처리·모델링 프로토콜 v1.2** | ⬜ 팀 확인 필요 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
