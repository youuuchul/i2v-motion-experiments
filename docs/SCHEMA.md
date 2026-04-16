# Experiment Log Schema

실험 로그는 두 레이어로 쌓임:

- **`outputs/<exp>/<run_id>/meta.json`** — 실행 1건의 전체 상세 (depth-structured)
- **`outputs/index.jsonl`** — 모든 실행의 flat 인덱스 (pandas/Streamlit 빠른 로드)

두 파일은 run 종료 시 원자적으로 같이 기록된다. `meta.json` 이 source of truth, `index.jsonl` 은 flat 캐시.

---

## Schema Version

| 버전 | 도입 커밋 | 특징 |
|---|---|---|
| v1 (legacy) | 초기 ~ 2026-04-14 | flat meta, template 필드 없음, quantization 단일 문자열 |
| **v2** | 2026-04-15 ~ | nested, `template.*` / `environment.*` 추가, `schema_version: 2` 표기 |

v1 → v2 migration 은 `scripts/migrate_meta_v2.py` 로 실행. 누락 필드는 best-effort 로 복원하고 `legacy: true` 표시.

---

## meta.json (v2)

```json
{
  "schema_version": 2,
  "legacy": false,

  "run": {
    "run_id": "wan_vace_coffee_man_offer_drink_20260415T121533_seed42",
    "run_dir": "outputs/wan_vace_coffee_man_offer_drink/...",
    "config_path": "configs/experiments/wan_vace_coffee_man_offer_drink.yaml",
    "started_at": "2026-04-15T12:15:33",
    "finished_at": "2026-04-15T12:29:01",
    "status": "ok",
    "error": null,
    "config_hash": "sha1:de4a662e6d1b"
  },

  "experiment": {
    "name": "wan_vace_coffee_man_offer_drink",
    "notes": "남자+아이스커피 → 커피를 카메라 쪽으로 내미는 액션",
    "tags": ["baseline", "v1"]
  },

  "template": {
    "template_id": null,
    "motion_template": "lift_to_camera",
    "meme_template": null,
    "category": "person_action",
    "subcategory": "offer_drink",
    "intent": "product_showcase",
    "secondary": [
      {"category": "camera_move", "subcategory": "dolly_in"}
    ],
    "promoted_at": null
  },

  "input": {
    "mode": "i2v",
    "image_path": "assets/samples/coffee_man.png",
    "image_hash": "sha256:a1b2c3...",
    "reference_images": [],
    "prompt": "young man smiling and gently extending...",
    "negative_prompt": "low quality, blurry, watermark..."
  },

  "model": {
    "name": "wan2_1_vace_14b",
    "class": "i2v.models.wan2_1_vace_14b.Wan21VACE14BPipeline",
    "version": "diffusers-0.31",
    "quantization": {
      "transformer": "gguf_q4_k_m",
      "gguf_repo": "QuantStack/Wan2.1_14B_VACE-GGUF",
      "gguf_filename": "Wan2.1_14B_VACE-Q4_K_M.gguf",
      "text_encoder": "bnb_nf4"
    },
    "offload": "model_cpu_offload",
    "lora": []
  },

  "generation": {
    "seed": 42,
    "num_inference_steps": 40,
    "guidance_scale": 5.0,
    "width": 432,
    "height": 768,
    "fps": 16,
    "num_frames": 49,
    "duration_s": 3.0,
    "aspect": "9:16",
    "resolution_tier": "smoke"
  },

  "output": {
    "video_path": "outputs/.../wan21_vace_i2v_42.mp4",
    "video_size_mb": 1.2,
    "archived": false,
    "drive_path": null,
    "archived_at": null
  },

  "metrics": {
    "wall_sec": 807.4,
    "load_sec": null,
    "inference_sec": null,
    "vram_peak_mib": 17234.1,
    "ram_peak_mib": null,
    "steps_per_sec": null
  },

  "environment": {
    "gpu": "L4",
    "vram_total_gib": 22.5,
    "host": "gcp-vm",
    "driver": null,
    "torch": null,
    "diffusers": null
  }
}
```

### 필드 설명

#### `schema_version` (int, required)
스키마 버전. 현재 `2`.

#### `legacy` (bool)
v1 → v2 migration 으로 만들어진 엔트리면 `true`. 누락 필드는 null.

#### `run.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| run_id | str | `{experiment}_{YYYYMMDDTHHMMSS}_seed{N}` |
| run_dir | str | outputs 루트 기준 상대경로 |
| config_path | str | 실행 당시 YAML 경로 |
| started_at / finished_at | ISO8601 | local time |
| status | "ok" / "error" | |
| error | str / null | status="error" 시 `"<ExceptionType>: <msg>"` |
| config_hash | str | sha1 short. prompt/seed/steps/cfg/width/height/fps/model/quant/image 등 재현성 키 필드의 해시. **version 산정 기준** — 같은 experiment 내 동일 hash = 같은 version, 다르면 version+1 |

#### `experiment.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| name | str | YAML `experiment:` 또는 파일명 |
| notes | str | 자유 메모 (YAML `notes:`) |
| tags | list[str] | `["baseline", "v1", "lora-test"]` 등 자유 태그 |

#### `template.*` ⭐ v2 신규
| 필드 | 타입 | 설명 |
|---|---|---|
| template_id | str / null | 템플릿으로 승격된 실험만 채워짐 (예: `"tpl_drink_ripple_001"`) |
| **motion_template** | str / null | **신규 (2026-04-16)**. 활성 6개 모션 프리미티브 중 하나: `consume_product`, `lift_to_camera`, `dolly_in`, `orbit_pan`, `steam_rise`, `surface_shimmer`. 신규 실험 필수. 정의/맵핑은 `docs/TEMPLATES.md` |
| **meme_template** | str / null | **신규 (2026-04-16)**. 밈 포맷 (motion_template 과 직교). 활성: `meme_ai_character`, `meme_dance_ref`, `meme_ai_animal`. 일반 실험은 null |
| category | str | **v2 정규값**: `motion` 또는 `meme`. v1 legacy 값(person_action/camera_move 등)은 기존 meta 에만 존재 |
| subcategory | str | **v2 정규값** (9개): `consume_product`, `lift_to_camera`, `dolly_in`, `orbit_pan`, `steam_rise`, `surface_shimmer`, `meme_ai_character`, `meme_ai_animal`, `meme_dance_ref`. motion_template/meme_template 값과 일치시켜야 함 |
| intent | str / null | `product_showcase`, `meme`, `portrait`, `ambiance`, `tutorial` |
| secondary | list[{category, subcategory}] | (legacy) 복합 실험 시 보조 축들. 필터는 any-match |
| promoted_at | ISO8601 / null | 템플릿 승격 타임스탬프 |

일반 탐색 실험은 `template_id=null`, `promoted_at=null`.
신규 실험은 `category`/`subcategory` 모두 v2 정규값 사용.
`motion_template`/`meme_template` 와 `subcategory` 는 **같은 값을 중복 저장** (motion_template은 machine-queryable, subcategory는 human-readable). 값 불일치는 버그.

#### `input.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| mode | "i2v" / "r2v" / "t2v" | 생성 모드 |
| image_path | str | 입력 이미지 (t2v면 null) |
| image_hash | str | `sha256:<hex>` — 같은 이미지 재사용 탐지용 |
| reference_images | list[str] | r2v 레퍼런스 경로들 |
| prompt / negative_prompt | str | |

#### `model.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| name | str | `configs/models/*.yaml` 의 `name` |
| class | str | Python import path |
| version | str | `"diffusers-0.31"` 같은 라이브러리 버전 |
| quantization.transformer | str | `gguf_q4_k_m`, `fp16`, `bnb_nf4` 등 |
| quantization.gguf_repo / gguf_filename | str | GGUF 쓰는 경우만 |
| quantization.text_encoder | str | T5 등 텍스트 인코더 양자화 |
| offload | str | `model_cpu_offload` / `sequential_cpu_offload` / `none` |
| lora | list | LoRA 적용 시 `[{path, scale}, ...]` |

#### `generation.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| seed / steps / cfg | int / float | |
| width / height / fps / num_frames / duration_s | | |
| aspect | str | `"9:16"` 등 |
| resolution_tier | `"smoke" / "hd" / "fhd" / "2k"` | preset 계층 |

resolution tier 기준:
- `smoke` : <= 480 세로변 (속도 테스트용)
- `hd`    : 720×1280 급
- `fhd`   : 1080×1920 급
- `2k`    : 1440×2560 이상 (업스케일 후처리 포함 가능)

#### `output.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| video_path | str | run_dir 내부 mp4 |
| video_size_mb | float | |
| archived | bool | Drive 업로드 완료 여부 |
| drive_path | str / null | rclone remote path |
| archived_at | ISO8601 / null | |

#### `metrics.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| wall_sec | float | 전체 벽시계 (로드 포함 안 함 — 로드 재사용 배치 고려) |
| load_sec | float / null | 모델 최초 로드 (배치 전체에서 1회 측정) |
| inference_sec | float / null | 순수 추론 시간 (wall - 기타) |
| vram_peak_mib | float | `torch.cuda.max_memory_allocated()` |
| ram_peak_mib | float / null | 호스트 RAM 피크 (추후) |
| steps_per_sec | float / null | `num_inference_steps / inference_sec` |

#### `environment.*`
| 필드 | 타입 | 설명 |
|---|---|---|
| gpu | str | `nvidia-smi` 에서 추출, `"L4"` |
| vram_total_gib | float | |
| host | str | `"gcp-vm"`, `"local"` 등 |
| driver | str / null | nvidia driver version |
| torch / diffusers | str / null | 라이브러리 버전 |

---

### `run_num` vs `version` (Streamlit 컴퓨트, 저장 안 함)

- `run_num` = 전역 시간순 일련번호 (1..N). 매 실행마다 +1. 실패도 카운트. **언제나 안정** (새 run 추가돼도 기존 번호 안 변함).
- `version` = `(experiment, config_hash)` 그룹 내 first-appearance 순서. 같은 설정 재현 → 같은 version 유지. 설정 바뀌면 +1.

저장 필드 아님. Streamlit 이 index.jsonl 로드 시 시간순 + config_hash 기준으로 동적 계산.

---

## index.jsonl (flat entry)

Gallery 테이블 렌더링을 빠르게 하기 위한 **flat** 포맷. meta.json 의 subset 이며, 필요 필드만 한 줄 JSON 으로 append:

```json
{"schema_version":2,"run_id":"...","experiment":"wan_vace_coffee_man_offer_drink","motion_template":"lift_to_camera","meme_template":null,"template_category":"person_action","template_subcategory":"offer_drink","template_id":null,"tags":["baseline","v1"],"model":"wan2_1_vace_14b","quant":"gguf_q4_k_m","mode":"i2v","seed":42,"steps":40,"cfg":5.0,"width":432,"height":768,"fps":16,"resolution_tier":"smoke","wall_sec":807.4,"vram_peak_mib":17234,"status":"ok","archived":false,"started_at":"2026-04-15T12:15:33","video_path":"...","run_dir":"..."}
```

pandas 한 줄 로드:
```python
df = pd.read_json("outputs/index.jsonl", lines=True)
```

상세는 항상 `run_dir/meta.json` 을 재로드.

---

## 실험 → 템플릿 승격 플로우

```
1. 실험 실행 (meta.template_id=null)
   ↓
2. Gallery 에서 결과 확인, "좋다" 판단
   ↓
3. promote 액션 (Phase 4 구현)
   - templates/<template_id>.yaml 생성 (prompt + params 복사)
   - meta.json 업데이트: template_id, promoted_at
   - index.jsonl 재집계 (또는 해당 라인 patch)
```

`templates/` 디렉토리 포맷은 `docs/TEMPLATES.md` 참조.

---

## v1 → v2 Migration

`scripts/migrate_meta_v2.py` 실행:

1. `outputs/` 의 모든 `meta.json` 스캔
2. `schema_version` 이 없거나 < 2 이면 변환
   - 기존 flat 필드 → nested 구조에 매핑
   - `image_hash` 실제 파일 존재 시 계산, 없으면 null
   - `template.category/subcategory` 는 **실험명에서 휴리스틱 추론** (실패 시 null)
   - `legacy: true`, `schema_version: 2` 찍음
3. 백업: 원본은 `meta.json.v1.bak` 으로 보관
4. `outputs/index.jsonl` 재생성 (`index.jsonl.v1.bak` 백업)

실행:
```bash
python scripts/migrate_meta_v2.py --outputs-root outputs --dry-run  # 먼저 확인
python scripts/migrate_meta_v2.py --outputs-root outputs            # 적용
```

---

## 쓰기 규약

- `meta.json` 은 run 종료 시 **한 번만** atomic write (tmp → rename)
- `index.jsonl` 은 append-only. 수정은 재생성 스크립트로만
- `archived`/`drive_path` 업데이트는 sync 스크립트가 meta.json 을 rewrite + index 재빌드
- 스키마 필드 추가 시 이 문서 갱신 + `schema_version` bump 여부 판단
