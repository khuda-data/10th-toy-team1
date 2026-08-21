# 2026-08-22 Global 반복관측 Sensitivity Analysis Step 4

- 도구/모델: Codex / GPT-5
- 브랜치: `feat/hanliyagi-global-sensitivity-audit`

## 지침

- 사용자는 Step 4 B/C diagnostics Notebook과 재사용 가능한 진단 함수를 요청했다. 실제 Notebook·Global Train fit·PI·1,000회 bootstrap·Test 접근·결과 해석은 하지 않는다.

## AI가 한 일

- B/C diagnostics Notebook을 각각 만들고, 기존 A Stage 3.5 및 Step 2/3 Train artifact만 읽도록 구성했다.
- OOF subgroup metric, SAMPID paired bootstrap, validation-fold 원 Feature permutation importance helper를 추가했다.

## 검증

- Notebook Python 문법, 공용 helper import를 확인했다.
- 합성 OOF에서 subgroup metric과 짧은 paired bootstrap만 검증했다.

## 남은 것

- 사람이 Notebook을 실행해 진단 결과와 해석을 직접 확인해야 한다.
