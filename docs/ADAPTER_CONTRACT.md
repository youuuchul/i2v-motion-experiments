# Worker Adapter Contract

trunk 저장소 (`AI-5Team/AI6_5Team_Advanced_Project`) 의 worker 는 이 실험 저장소를
**subprocess 경계** 로만 호출한다 (트렁크 합의: "모델 실험 저장소는 독립 유지,
worker adapter 경계만 반영").

이 문서는 그 경계의 **입력/출력 계약** 을 고정한다. 이 계약을 깨는 변경은
trunk 의 `adapter_wan2_vace` 를 동시에 업데이트해야 한다 (PR 에 명시).

---

## 1. 진입점 (Entry Point)

### 단일 실행
```
python scripts/run_inference.py --config <path-to-yaml> [--outputs-root <dir>]
```

### 배치 (여러 실험, 모델 로드 재사용)
```
python scripts/run_batch.py --configs <yaml>... [--outputs-root <dir>]
python scripts/run_batch.py --glob  "configs/experiments/*.yaml"
```

**working dir**: 저장소 루트. 상대 경로 (`assets/samples/...`, `configs/...`) 가 해석됨.
**환경변수**: `.env` 자동 로드 (python-dotenv). 호출측에서 `HF_TOKEN` 등 주입해도 OK.
**Python path**: `src/` 가 루트. Docker 컨테이너에서 `PYTHONPATH=src` 가 자동 설정.

### 컨테이너 호출 예시 (trunk worker 가 쓸 패턴)
```bash
docker run --rm --gpus all \
  -v "$REPO":/workspace -v hf_cache:/cache/huggingface -v torch_cache:/cache/torch \
  -w /workspace --user "$(id -u):$(id -g)" \
  --env-file "$REPO/.env" \
  -e HF_HOME=/cache/huggingface -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e HF_HUB_DISABLE_XET=1 -e PYTHONPATH=src \
  i2v-motion:dev \
  python scripts/run_inference.py --config configs/experiments/<name>.yaml
```

---

## 2. 입력 (Config YAML)

trunk 가 **YAML 파일 하나** 를 이 저장소에 만들어 넘기거나, 기존 파일 경로를 지정한다.

```yaml
experiment: <unique_name>                   # required, run_dir 명칭 기준
notes: "..."                                # optional
tags: [...]                                 # optional, 필터링용
template:                                   # optional, meta 에만 기록됨 (동작 X)
  motion_template: lift_to_camera           # 활성 모션 (없으면 null)
  meme_template: null                       # meme 변형 (없으면 null)
  category: person_action
  subcategory: offer_drink
  intent: product_showcase
model_config: configs/models/<model>.yaml   # required
preset: configs/presets/<preset>.yaml       # required
input:                                      # required
  mode: i2v | r2v | t2v                     # 기본 i2v
  image: <path-to-image>                    # required (t2v 제외)
  reference_images: [<path>, ...]           # optional (r2v 다중 ref)
  prompt: "..."                             # required
  negative_prompt: "..."                    # optional
run:                                        # required
  seed: 42
  num_inference_steps: 40
  guidance_scale: 5.0
  out_dir: outputs/<exp>                    # 힌트 (run_inference 가 run_dir 로 재작성)
```

**고정 전제 (변경 시 계약 깨짐)**:
- `model_config` / `preset` 은 이 저장소의 상대 경로. 존재해야 함.
- `input.image` 도 상대 경로 (저장소 루트 기준).
- 알 수 없는 최상위 키는 무시됨 (hard fail 아님).

**확장 시 (신규 필드 추가)**:
- `input.*` / `run.*` 는 `GenerationRequest` 필드에 매핑됨 (`src/i2v/core/types.py`).
- 신규 필드는 타입 변경까지 필요. **public 타입 변경 시 이 문서 + trunk PR 설명에 명시.**

---

## 3. 출력 (Run Artifacts)

한 번의 실행은 **정확히 하나의 run_dir** 과 **한 줄의 index entry** 를 만든다.

### 파일 레이아웃
```
<outputs-root>/
  <experiment>/
    <experiment>_<YYYYMMDD-HHMMSS>_seed<N>/
      wan21_vace_<mode>_<seed>.mp4    # 생성된 비디오 (실패 시 없음)
      config.snapshot.yaml            # experiment + preset + model 머지 덤프
      run.log                         # stdout/stderr 복제 (Tee)
      meta.json                       # v2 schema, docs/SCHEMA.md 참조
  index.jsonl                         # 모든 실행 flat 인덱스 (한 줄 append)
```

### meta.json — source of truth
`docs/SCHEMA.md` 에 필드 스펙 상세. **worker 가 절대 읽어야 하는 핵심 필드**:

| 필드 | 용도 |
|---|---|
| `run.status` | `"ok"` / `"error"` — 실패해도 meta 는 생성됨 |
| `run.error` | status=error 시 `"<ExceptionType>: <msg>"` |
| `run.config_hash` | 재현성 키 (prompt/seed/steps/…). 같은 hash = 같은 config |
| `output.video_path` | 생성된 mp4 절대/상대 경로 (status=ok 시) |
| `metrics.wall_sec` | 실행 시간 (초) |
| `metrics.vram_peak_mib` | VRAM 피크 (MiB) |
| `generation.*` | width/height/fps/num_frames/seed/steps/cfg |

### index.jsonl — flat cache
`meta.json` 의 subset (flat). 빠른 필터링용. 포맷 스펙은 `docs/SCHEMA.md` 의 `index.jsonl (flat entry)` 섹션.

### 실패 규약
- 예외가 터져도 **run_dir / meta.json / run.log / index 엔트리 항상 생성**.
- `status: error`, `error: "<traceback header>"`, `video_path: null`.
- exit code 1 반환 (worker 에서 감지 가능).

---

## 4. Exit Codes

| code | 의미 |
|---|---|
| 0 | status=ok, video 생성 완료 |
| 1 | status=error. meta.json 에 traceback, index 에도 entry 있음. |

worker 는 **exit code + meta.json.run.status 를 같이 볼 것**. (0 이어도 meta 확인 권장.)

---

## 5. 부작용 / 비보장

이 저장소는 다음을 **건드리지 않는다**:
- 외부 네트워크 (HF 다운로드 제외 — 캐시된 상태 전제 가능)
- trunk 의 DB / 큐 / 세션
- 사용자 환경 변수 (.env 외)

다음은 **보장하지 않음**:
- 동시 실행 (같은 `experiment` + seed 는 run_dir 타임스탬프로 구분되지만, GPU 는 1개라 실제 동시 추론은 OOM).
- idempotency (같은 config 두 번 돌리면 run_dir 2개 생김, config_hash 는 동일).

---

## 6. 변경 관리

이 계약을 깨는 변경:
- 진입점 CLI 인자 변경 (`--config` 이름, argparse default)
- meta.json / index.jsonl 필드 이름/타입 변경
- exit code semantic 변경
- 파일 레이아웃 변경

→ trunk 의 `adapter_wan2_vace` 동시 수정 필수. PR 에 "adapter contract change" 라벨링.

안전한 변경:
- 신규 meta 필드 추가 (worker 는 unknown key 를 무시해야 함)
- 신규 CLI 옵션 추가 (기본값 유지 필수)
- 모델 구현 교체 (동일 `model_config` 인터페이스 유지)

---

## 7. 참고

- 스키마 상세: [`docs/SCHEMA.md`](./SCHEMA.md)
- 템플릿 taxonomy: [`docs/TEMPLATES.md`](./TEMPLATES.md)
- 로드맵: [`docs/ROADMAP.md`](./ROADMAP.md)
- trunk 합의: `AI-5Team/AI6_5Team_Advanced_Project` README §3, §4
