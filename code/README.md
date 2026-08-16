# code — YP2021 공통 분석 코드

**무엇**: 원자료를 Person-Period 데이터셋으로 만들고, Global/Local 모델을 같은 조건에서 실행하는 팀 공용 코드다.

**왜**: 각자가 Notebook을 마지막에 합치는 대신, 처음부터 같은 입력·분할·전처리·결과 형식을 사용해 PR만으로 연결하기 위해 만든다.

먼저 [`AGENTS.md`](AGENTS.md)와 [`../plan/details/06-인터페이스.md`](../plan/details/06-인터페이스.md)를 읽는다.

## 구조

| 폴더/파일 | 역할 | 담당자가 채울 부분 |
|---|---|---|
| `pipeline/` | 원자료 읽기, Person-Period, Global/Local, SAMPID split, 실행점 | YP 원문항을 표준 Feature로 바꾸는 source adapter 보완 |
| `preprocess/` | Feature 계약 검증, Train-only 결측·희소범주·인코딩 | 이력형 Feature 누적·특수결측·분기 처리 |
| `model/` | 다섯 공통 모델의 학습·CV 튜닝 | XGBoost fold별 `scale_pos_weight` 처리, 실행 최적화 |
| `evaluation/` | F1 등 공통 지표와 Permutation Importance | SAMPID bootstrap 95% CI와 Global-vs-Local Δ 지표 |
| `config/` | Feature·KECO·모델 설정 단일 원본 | 팀 합의가 있는 경우에만 갱신 |
| `requirements.txt` | 첫 실행 시 설치할 패키지 | 팀의 실제 실행 환경 확인 후 버전 freeze |

## 실행 흐름

원자료 zip은 Git에 넣지 않는다. 제공받은 `YP2021_EXCEL_*.zip` 경로를 그대로 전달한다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/경로/YP2021_EXCEL_0227.zip"
```

이 명령은 다음 구조 산출물만 만든다.

```text
원자료 → person_period.parquet → global/local_dataset.parquet → split_ids.csv
```

현재 source adapter는 코드북으로 확인된 **기준연도 미취업자 선정·Target·희망직업 이력**을 구현한다. 구직·취업준비 변수는 표본 제한이 아닌 Feature로 남긴다. 전공 대계열·자격증/훈련/일경험 누적과 설문 특수결측 처리가 완성되기 전에는 모델 실행을 의도적으로 막는다. 없는 Feature를 0으로 채워 성능을 내는 것은 금지다.

모든 Feature mapping을 마친 뒤에만 아래처럼 모델을 실행한다.

```bash
python -m code.pipeline.run_pipeline \
  --raw-zip "/경로/YP2021_EXCEL_0227.zip" \
  --run-modeling --model logistic_regression
```

`--tune`은 Train 내부 `StratifiedGroupKFold`만 이용해 공통 탐색 범위를 실행한다. 계산량 때문에 Randomized Search가 필요하면 팀 공통 결정을 먼저 반영한다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록. 분석 기준은 사용자가 제공한 프로토콜에서 가져왔으며, 구현 상태 설명은 AI가 작성했다.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 구조·실행 안내 | AI가 공통 코드 뼈대를 설명 | ⬜ 미검토 |
| Person-Period·분할·전처리·평가 기준 | **사용자 제공 YP2021 공통 전처리·모델링 프로토콜 v1.3** | ✅ 2026-08-14 검토 완료 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
