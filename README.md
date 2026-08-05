# 10th-toy-team1 — KHUDA 26-2 10기 1조 (YB) 토이프로젝트

서울 안전 경로 추천 시스템(안)을 향해 논문 리딩 → 설계 → 구현으로 진행 중인 팀 레포.
현재 상태와 확정된 결정은 [`plan/README.md`](plan/README.md)가 항상 최신이다.

---

## 처음 온 팀원은 (3단계)

설치부터 차근차근 필요하면 [`온보딩.md`](온보딩.md)를 보면 된다 (15분 코스). 요약:

1. `git clone https://github.com/khuda-data/10th-toy-team1.git`
2. 터미널 AI(Claude Code / Gemini CLI / Codex CLI) 실행 → **"이 레포의 작업 원칙을 요약해봐"** 라고 물어 [`AGENTS.md`](AGENTS.md)가 로드됐는지 확인
3. 작업 → 끝나면 [`작업기록/`](작업기록/README.md)에 세션 로그를 남기고 push

규칙 전문은 `AGENTS.md` 하나만 보면 된다 (CLAUDE.md·GEMINI.md는 포인터).

---

## 파일 지도

> **유지 규칙**: 새 폴더·중요 산출물을 만들면 그 커밋에서 이 표에 한 줄 추가한다. AI가 자동으로 하게 되어 있다 (`AGENTS.md` §10).

| 경로 | 무엇 | 언제 보나 |
|---|---|---|
| [`온보딩.md`](온보딩.md) | 새 팀원 시작 안내 — 설치부터 첫 세션까지 15분 코스 | 처음 합류했을 때 |
| [`AGENTS.md`](AGENTS.md) | AI 작업 원칙 (단일 소스) — git 루틴·금지 목록·문서/디자인 규칙·산출물 스타일·Windows 팁 | 터미널 AI를 쓰는 모든 세션 |
| `CLAUDE.md` / `GEMINI.md` | AGENTS.md를 가리키는 포인터 | 직접 볼 일 없음 |
| [`plan/README.md`](plan/README.md) | 프로젝트 메타 + 상태 스냅샷 + Phase 로그 | 프로젝트 현황이 궁금할 때 (여기부터) |
| [`plan/CHANGELOG.md`](plan/CHANGELOG.md) | 날짜순 작업 로그 (만든 것·정한 것·막힌 것) | 언제 무엇이 결정됐는지 찾을 때 |
| [`plan/details/01-overview.md`](plan/details/01-overview.md) | 확정/미확정 목록 + 주제 후보 + 열린 질문 | 주제·범위 논의 전 |
| [`plan/details/02-한국어해설-작성지침.md`](plan/details/02-한국어해설-작성지침.md) | 논문 한국어 해설 제작 파이프라인 | 논문 해설을 만들 때 |
| [`plan/details/03-논문인덱스.md`](plan/details/03-논문인덱스.md) | 읽은 논문 인덱스 (한 줄 요약 + 태그) | 어떤 논문을 읽었는지 찾을 때 |
| [`plan/details/04-구현계획-20260729.md`](plan/details/04-구현계획-20260729.md) | 안전 경로 시스템 설계 초안 v0.1 (XGBoost 배치 + 회랑 A*) | 구현 착수 전 필독 |
| [`plan/details/05-협업-통합절차.md`](plan/details/05-협업-통합절차.md) | 여러 명의 결과물을 합치는 4단계 (뼈대→약속→분담→작은 PR) | 협업 작업 시작 전 |
| [`plan/details/06-인터페이스.md`](plan/details/06-인터페이스.md) | 모듈 사이 약속 장부 (API·데이터 형식) — 살아있는 계약서 | 공용 코드·데이터 만들기 전 |
| [`design/DESIGN-apple.md`](design/DESIGN-apple.md) | **앱·PPT·대시보드 등 모든 시각 산출물의 디자인 토큰** | 눈에 보이는 것을 만들 때 (예외 없음) |
| [`design/DESIGN-notion.md`](design/DESIGN-notion.md) | 논문 해설 HTML 전용 디자인 토큰 | 해설 문서를 만들 때만 |
| [`논문/`](논문/) | 논문 1편 = 전용 폴더 1개 (원본 PDF + `[해설]` html/md + assets) | 선행연구를 읽을 때 |
| [`작업기록/`](작업기록/README.md) | AI 세션 로그 — 지침·답변·검증의 시간순 이력 (사람별 폴더) | 세션 시작 전(이어받기)·종료 시(기록) |
| [`scripts/`](scripts/) | 유틸 스크립트 (논문 그림 추출) + git 훅 (작업기록 누락 시 커밋 차단) | 해설 그림 작업·최초 세팅 시 |
| [`code/`](code/) | 전체를 하나로 모은 통합 코드 — 모듈 폴더마다 주인 1명, PR로만 합류 | 코드 작업 전 (`code/README.md` 먼저) |
| [`data/raw/`](data/raw/) | 원본 데이터 — 수정 금지, 출처 기록 필수 | 데이터를 받아올 때 |
| [`data/result/`](data/result/) | 팀 공용·최종 결과물 (통합 코드가 만든 것만) | 합의된 최종 산출물을 저장할 때 |
| [`sandbox/`](sandbox/) | 각자 개인 작업 공간 (`sandbox/<영문이름>/`) — 실험 코드·개인 중간 산출물, 리뷰 없이 자유 | 각자 작업할 때 (여기서 시작) |

---

## 자주 쓰는 규칙 요약 (전문: AGENTS.md)

- 작업 전 `git pull`, 커밋 전 `git diff` 직접 읽기, 세션 끝나면 작업기록 + push
- 코드는 `feat/<영문이름>-<주제>` 브랜치 + PR(리뷰 1명), 문서 md는 main 직푸시 허용
- **PDF 커밋 금지** — 문서는 md로 변환해 커밋 (논문 원본 PDF만 예외, .gitignore가 강제)
- 시각 산출물은 무조건 `design/DESIGN-apple.md`, 코드 경로는 ASCII, 비밀키는 절대 커밋 금지
