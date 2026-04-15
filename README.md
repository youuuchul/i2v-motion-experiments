# i2v-motion-experiments

이미지(+텍스트) → 비디오 모델 실험 / 파인튜닝 / 결과 분석 워크스페이스.
타깃 출력은 **세로(9:16) 릴스/쇼츠**, 1차 길이 **5초** (3~15초 가변).

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

런타임 옵션:
- `enable_model_cpu_offload()` — GGUF는 `enable_sequential_cpu_offload()` 비호환 (meta-tensor 초기화에서 `KeyError`)
- `enable_vae_tiling()` + `enable_vae_slicing()` — VAE 활성화 절감
- 환경변수 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` — 단편화 완화
- **16GB swap 필수** — 로딩 피크 스파이크 흡수 (없으면 VM 리셋)

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

## 3. VM / Docker 환경

### VM (GCP)
- Debian 12, L4 GPU 1개 (24GB VRAM, 실제 가용 ~22GB), 16GB RAM, 100GB 디스크
- 16GB swapfile (`/swapfile`) — 추론 로딩 피크 흡수용
- NVIDIA 드라이버 595 + CUDA 12.4

### Docker
- `docker/Dockerfile` — CUDA 12.4 runtime + Python 3.11 + torch 2.6 + gguf/bnb/ftfy
- `docker/compose.yaml`:
  - HF/torch 캐시 볼륨 (최초 fp16 캐시 70GB → Q4 전환 후 ~22GB)
  - `user: "${UID:-1004}:${GID:-1007}"` — 호스트 유저 UID 매핑 (outputs 권한 정렬)
  - 포트 8501 노출 (Streamlit)
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`

### 주의 / 잔 팁
- HF 다운로드 시 `HF_HUB_DISABLE_XET=1` 필수 (VM에서 xet deadlock) — Dockerfile에 반영
- `.env` 에 `HF_TOKEN = <value>` 로 공백 붙이면 dotenv 로드 안 됨 → `HF_TOKEN=<value>` (등호 양쪽 공백 X)

---

## 4. 세팅

### 최초 (VM에서)
```bash
cp .env.example .env          # HF_TOKEN, OPENAI_API_KEY 등 채우기
sudo fallocate -l 16G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile
sudo docker-compose -f docker/compose.yaml build
```

### rclone (Google Drive 백업용, 선택)
1. 로컬 PC에서 `rclone config` → remote 이름 `gdrive`, Drive OAuth (개인 드라이브면 "Shared Drive?" 에 `n`)
2. 로컬 `~/.config/rclone/rclone.conf` 를 VM 같은 경로로 복사 (scp 또는 VSCode)
3. VM에 rclone 설치: `sudo apt-get install -y unzip && curl https://rclone.org/install.sh | sudo bash`
4. 확인: `rclone lsd gdrive:`

---

## 5. 사용법

### 추론 (1회 실행)
실험 YAML 지정:
```bash
sudo docker-compose -f docker/compose.yaml run --rm i2v \
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

### 결과 분석 (Streamlit)
```bash
sudo docker-compose -f docker/compose.yaml run --rm --service-ports i2v \
  streamlit run apps/streamlit_app.py --server.address 0.0.0.0 --server.headless true
```
브라우저에서 `http://<VM_EXTERNAL_IP>:8501`. GCP 방화벽 8501 포트 허용 필요.

**Gallery 탭**
- 실험/모드/상태 필터
- 테이블: 시작시간·실험·모드·모델·양자화·스텝·seed·wall_sec·vram_peak
- 1~4개 선택 → 1개면 비디오+config snapshot+run.log, 여러 개면 side-by-side 비교
- archived 엔트리는 "📦 archived to Drive" 안내 + rclone 복원 명령 자동 표시

**Generate 탭** (ad-hoc 실행; 일회성 테스트용)
- mode/해상도/스텝 조절 후 즉시 실행. 결과는 `outputs/streamlit/<model>/` 에 저장.

### Drive 백업 / 아카이브
```bash
python3 scripts/sync_to_drive.py --dry-run                             # 대상 확인만
python3 scripts/sync_to_drive.py --delete-local-video                  # 업로드 + 로컬 비디오 삭제
python3 scripts/sync_to_drive.py --older-than-days 7 --delete-local-video
python3 scripts/sync_to_drive.py --experiment smoke_wan2_1_vace_14b
```
- Drive 경로: `gdrive:i2v-experiments/<experiment>/<run_dir>/`
- 인덱스에 `archived: true`, `drive_path`, `archived_at` 기록 (meta/config/log는 로컬 유지)
- 복원: `rclone copy gdrive:i2v-experiments/<exp>/<run_dir> outputs/<exp>/<run_dir>`

### 파인튜닝
**아직 미구현**. `run_finetune.py` 는 `NotImplementedError` 스캐폴드.
구현 시 `src/i2v/training/` 에 모델별 LoRA/full-finetune 루프 추가 예정 (PEFT 기반).

---

## 6. 실험 전략

### 실험 YAML 구조
```yaml
experiment: <unique_name>
notes: "실험 의도 한 줄"
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

### 샘플 이미지 준비 (다른 환경에서 재현 시)
- `assets/samples/*` 는 **gitignore** (개인 사진 노출 방지). repo 에는 포함 안 됨.
- 기존 YAML 의 `input.image` 경로 (`assets/samples/<file>.png`) 에 **본인이 쓸 이미지를 그대로 같은 이름으로** 두거나, YAML 의 경로를 바꿔서 사용.
- 최소 1장 있으면 smoke_test preset 으로 30분 이내 첫 런 확인 가능.

### 관련 문서
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Phase 0~6 계획 / 결정 로그
- [`docs/SCHEMA.md`](docs/SCHEMA.md) — meta.json v2 / index.jsonl 필드 사양
- [`docs/TEMPLATES.md`](docs/TEMPLATES.md) — 템플릿 카테고리 taxonomy / 승격 플로우

---

## 7. 결과 분석 워크플로

1. **동일 실험 반복** (seed 고정, 같은 config) → 재현성 확인
2. **축 하나씩 변경** (예: steps 20 ↔ 40) → Gallery 에서 2개 선택, side-by-side 비교
3. 관찰 → `notes` 업데이트 + meta.json 내 `wall_sec`/`vram_peak_mib` 로 객관 지표 교차
4. 비교 끝난 실험은 `sync_to_drive.py --delete-local-video` 로 이동 (로컬 디스크 확보)
5. Gallery 는 archived 도 목록에 남음 → 과거 결정 기록으로 계속 활용

**정량 메트릭 (TODO)**: `src/i2v/eval/` 에 LPIPS / SSIM / 움직임 일관성 등 계획. 미구현.

---

## 8. 협업 / 머지 규칙 (`CLAUDE.md` 일관)

- 새 모델은 `src/i2v/models/<name>.py` + `@registry.register("<name>")` + `configs/models/<name>.yaml`. 외부에선 `BasePipeline` 인터페이스만 의존.
- 코드에 하이퍼파라미터 하드코딩 금지 — YAML 로.
- 비디오 스펙(해상도/fps/길이)은 `configs/presets/` 한 곳에.
- 공용 타입 (`src/i2v/core/types.py`) 시그니처 변경 시 PR 설명에 명시.
- 무거운 산출물 커밋 금지. 백업은 Drive 로.
- 학습/서빙/평가는 서로 import 안 함 (공통은 `core`/`utils` 경유).

---

## 9. 디렉토리

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
  utils/        config, video, seed, run_logging
apps/           streamlit 프로토타입
scripts/        run_inference / run_finetune / migrate_outputs / sync_to_drive
docker/         Dockerfile, compose.yaml
outputs/        실행 결과물 (gitignored, index.jsonl + run_dirs)
assets/         작은 참조 자산 (샘플 이미지 등, 트래킹 대상)
data/           대용량 데이터셋 (gitignored)
```
