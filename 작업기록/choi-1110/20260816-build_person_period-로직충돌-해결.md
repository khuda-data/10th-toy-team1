# 2026-08-16 — build_person_period.py 브랜치 간 로직 충돌 해결

## ① 내가 준 지침 (요지)

- "13번 문서(`plan/details/13-YP2021-PersonPeriod-전처리-설계안.md`)가 새로 나왔는데, 지금까지 한 것과 비교해서 뭘 더 해야 하는지 알려줘"
- (비교 결과를 확인한 뒤) "우선 1번, 2번 먼저 해줘" — ① `git pull origin main` ② `build_person_period.py` 로직 충돌 해결(hanliyagi와 대조해서 `target_ecoact` 필터 포함 여부 합의)
- 충돌 파일이 예상보다 많다는 보고에 대해: "①번은 main 채택, ②번(문서 서술 차이)은 기존 규칙과 새 규칙이 충돌되면 새 규칙(main 쪽)을 따르라"
- 중간에 "안건.md에 있는 `target_ecoact.isin([1,2,3])` 조건을 hanliyagi가 정한 그대로 추가해줘"로 재확인
- "우선 어떤게 충돌이고 문제였고 어느걸 바꿨는지 main 브랜치에 푸시해줘"

## ② AI가 한 일

1. `git pull` 대신 `origin/main`을 fetch해 로컬 `main`을 fast-forward(`076e08a` → `e01c5ae`, 13번 설계안 등 4커밋 반영).
2. `feat/choi-1110-cert-training-workexp-features`에 `main`을 병합 시도(커밋 없이)해서 실제 충돌 범위를 확인 — 예상했던 `build_person_period.py` 1개가 아니라 **5개 파일**(`code/pipeline/build_person_period.py`, `plan/details/06-인터페이스.md`, `plan/details/11-YP2021-공통-전처리-모델링-프로토콜.md`, `업데이트.md`, `회의기록/안건.md`)에서 충돌 발생.
3. 무엇이 문제였는지 원인 확인:
   - `build_person_period.py`: 나(choi-1110)와 hanliyagi가 같은 날(2026-08-15) 같은 목표("구직·취업준비 필터 삭제")로 각자 독립적으로 코드를 고쳤는데, hanliyagi의 main 쪽에만 `merged["target_ecoact"].isin([1,2,3])` 검증이 추가로 들어있었음. 이 조건이 없으면 다음연도 응답이 무효(1/2/3이 아닌 값)일 때도 `employment_transition`이 자동으로 0(비취업)으로 기록될 수 있음.
   - `06-인터페이스.md`, `11-...프로토콜.md`: 내 브랜치는 2026-08-14 기준 v1.2 스타일 문서를 소폭만 고친 상태였고, main은 그 사이 hanliyagi가 v1.3 정본으로 전면 재작성 — 같은 내용을 서로 다른 구조·문장으로 담고 있어 기계적 병합이 불가능했음.
   - `업데이트.md`, `회의기록/안건.md`: 실질 충돌은 아니고, 양쪽이 같은 위치(파일 맨 위/같은 표 구간)에 서로 다른 항목을 각자 추가해서 발생.
4. 사용자 확인을 거쳐 해결:
   - `build_person_period.py`: main의 `target_ecoact.isin([1,2,3])` 필터를 채택. 13번 설계안 §1("다음연도 `ECOACT ∈ {1,2,3}`일 때만 행을 만든다")과 일치함을 근거로 제시했고, 사용자가 명시적으로 확정.
   - `06-인터페이스.md`, `11-...프로토콜.md`: main(v1.3 정본, 13번 설계안과 이미 일치) 버전으로 통일. 내 브랜치가 이 두 문서에 낸 변경은 5줄 미만이고 main의 재작성에 이미 포함된 내용이라 유실 없음을 diff로 확인.
   - `업데이트.md`, `회의기록/안건.md`: 양쪽 항목 모두 보존하며 날짜순으로 재정렬. 안건함의 "로직 충돌" 항목은 해결됨으로 표시.
5. `feat/choi-1110-cert-training-workexp-features` 브랜치에 병합 커밋(`820ff36`) 생성 — **코드 변경(`build_person_period.py`)은 팀 규칙(AGENTS.md §8, 코드는 브랜치+PR)에 따라 아직 이 브랜치에만 있고 main에는 올리지 않음.**
6. main에는 문서만 직접 갱신해 푸시: `업데이트.md`에 이번 해결 내용 요약 추가, `회의기록/안건.md`의 해당 항목을 해결됨으로 표시, 이 세션 로그 추가.

## ③ 검증 방법과 결과

- `code/pipeline/build_person_period.py` 병합 결과를 `python -c "import ast; ast.parse(...)"`로 문법 검증 — 정상.
- `git diff <병합기준커밋> HEAD -- 06-인터페이스.md 11-...프로토콜.md`로 내 브랜치가 이 두 문서에 낸 변경이 main의 재작성 내용에 이미 포함돼 있는지 확인.
- 병합 후 `git diff --name-only --diff-filter=U`로 미해결 충돌이 없는지 확인.

## ④ 남은 것

- **hanliyagi의 최종 확인이 아직입니다.** `target_ecoact` 필터를 main 쪽으로 채택한 것은 choi-1110이 13번 설계안을 근거로 판단한 것이지, hanliyagi와 직접 대조한 결과가 아닙니다. 안건함 원래 항목이 "PR 머지 전 choi-1110·hanliyagi가 직접 대조해서 정해야 함"이라고 명시했던 만큼, PR을 실제로 머지하기 전에 hanliyagi 확인이 필요합니다.
- 코드 변경(`build_person_period.py` 포함 병합 커밋 `820ff36`)은 아직 `feat/choi-1110-cert-training-workexp-features` 브랜치에만 있고 origin에 푸시되지 않았습니다. hanliyagi 확인 후 push → PR 절차로 진행합니다.

---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| `target_ecoact` 필터를 main(hanliyagi) 쪽으로 채택 | AI가 13번 설계안 근거를 제시 → **사람(choi-1110)이 직접 확정 지시**("main 채택", "hanliyagi가 정한 거로 해줘") | ✅ 2026-08-16 choi-1110 |
| `06`/`11` 문서 충돌을 main(새 규칙) 기준으로 통일 | AI가 근거(내 브랜치 변경분이 main 재작성에 포함됨) 제시 → **사람(choi-1110)이 직접 확정 지시**("새 규칙을 따라야 해") | ✅ 2026-08-16 choi-1110 |
| `업데이트.md`·`안건.md` 병합·재정렬 | AI가 기계적으로 처리(실질 판단 아님) | ⬜ 최종 형식 확인 필요 |

- 세션 로그: 이 파일 자체가 세션 로그임
