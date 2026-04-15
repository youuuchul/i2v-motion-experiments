# Roadmap

> 최종 프로덕트: **영상 밈/스타일/동작을 템플릿으로 주고, 유저 이미지 → 릴스 영상 자동 생성**. 지금은 그 재료가 되는 **템플릿 도서관** 을 구축 + 검증하는 단계.

진행 표기: ⬜ 미착수 / 🔄 진행 / ✅ 완료 / ⏸ 보류

---

## 전체 Phase 개요

| Phase | 목표 | 상태 |
|---|---|---|
| 0 | 로그/스키마 구조화 + 템플릿 지향 실험 대량 축적 | 🔄 |
| 1 | Lab UI 정비 (Gallery 고도화, mockup 정리) | ⬜ |
| 2 | Generate 탭 — SQLite 큐 + progress + auto preset | ⬜ |
| 3 | Resolution 업그레이드 (720→1080, 업스케일 옵션) | ⬜ |
| 4 | Template 탭 — 영상→프롬프트→i2v 재생성 | ⬜ |
| 5 | LoRA 실험 (프롬프트로 안 잡히는 스타일) | ⏸ |
| 6 | 서빙/배포 (Docker + FastAPI, 템플릿 DB 탑재) | ⏸ |

---

## Phase 0 — 로그 구조화 + 템플릿 지향 실험 🔄

### 완료 조건
- [ ] `docs/SCHEMA.md` v2 스키마 확정 ✅
- [ ] `docs/TEMPLATES.md` taxonomy 확정 ✅
- [ ] `src/i2v/utils/run_logging.py` v2 builder 함수
- [ ] `scripts/migrate_meta_v2.py` legacy → v2 변환
- [ ] `scripts/run_inference.py`, `scripts/run_batch.py` v2 출력
- [ ] 기존 experiment YAML 에 `template:` 블록 추가
- [ ] 카테고리별 신규 실험 YAML 5~10개 작성
- [ ] 신규 배치 실행 + Drive sync
- [ ] SVD 캐시 PermissionError 수정 (Phase 2 블로커 선제 해결)

### 핵심 결정
- 스키마 v2 는 nested. `schema_version: 2`, `legacy: bool`.
- v1 legacy 는 migration 시 `legacy=true` 로 마킹, 휴리스틱으로 카테고리 추론.
- 템플릿 승격은 **Phase 4** 에서 UI 붙임. Phase 0 에서는 실험만 쌓음.

---

## Phase 1 — Lab UI 정비

### 완료 조건
- [ ] Streamlit Gallery: 동작 안 하는 mockup 버튼 disable + tooltip
- [ ] 프롬프트 비교 뷰 (side-by-side 에 prompt/neg/seed/steps 컬럼)
- [ ] 템플릿 카테고리/서브카테고리 필터 추가
- [ ] 실험 회차/일시/latency 테이블 정렬 (ag-grid 대신 `st.dataframe` 컬럼 설정)
- [ ] 태그 필터 (multiselect)
- [ ] archived 엔트리 Drive 경로 클릭 → rclone 복원 명령 복사 버튼

### 결정 남은 것
- Gallery 상세 뷰 우측 패널 vs 하단 패널 — **결정 보류**, 실사용 보고 판단

---

## Phase 2 — Generate 탭 고도화

### 완료 조건
- [ ] SVD PermissionError 수정 (cache 볼륨 chown + compose entrypoint guard)
- [ ] SQLite 잡 큐 (`data/queue.db`)
  - 스키마: `jobs(id, config_path, status, created_at, started_at, finished_at, run_dir, error)`
  - 상태: `queued → running → done / error / canceled`
- [ ] 백그라운드 워커 프로세스 (`scripts/worker.py`)
- [ ] Streamlit Generate 탭
  - 큐에 추가 / 대기 중 삭제 / 순서 확인
  - 진행바 (diffusers callback → SQLite progress 필드 업데이트)
- [ ] Auto 옵션 = **선택형 preset** (drink_ripple, dolly_pan 등 기존 성공 실험 목록에서 고름)
- [ ] 생성 결과 자동으로 `outputs/index.jsonl` 에 기록 (Gallery 연동)

### 기술 결정
- 큐 백엔드 = **SQLite** (단일 워커, 복잡도 낮음). Redis 불필요.
- 진행바 = diffusers `callback_on_step_end` 훅 → SQLite 의 `progress` 컬럼 update → Streamlit 5초 polling
- 워커 프로세스 = docker 컨테이너 내부에서 `python scripts/worker.py` 가 foreground 로 돎. 일단 Streamlit 과 별도 컨테이너로.

---

## Phase 3 — Resolution 업그레이드

### 완료 조건
- [ ] 720×1280 preset (`configs/presets/hd.yaml`) + VRAM/시간 측정
- [ ] 1080×1920 preset (`configs/presets/fhd.yaml`) — OOM 여부 확인
- [ ] 업스케일러 후처리 (Real-ESRGAN / VEnhancer 검토)
- [ ] `preset.upscale: {enabled, factor, method}` 필드 추가
- [ ] Resolution tier 별 성공률 리포트

### 메모
- L4 24GB 에서 720 은 가능할 확률 높음, 1080 은 model_cpu_offload 로 겨우 / 실패 예상
- 2K 는 업스케일 후처리로만 현실적

---

## Phase 4 — Template 탭 🎯 프로덕트 핵심

### 완료 조건
- [ ] `templates/` 디렉토리 + YAML 포맷 (`docs/TEMPLATES.md`)
- [ ] Streamlit Template 탭
  - 템플릿 리스트 / 생성 / 삭제
  - 실험 Gallery 에서 "Promote to Template" 버튼 → templates/ 생성
- [ ] `scripts/extract_frames.py` — 영상 → 프레임 3~7장 추출
- [ ] `scripts/video_to_prompt.py` — 프레임 → gpt-5-mini → 프롬프트 후보 생성
- [ ] 템플릿 기반 재생성 플로우
  - 유저 이미지 업로드 → 템플릿 선택 → params 적용 → 생성
  - 결과는 outputs/ 에 기록, `source_template_id` 필드 추가
- [ ] Composition hint (첫 프레임 가이드) UI

### 기술 결정
- VLM = `gpt-5-mini` (현재 OpenAI 키 가능 모델)
- 영상 네이티브 입력 불가 → 프레임 추출 필수
- 초기 템플릿 ~10개는 **수동 프롬프트** 로 시작, 이후 VLM 자동화

### Frame extraction 세부
- 프레임 수: 영상 길이에 따라 3/5/7 (`docs/TEMPLATES.md` 표 참조)
- 시점: 0%, 중간 균등, 95% (마지막 프레임 회피 — fade-to-black 대응)

---

## Phase 5 — LoRA 실험 ⏸

트리거 조건: **"이 카테고리는 프롬프트로 안 잡힌다"** 가 10건 이상 쌓일 때.

### 예상 완료 조건
- [ ] LoRA 학습 파이프라인 (Diffusers + peft)
- [ ] 학습 데이터셋 규격 (20~200 샘플)
- [ ] `run_finetune.py` 구현 (현재 NotImplementedError)
- [ ] 템플릿에 `lora: [{path, scale}]` 필드 붙이기
- [ ] LoRA 가중치 Drive/HF 저장 규약

---

## Phase 6 — 서빙/배포 ⏸

### 예상 완료 조건
- [ ] FastAPI 서버 (`/generate` 엔드포인트)
- [ ] Docker 이미지 = Wan base + templates/ + LoRA weights 번들
- [ ] Cloud Run / GCE / 온프렘 선택
- [ ] 인증/레이트리밋
- [ ] 모니터링 (Grafana 등)

---

## 결정 로그

| 날짜 | 결정 | 이유 |
|---|---|---|
| 2026-04-14 | Wan2.1-VACE-14B GGUF Q4_K_M + bnb4 T5 + model_cpu_offload | L4 24GB + 16GB RAM 제약 |
| 2026-04-15 | 큐는 SQLite (Redis 불필요) | 단일 GPU, 동시 생성 1개면 충분 |
| 2026-04-15 | VLM = gpt-5-mini | 현재 OpenAI 키에서 가능한 유일한 비전 모델 (영상 네이티브 미지원 → 프레임 추출) |
| 2026-04-15 | Template 탭 v1 은 수동 프롬프트, v2 에서 VLM 자동화 | 리스크 분산 |
| 2026-04-15 | Schema v2 (nested, template 블록, environment 블록) | 템플릿/배포 대비 필드 미리 파둠 |

---

## 다음 실행 순서 (Phase 0 기준)

1. `run_logging.py` v2 builder + util 헬퍼 작성
2. `migrate_meta_v2.py` 스크립트
3. `run_inference.py` / `run_batch.py` v2 출력으로 업데이트
4. 기존 experiment YAML 에 `template:` 블록 추가
5. 신규 카테고리별 실험 YAML 작성
6. SVD 캐시 권한 수정 (compose entrypoint)
7. 신규 배치 실행 → Drive sync
8. Gallery 에서 새 필드들 보이는지 확인 → Phase 1 진입
