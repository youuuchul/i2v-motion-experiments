# i2v-motion-experiments

이미지(+텍스트) → 비디오 모델 실험 / 파인튜닝 / 결과 분석 워크스페이스.
타깃 출력은 **세로(9:16) 릴스/쇼츠**, 1차 길이 **5초** (3~15초 가변).

베이스라인: **Wan2.1-VACE-14B (Q4 GGUF + bnb4 T5 + model_cpu_offload)**, GCP L4 24GB 환경.

---

## Quickstart (clone → 실행, 30분)

> 전제: NVIDIA 드라이버(>=535) + Docker + nvidia-container-toolkit 가 호스트에 설치돼있고,
> GPU 는 24GB VRAM 이상 (L4/A10G/3090/4090 등). HF token 만 있으면 됨.

```bash
# 1) 클론
git clone <this-repo> i2v-motion-experiments
cd i2v-motion-experiments

# 2) 환경 변수
cp .env.example .env
#   .env 열어서 최소한 HF_TOKEN= 채우기.
#   docker bind-mount 권한 정렬을 위해 UID/GID 도 채우는 게 안전:
echo "UID=$(id -u)"  >> .env
echo "GID=$(id -g)"  >> .env

# 3) 샘플 이미지 (assets/samples/* 는 .gitignore — 개인 사진 노출 방지)
#    (a) 기존 팀 Drive 에서 당겨오기 (rclone 의 gdrive remote 필요):
python3 scripts/sync_samples.py pull
#    (b) 또는 본인 이미지를 직접 넣기 — smoke 실험은 sample.png 하나면 OK:
# cp <본인이 쓸 사진>.png assets/samples/sample.png

# 4) (권장) 추론 로딩 피크 흡수용 16GB swap
sudo fallocate -l 16G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile

# 5) 도커 빌드 + smoke test (Q4 GGUF + 432×768 · 3s · 40step ≈ 30분)
sudo docker compose -f docker/compose.yaml build
sudo docker compose -f docker/compose.yaml run --rm i2v \
  python scripts/run_inference.py --config configs/experiments/smoke_wan2_1_vace_14b.yaml

# 6) 결과 분석 (Streamlit 갤러리)
sudo docker compose -f docker/compose.yaml run --rm --service-ports i2v \
  streamlit run apps/streamlit_app.py --server.address 0.0.0.0 --server.headless true
# 브라우저: http://<HOST_IP>:8501  (GCP 라면 8501 방화벽 허용 필요)
```

문제가 생기면 [§3 환경 / 흔한 함정](#3-환경--흔한-함정) 참고.

---

## 1. 단계별 목표 & 현황

| Phase | 설명 | 상태 |
|---|---|---|
| Phase 1 | 이미지 + 고정 텍스트 → 5s 9:16 비디오. 모델·하이퍼 비교 | **진행 중** — Wan2.1-VACE-14B 추론 파이프 동작 |
| Phase 2 | 사용자 이미지 + 카테고리 → LLM 자동 프롬프트 → 비디오 | 프롬프트 모듈 스텁만 있음 (`src/i2v/prompts/`) |
| Phase 3 | 베스트 파이프 서빙화 (`src/i2v/serving/`) | 미시작 |
| 파인튜닝 | LoRA 등 파인튜닝 루프 | **미구현** (`run_finetune.py` 는 스캐폴드) |

---

## 2. 모델 / 추론 런타임 전략

### 선택된 베이스라인
**Wan2.1-VACE-14B** (통합 T2V/I2V/R2V/V2V 멀티모드 비디오 DiT).
- 네이티브 16fps, 16:9 (480P 832×480 / 720P 1280×720)
- 9:16 출력은 비네이티브 → 해상도 타협 필요

### L4 24GB + 16GB RAM 환경 최적화
L4 VRAM·VM RAM 제약 때문에 그대로는 못 돌림. 확정된 조합:

| 컴포넌트 | 포맷 | 출처 |
|---|---|---|
| Transformer (DiT) | **GGUF Q4_K_M** (~11.6GB) | `QuantStack/Wan2.1_14B_VACE-GGUF` |
| Text encoder (UMT5-XXL) | **bitsandbytes 4bit (NF4)** (~2.5GB) | `Wan-AI/Wan2.1-VACE-14B-diffusers` text_encoder |
| VAE / scheduler / tokenizer | fp16 원본 | 동일 diffusers 리포 |

런타임 옵션 (`configs/models/wan2_1_vace_14b.yaml`):
- `enable_model_cpu_offload()` — GGUF는 `enable_sequential_cpu_offload()` 비호환 (meta-tensor 초기화에서 `KeyError`)
- `enable_vae_tiling()` + `enable_vae_slicing()` — VAE 활성화 절감
- 환경변수 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` — 단편화 완화 (compose 가 자동 주입)

### 성능 기준점 (L4 22GB 실측)
- 432×768 · 3s · 16fps · 40 steps · Q4_K_M → **~30분** (44s/it)
- 5s · 576×1024 는 **VRAM 초과** — 활성화 텐서 너무 큼. 해상도/길이 조정 필요.

### 생성 모드
`GenerationRequest.mode` 로 전환:
- `i2v` (기본): 첫 프레임을 입력 이미지로 고정하고 나머지 inpaint
- `r2v`: 입력을 reference 로만 쓰고 자유 생성 (첫 프레임 비고정)
- `t2v`: 프롬프트만 사용
- `v2v`: 아직 미지원 (추가 예정)

---

## 3. 환경 / 흔한 함정

### Docker (compose) 동작 방식
- `docker/Dockerfile`: CUDA 12.4 runtime + Python 3.11 + torch 2.6 + gguf/bnb/ftfy
- `docker/compose.yaml`:
  - HF/torch 캐시는 named volume (`hf_cache`, `torch_cache`) — 컨테이너 재생성해도 모델 재다운로드 X
  - `user: "${UID:-1000}:${GID:-1000}"` — `.env` 의 `UID`/`GID` 로 호스트 유저 매핑 (outputs 권한 정렬)
  - 8501 포트 노출 (Streamlit), `--service-ports` 가 있어야 바인딩됨
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 자동 주입

### 캐시 권한이 뒤틀렸을 때
named volume 의 초기 권한은 root:root 라서 첫 실행 시 `PermissionError` 가 날 수 있음:
```bash
bash scripts/setup_cache_perms.sh   # docker_hf_cache / docker_torch_cache 의 owner 를 호스트 유저로
```

### 흔한 함정
- `.env` 의 `HF_TOKEN = <value>` 처럼 등호 양쪽 공백 → dotenv 로드 안 됨. `HF_TOKEN=<value>` 로.
- HF 다운로드 멈춤 (xet deadlock) → Dockerfile 에 `HF_HUB_DISABLE_XET=1` 박혀있음. 호스트에서 직접 돌릴 땐 export 필요.
- `assets/samples/*` 는 gitignore. 클론 직후엔 비어있고, 본인 이미지를 같은 파일명으로 넣어야 기존 YAML 이 그대로 동작.
- swap 없이 Q4 GGUF 로딩 → 피크 RAM 스파이크로 VM 리셋. 16GB swap 권장.

---

## 4. 사용법

### 추론 (1회 실행)
실험 YAML 지정:
```bash
sudo docker compose -f docker/compose.yaml run --rm i2v \
  python scripts/run_inference.py --config configs/experiments/smoke_wan2_1_vace_14b.yaml
```

결과물 구조:
```
outputs/
  <experiment>/
    <experiment>_<YYYYMMDD-HHMMSS>_seed<N>/
      wan21_vace_<mode>_<seed>.mp4
      config.snapshot.yaml    # 실험+프리셋+모델 머지 덤프
      run.log                 # stdout/stderr 복제
      meta.json               # 모델·양자화·시간·VRAM 피크·status
  index.jsonl                 # 한 줄당 한 실행 (Streamlit이 읽음)
```
- 실패해도 run_dir 생성 + `status: error` + traceback 기록됨
- 레거시(규약 이전) mp4 흡수: `python3 scripts/migrate_outputs.py`

### 배치 (여러 실험 순차 실행)
```bash
# 카테고리별 미완료 실험만 골라 백그라운드 컨테이너로 실행
bash scripts/resume_batch.sh           # 실행 (detached container 'batch')
bash scripts/resume_batch.sh --dry     # 후보만 확인

# 직접 지정
sudo docker compose -f docker/compose.yaml run --rm i2v \
  python scripts/run_batch.py --glob "configs/experiments/wan_vace_*.yaml" \
                              --sync-after-each
```
같은 model_config 끼리 그룹핑 → 모델 로드 1회로 여러 실험 돌림.

### Streamlit (Gallery + Generate)
```bash
sudo docker compose -f docker/compose.yaml run --rm --service-ports i2v \
  streamlit run apps/streamlit_app.py --server.address 0.0.0.0 --server.headless true
```

**Gallery 탭**
- 실험/모드/상태/template 카테고리 필터
- 테이블: run_num · version · 시작시간(KST) · 실험 · template · mode · model · quant · steps · seed · wall_sec · vram_peak
- 1~4개 선택 → 1개면 비디오+config snapshot+run.log, 여러 개면 side-by-side 비교
- archived 엔트리는 "📦 archived to Drive" 안내 + rclone 복원 명령 자동 표시

**Generate 탭** (ad-hoc; 일회성 테스트)
- mode/해상도/스텝 조절 후 즉시 실행. 결과는 `outputs/streamlit/<model>/` 에 저장.

### Drive 백업 / 아카이브 (선택)
rclone 으로 Google Drive 에 결과물 보관, 로컬 디스크 확보:
```bash
# 사전: rclone 설치 + ~/.config/rclone/rclone.conf 에 'gdrive' remote 등록
python3 scripts/sync_to_drive.py --dry-run                             # 대상 확인만
python3 scripts/sync_to_drive.py --delete-local-video                  # 업로드 + 로컬 비디오 삭제
python3 scripts/sync_to_drive.py --older-than-days 7 --delete-local-video
python3 scripts/sync_to_drive.py --experiment smoke_wan2_1_vace_14b
```
- Drive 경로: `gdrive:i2v-experiments/<experiment>/<run_dir>/`
- 인덱스에 `archived: true`, `drive_path`, `archived_at` 기록 (meta/config/log는 로컬 유지)
- 복원: `rclone copy gdrive:i2v-experiments/<exp>/<run_dir> outputs/<exp>/<run_dir>`

### 샘플 이미지 동기화 (assets/samples/)
`assets/samples/*` 는 .gitignore (개인 사진 보호) — 대신 Drive 로 백업.
```bash
python3 scripts/sync_samples.py push          # 로컬 → Drive
python3 scripts/sync_samples.py pull          # Drive → 로컬 (클론 직후)
python3 scripts/sync_samples.py list          # Drive 에 있는 것 확인
python3 scripts/sync_samples.py push --dry-run
```
Drive 경로: `gdrive:i2v-experiments/assets/samples/`.

### 파인튜닝
**아직 미구현**. `run_finetune.py` 는 `NotImplementedError` 스캐폴드.
구현 시 `src/i2v/training/` 에 모델별 LoRA/full-finetune 루프 추가 예정 (PEFT 기반).

---

## 5. 실험 전략

### 실험 YAML 구조
```yaml
experiment: <unique_name>
notes: "실험 의도 한 줄"
tags: ["v2", ...]                  # 선택
template:                          # v2 정책 (2026-04-16~)
  motion_template: lift_to_camera  # 활성 6개 모션 중 하나 (신규 실험 필수)
  meme_template: null              # 또는 meme_ai_character / meme_ai_animal / meme_dance_ref
  category: person_action          # (legacy) v1 taxonomy. 신규는 선택
  subcategory: offer_drink         # (legacy)
  intent: product_showcase
model_config: configs/models/<model>.yaml   # 모델 어댑터 + init 인자
preset: configs/presets/<preset>.yaml       # 해상도/fps/길이
input:
  mode: i2v | r2v | t2v
  image: assets/samples/<file>.png
  reference_images: [...]                   # r2v 다중 reference 시
  prompt: "..."
  negative_prompt: "..."
run:
  seed: 42
  num_inference_steps: 40
  guidance_scale: 5.0
  out_dir: outputs/<experiment>             # run_inference 가 run_dir 로 재작성
```

### 템플릿 정책 (2026-04-16~)

신규 실험은 아래 두 축의 조합으로 정의된다. 상세는 [`docs/TEMPLATES.md`](docs/TEMPLATES.md).

**Motion templates (6, 필수 1개):** `consume_product`, `lift_to_camera`, `dolly_in`, `orbit_pan`, `steam_rise`, `surface_shimmer`

**Meme templates (3, 선택):** `meme_ai_character`, `meme_ai_animal`, `meme_dance_ref` (※ dance_ref는 레퍼런스 영상 처리 PoC 필요 — 현재 배치 제외)

조명/광학/분위기는 모션이 아님 — 별도 `configs/presets/lighting/` 로 분리 예정, 모션과 직교 조합.

### 비교 축
- **mode** (i2v vs r2v): 구도 고정 vs 자유 해석
- **양자화** (Q3_K_S / Q4_K_M / Q5_K_M): 품질 ↔ 메모리
- **steps** (20/40/50): 품질 ↔ 시간
- **해상도 / 길이**: VRAM 피크 결정
- **prompt / negative**: 스타일·움직임 제어
- **seed**: 같은 설정 재현성 확인

### 품질 트레이드오프 기록
- Q3_K_S: 비디오 DiT에서 품질 급락 (출력 뭉개짐). 파이프 디버깅용.
- Q4_K_M: 최소 실용 품질. 현재 기본.
- steps 20 이하: 최종물엔 불충분. 40+ 권장.
- r2v 단독으로 입력 이미지 쓰면 첫 프레임 고정 안 됨 → I2V 기대면 `mode: i2v` 필수.

### 새 실험 추가
1. `configs/experiments/<name>.yaml` 작성 (위 구조)
2. (필요 시) `configs/presets/<preset>.yaml` 추가
3. CLI: `run_inference.py --config configs/experiments/<name>.yaml`
4. `outputs/<name>/<name>_<ts>_seed<N>/` 자동 저장 + index 업데이트
5. Streamlit Gallery 에서 비교

### 관련 문서
- [`docs/EXPERIMENT_LOG.md`](docs/EXPERIMENT_LOG.md) — **실험 기록 타임라인** (배치별 원본 소스 · 템플릿 · duration · latency · 의도/관찰)
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Phase 0~6 계획 / 결정 로그
- [`docs/SCHEMA.md`](docs/SCHEMA.md) — meta.json v2 / index.jsonl 필드 사양
- [`docs/TEMPLATES.md`](docs/TEMPLATES.md) — 활성 **Motion 6개 + Meme 3개** 정책 / 기존 config 맵핑 / legacy taxonomy / 승격 플로우

---

## 6. 결과 분석 워크플로

1. **동일 실험 반복** (seed 고정, 같은 config) → 재현성 확인 (Streamlit 의 `version` 컬럼이 동일)
2. **축 하나씩 변경** (예: steps 20 ↔ 40) → Gallery 에서 2개 선택, side-by-side 비교
3. 관찰 → `notes` 업데이트 + meta.json 내 `wall_sec`/`vram_peak_mib` 로 객관 지표 교차
4. 비교 끝난 실험은 `sync_to_drive.py --delete-local-video` 로 이동 (로컬 디스크 확보)
5. Gallery 는 archived 도 목록에 남음 → 과거 결정 기록으로 계속 활용

**정량 메트릭 (TODO)**: `src/i2v/eval/` 에 LPIPS / SSIM / 움직임 일관성 등 계획. 미구현.

---

## 7. 협업 / 머지 규칙 (`CLAUDE.md` 일관)

- 새 모델은 `src/i2v/models/<name>.py` + `@registry.register("<name>")` + `configs/models/<name>.yaml`. 외부에선 `BasePipeline` 인터페이스만 의존.
- 코드에 하이퍼파라미터 하드코딩 금지 — YAML 로.
- 비디오 스펙(해상도/fps/길이)은 `configs/presets/` 한 곳에.
- 공용 타입 (`src/i2v/core/types.py`) 시그니처 변경 시 PR 설명에 명시.
- 무거운 산출물 커밋 금지. 백업은 Drive 로.
- 학습/서빙/평가는 서로 import 안 함 (공통은 `core`/`utils` 경유).

---

## 8. 디렉토리

```
configs/
  models/       모델 어댑터 init 파라미터
  presets/      비디오 스펙 (해상도/fps/길이)
  experiments/  실험 YAML (모델+프리셋+input+run)
src/i2v/
  core/         BasePipeline, Registry, types (모델 공통 인터페이스)
  models/       i2v 파이프라인 어댑터 (wan2_1_vace_14b, svd, ...)
  prompts/      LLM 프롬프트 생성 (Phase 2)
  data/         데이터셋 / 전처리 (파인튜닝 대비)
  training/     파인튜닝 루프 (현재 비어있음)
  eval/         메트릭 / 비교 분석 (현재 비어있음)
  serving/      서빙 스텁 (Phase 3)
  utils/        config, video, seed, run_logging, meta_v2
apps/           streamlit 프로토타입
scripts/        run_inference / run_batch / resume_batch / migrate_* / sync_to_drive
docker/         Dockerfile, compose.yaml
outputs/        실행 결과물 (gitignored, index.jsonl + run_dirs)
assets/         작은 참조 자산. assets/samples/* 는 gitignore (개인 사진 보호)
data/           대용량 데이터셋 (gitignored)
```
