# CHANGELOG

> 날짜순 작업 로그. 무엇을 만들었고, 무엇을 결정했고, 무엇이 막혔는지만 적는다.

---

## 2026-08-05 — Phase 2: 팀 협업 세팅 (1조 정정 · PDF→md · AGENTS.md · 디자인 라우팅)

### 만든 것
- "10조" → "1조" 표기 수정(문서 5개) + 폴더명 `git mv` rename. 원격 반영 완료.
- PDF 3종 md 변환 (pymupdf4llm, `write_images=True`): `구현 계획/20260729_수요일_구현계획.md`, `논문/.../buildings-15-02590.md`, `[해설] buildings-15-02590.md`. 그림·표는 각 폴더 `assets/`에 추출.
- 루트에 `AGENTS.md`(팀 공용 AI 작업 원칙) + `CLAUDE.md`/`GEMINI.md`(@AGENTS.md 포인터) 신설. UXC 연구실에서 축적한 터미널 팁(cp949, 한글 경로, Edge headless 플래그, Start-Process 등)을 §7로 이식.
- `DESIGN-apple.md`를 레포에 추가 (UXC 원본의 사본, 원본은 읽기 전용 유지).
- `.gitignore`에 `*.pdf` + `!**/논문/**/*.pdf` 추가. `git check-ignore`로 차단/예외 동작 검증.

### 정한 것
- **PDF는 레포에 커밋하지 않는다. 모든 PDF 내용은 md 변환본으로 커밋** (사용자 결정). 기존 커밋된 PDF 3개는 유지, 논문 원본 PDF는 계속 커밋(출처 자료 예외).
- **AI 작업 규칙의 단일 소스 = 루트 `AGENTS.md`.** CLAUDE.md/GEMINI.md에는 규칙을 적지 않는다.
- **시각 산출물(앱·PPT·대시보드 등)의 디자인 소스 = `DESIGN-apple.md`** (사용자 결정). 해설 HTML만 `DESIGN-notion.md` 유지.

### 알게 된 것 (환경/도구)
- pymupdf4llm 변환 시 한글·공백·대괄호 파일명이 md 속 이미지 링크를 깨뜨림 → **ASCII 이름 임시 사본으로 변환**하고 md만 원래 이름으로 저장 (Edge headless의 ASCII 경로 트릭과 동일 패턴).

### 다음
- 팀원 온보딩: clone → 각자 AI 도구에서 AGENTS.md 로드 확인 ("작업 원칙 요약해봐").
- 해설 PDF 재생성 시 푸터 "10조" 잔존 표기 정리 (로컬 생성용이므로 급하지 않음).

---

## 2026-07-29 — Phase 1: 프로젝트 개설 + 한국어 해설 1호

### 만든 것
- `1조 YB 토이프로젝트/` 폴더 개설. 구조: `plan/`(README·CHANGELOG·details) + `논문/`(논문 1편당 전용 폴더) + `_fig_extract/`(그림 추출 스캐폴딩).
- `plan/README.md`, `plan/details/01-overview.md`, `02-한국어해설-작성지침.md`, `03-논문인덱스.md` 작성.
- 논문 해설 1호: **Vidal-Domper et al. (2025), *Buildings* 15, 2590** — "Eyes on the Street" × 키토 노상강도.
  - `논문/EyesOnTheStreet_Quito_2025/` 생성, 원본 PDF를 `26-2 10기/` 루트에서 이 폴더로 이동.
  - 세그먼트 50개(원문 발췌 + 한국어 번역), insight 배지 46개, 토이프로젝트 매핑 카드 7개.
  - Figure 1·2, Table 1·2를 PyMuPDF 4배율 크롭 → base64 임베드(외부 경로 참조 없음).
  - HTML 3.0 MB → PDF 24쪽, 3.02 MB.

### 정한 것
- **디자인 소스를 `26-2 10기/DESIGN-notion.md`로 고정** (사용자 지시). CB07 CSS는 이 토큰셋에서 파생된 것이라 뼈대는 유지하되, 어긋난 값(heading-1/2/3 크기·자간, body-sm 행간, caption 14px, feature-card 패딩 24px, eyebrow 배지 12px, spacing/radius 토큰화)을 전부 토큰에 맞춰 정렬했다.
- 논문 1편 = 전용 폴더 1개 컨벤션 채택(UXC 연구실 규율 이식).
- 마지막 종합 섹션은 "AgentNotif 매핑" 대신 **"토이프로젝트 매핑"**. 주제 미확정이므로 *적용 후보* 형태로 서술한다.

### 알게 된 것 (환경/도구)
- Edge headless의 머리말·꼬리말 제거 플래그는 이 환경에서 **`--no-pdf-header-footer`**. 구식 `--print-to-pdf-no-header`는 무시되어 날짜·제목·`file:///` 경로·페이지번호가 그대로 찍힌다. 1차 변환에서 헤더가 찍혀 재변환함.
- PyMuPDF로 추출한 영문 텍스트를 콘솔에 직접 print하면 cp949 인코딩 에러 → UTF-8 파일로 덤프한 뒤 읽어야 한다.

### 이탈 기록
- 해설 지침의 "insights는 전체 세그먼트의 30~40%" 권고 대비 **76%(50개 중 38개)**로 높다. 원문 내부 불일치가 9건이라 표시할 지점이 실제로 많았기 때문. 중복·저가치 6블록 + 4행은 잘라냈다.

### 다음
- 주제 결정 (`details/01-overview.md` §4 열린 질문 3개 확인 필요).
- C1(국내 이식) 후보를 살릴 경우 **좌표 단위 사건 데이터 확보 가능 여부**부터 확인 — 여기서 막히면 주제 자체를 바꿔야 한다.
