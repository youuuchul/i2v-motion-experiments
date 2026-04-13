# i2v-motion-experiments

이미지(+텍스트) → 비디오 모델 실험 / 파인튜닝 / 결과 분석용 워크스페이스.
타깃 출력은 **세로(9:16) 릴스/쇼츠**, 1차 길이는 **5초** (3~15초 가변).

## 단계별 목표
1. **Phase 1 (now)**: 이미지 + 고정 텍스트 프롬프트 → 5s 9:16 비디오. 모델/하이퍼파라미터 비교.
2. **Phase 2**: 사용자 이미지 + 항목(카테고리/스타일/액션) → LLM 자동 프롬프트 → 비디오.
3. **Phase 3**: 베스트 파이프라인을 `src/i2v/serving/`로 분리해 서빙(API).

## 디렉토리

```
configs/        모델·실험·프리셋 YAML
src/i2v/
  core/         BasePipeline, Registry, types (모델 간 공통 인터페이스)
  models/       i2v 파이프라인 어댑터 (svd, cogvideox, wan, ltx, ...)
  prompts/      LLM 프롬프트 생성 (Phase 2)
  data/         데이터셋 / 전처리
  training/     파인튜닝 루프 (lora 등)
  eval/         메트릭 / 비교 분석
  serving/      서빙 스텁 (확장용)
  utils/        io, video, seed, logging
apps/           streamlit 프로토타입
scripts/        CLI 엔트리포인트
experiments/    런 결과 (gitignored)
data/           원본/전처리 자산 (gitignored)
outputs/        생성 비디오 (gitignored)
notebooks/      탐색/분석 노트북
```

## 셋업
```bash
cp .env.example .env  # 토큰 채우기
uv venv && source .venv/bin/activate    # 또는 python -m venv
uv pip install -e ".[dev]"              # 또는 pip install -e .
streamlit run apps/streamlit_app.py
```

## 협업 규칙 (다른 사람들과 머지 고려)
- 새 모델은 `src/i2v/models/<name>.py`에 추가하고 `core.registry`에 등록. 외부에선 `BasePipeline` 인터페이스만 의존.
- 실험 설정은 코드가 아니라 `configs/experiments/*.yaml`로. 하드코딩 금지.
- 비디오 스펙(해상도/fps/길이)은 `configs/presets/`에서 한 곳으로 관리.
- 무거운 산출물은 절대 커밋 금지(.gitignore 확인). 공유 필요하면 wandb/외부 스토리지.
