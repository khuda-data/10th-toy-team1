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
- paired bootstrap은 반복마다 수천 개 DataFrame을 만들던 구현을 SAMPID별 TP·FP·FN 사전 집계 후 NumPy 합산 방식으로 변경했다. 같은 SAMPID 복원추출·반복 수·seed·F1·percentile CI 정의를 유지한다. 합성 OOF에서 이전 행 재구성 정의와 bootstrap mean·CI가 일치함을 확인했다.
- 사용자가 제공한 B/C 반복관측 민감도 결과 보고서 원문을 `plan/reports/`에 보관하고, 실행된 Step 2~4 Notebook 및 B/C locked·tuning·diagnostics artifact를 커밋 대상으로 준비했다. `.DS_Store`와 반복관측 sensitivity 범위 밖 결과물은 제외한다.

## 남은 것

- 사람이 Notebook을 실행해 진단 결과와 해석을 직접 확인해야 한다.
