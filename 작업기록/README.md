# 작업기록 — AI 세션 로그

> 규칙: 루트 `AGENTS.md` §9. **세션 1개 = 파일 1개.** 경로: `작업기록/<영문이름>/YYYYMMDD-<주제>.md`
>
> **직접 쓸 필요 없다 — AI가 자동으로 남기게 되어 있다** (AGENTS.md §9에 AI 지시로 명시).
> 깜빡한 커밋은 pre-commit 훅이 막아준다 (활성화: `git config core.hooksPath scripts/githooks`, 온보딩.md 참조).

## 템플릿 (아래 블록을 복사해서 시작)

```markdown
# YYYY-MM-DD <주제 한 줄>

- 도구/모델: (예: Claude Code / Opus, Gemini CLI / 2.5 Pro, Codex CLI / GPT-5)
- 브랜치: (예: feat/hoyeol-risk-model, 문서 작업이면 main)

## 지침 (내가 시킨 것)
- 프롬프트 요지를 순서대로. 잘 먹힌 중요한 프롬프트는 원문 그대로 남긴다.

## AI가 한 일
- 변경/생성 파일 목록 + 각 한 줄 설명

## 검증 (내가 직접 확인한 것)
- 실행한 명령·확인한 화면과 그 결과. "AI가 됐다고 함"은 검증이 아니다.

## 남은 것 / 막힌 것
- 다음 세션에서 이어받을 것. 막혔으면 뭘 시도했고 뭐가 안 됐는지.
```

## 팁

- 다음 세션을 시작할 때 AI에게 직전 로그 파일을 읽히면 이어서 작업된다: "작업기록/hoyeol/20260805-repo-setup.md 읽고 이어서 해줘"
- 실제 작성 예시: [`hoyeol/20260805-repo-setup.md`](hoyeol/20260805-repo-setup.md)
