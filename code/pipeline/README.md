# pipeline — 데이터셋 생성 단계

원자료를 읽어 Person-Period, Global/Local Dataset, SAMPID split을 만든다. 다음 연도에서는 `ECOACT`만 Target으로 사용하고 Feature를 합치지 않는다.

원자료 문항을 표준 Feature로 바꾸는 로직은 코드북 대조가 끝난 범위부터 `source_adapter.py`에 추가한다.

---
## 🖊 작성 출처

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| 본문 | AI가 사용자 제공 프로토콜의 모듈 역할을 정리 | ⬜ 미검토 |

- 세션 로그: `작업기록/hanliyagi/20260814-yp2021-공통-파이프라인-뼈대.md`
