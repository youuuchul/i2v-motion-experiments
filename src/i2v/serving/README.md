# serving/

Phase 3: 실험에서 검증된 파이프라인을 여기에 분리해 서빙.

가이드라인:
- 이 모듈은 `src/i2v/core/`와 `src/i2v/models/`만 import. `training/` / `eval/`을 import하지 말 것 (의존성/이미지 크기 분리).
- FastAPI 엔드포인트는 `app.py`, 스키마는 `schemas.py`, 파이프라인 로딩은 `deps.py`.
- 컨테이너 이미지에서 웨이트는 런타임 볼륨에서 마운트 (`HF_HOME` 활용).
