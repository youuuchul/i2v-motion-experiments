# Project context for Claude

이미지(+텍스트) → 비디오 실험 워크스페이스. 다른 팀원들과 병렬 작업 후 머지할 예정이라 **모듈 경계**가 중요함.

## 비디오 스펙 (기본값)
- 종횡비: **9:16 (세로, Reels/Shorts)** — 가로 출력 금지, 반드시 크롭/리사이즈
- 길이: 3~15초, **1차 목표 5초**
- fps: 24 (모델 기본값 사용 시 리샘플)
- 해상도: 576x1024 또는 모델 네이티브의 9:16 근사값

스펙 상수는 `configs/presets/` YAML에만 두고, 코드에서 하드코딩 금지.

## 아키텍처 원칙
- `src/i2v/core/`의 `BasePipeline` 인터페이스만 외부에서 의존. 모델 구현은 `src/i2v/models/<name>.py`.
- 새 모델 추가: 파일 하나 + `registry.register("name")` 데코레이터 + `configs/models/<name>.yaml`.
- 학습/서빙/평가는 서로 import하지 않음 (공통은 `core`/`utils` 경유).
- 실험 설정은 YAML → `load_experiment(path)`. 코드에 하이퍼파라미터 박지 말 것.
- Phase 2 LLM 프롬프트 생성은 `src/i2v/prompts/` 안에서 독립 호출 가능해야 함 (비디오 파이프라인과 디커플).

## 협업 / 머지 친화
- 다른 사람이 다른 모델을 파일 단위로 추가할 수 있도록 레지스트리 기반.
- 공용 타입(`types.py`)만 깨지 않게 변경. 시그니처 바꾸면 PR 설명에 명시.
- 무거운 바이너리/가중치/생성물 커밋 금지 (`.gitignore` 확인).

## 토큰/키
`.env`에서 로드 (`python-dotenv`). `.env.example` 기준:
`HF_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `WANDB_API_KEY`.

## 테스트/실행
- 프로토타입 UI: `streamlit run apps/streamlit_app.py`
- CLI 추론: `python scripts/run_inference.py --config configs/experiments/<name>.yaml`
- 파인튜닝: `python scripts/run_finetune.py --config configs/experiments/<name>.yaml`
