# global — Global 모델링 실행 Notebook

## 무엇

전체 미취업 청년 Person-Period를 사용하는 Global 모델의 단계별 확인 Notebook을 둔다.

## 왜

Global 모델은 [14번 단계별 실행 흐름](../../plan/details/14-Global-모델링-단계별-실행흐름.md)에 따라 사람의 확인을 거쳐 다음 단계로 넘어간다. 각 Notebook이 어느 단계의 확인인지 분명히 남기기 위해 분리한다.

## 규칙

- `00_modeling_check.ipynb`는 Stage 0의 데이터·split 확인용이며 모델 학습·선택·결과 해석을 하지 않는다.
- 이후 Notebook도 `code/` 공용 함수를 import하며, Test를 Feature·모델 선택에 사용하지 않는다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 폴더 역할·Stage 0 경계 | 사용자 제공 Global 모델링 준비 요구사항을 AI가 폴더 규칙으로 구조화 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260820-Global-모델링-준비구현.md`
