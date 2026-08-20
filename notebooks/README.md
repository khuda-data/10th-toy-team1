# notebooks — 결과 확인용 Jupyter Notebook

## 무엇

공용 `code/` 모듈을 실행해 표·그래프·중간 결과를 확인하는 Notebook을 둔다.

## 왜

학습·튜닝·평가 로직을 Notebook마다 복사하면 수정이 갈라진다. 재사용 기능은 `code/`에 한 번만 구현하고, Notebook은 실행과 관찰만 맡기 위해 만들었다.

## 규칙

- 긴 모델 구현 코드를 Notebook에 복사하지 않는다. `code/`의 함수를 import한다.
- Notebook에서 나온 결과의 연구적 해석·Feature 선택·모델 선택은 사람이 직접 기록한다.
- 각 Notebook은 데이터·split·실행 조건을 처음에 표시한다.
- 이 저장소의 패키지 이름이 `code`라 Python 표준 라이브러리와 겹칠 수 있다. Jupyter가 저장소 루트에서 시작되지 않으면 `KHUDA_PROJECT_ROOT` 환경변수에 저장소 절대 경로를 지정한다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 폴더 역할·규칙 | 사용자 제공 Global 모델링 준비 요구사항을 AI가 폴더 규칙으로 구조화 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260820-Global-모델링-준비구현.md`
