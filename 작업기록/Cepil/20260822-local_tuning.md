---
## 🖊 작성 출처

> `AGENTS.md` 대원칙에 따른 기록.

| 구간 | 내용을 정한 주체 | 사람 검토 |
|---|---|---|
| §1 로컬 직군 모델 튜닝 | 사람이 방향 지시 → AI가 코드 수정 안내 | ✅ 2026-08-22 Cepil |

- 세션 로그: `작업기록/Cepil/20260822-local_tuning.md`

# 2026-08-22 로컬 직군(경영·사무·금융) 모델 튜닝 작업

## 1. 지침 및 프롬프트
- `03_second_model.ipynb` 결과 시각화 코드 및 한글 폰트 깨짐 해결 요청
- `03_5_final_tuning.ipynb`에서 로컬 직군 데이터만 필터링하고 경로를 수정하여 튜닝 진행 요청

## 2. 작업 내용
- 시각화 스크립트 작성 및 윈도우 한글 폰트(`Malgun Gothic`) 적용 완료
- `03_5_final_tuning.ipynb`에서 `OUTPUT_DIR` 및 `STAGE_3_DIR` 변경 사항 안내
- `run_pipeline.py`의 `_subset_bundle`을 불러와서 직군 필터링 적용 안내
- 10MB 미만의 결과물 데이터(`stage_3_local_group1`, `stage_3_5_local_group1`) 커밋 및 푸시 준비

## 3. 검증 방법 및 결과
- 파이썬 스크립트로 matplotlib 시각화 정상 확인
- 노트북 셀 실행을 통해 725번 CV 튜닝 정상 완료 확인

## 4. 남은 작업 및 막힌 부분
- 없음
