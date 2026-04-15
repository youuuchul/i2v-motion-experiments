# Template Taxonomy & Promotion Flow

프로덕트 핵심 개념: **유저 이미지 + 템플릿 → 릴스 영상**. 템플릿은 우리 실험으로 검증된 (프롬프트 + 생성 파라미터) 묶음.

---

## Category / Subcategory

실험 및 템플릿을 **2단계 taxonomy** 로 분류한다. Gallery 필터 + 템플릿 추천 알고리즘 기준.

| category | subcategory 예 | 설명 |
|---|---|---|
| **person_action** | `offer_drink`, `pose_reveal`, `gesture_point`, `laugh_react`, `face_reveal`, `lift_to_camera` | 인물의 동작. 손/표정/얼굴 노출 변화 기반 |
| **camera_move** | `dolly_in`, `dolly_pan`, `orbit`, `crane_up`, `rack_focus`, `pull_back`, `face_to_bg`, `bg_to_face`, `rim_light`, `golden_hour`, `silhouette` | 카메라 워크 + 포커스/구도 이동 + 조명 룩. "카메라/렌즈 관점의 모든 변화"를 한 카테고리로 합침 (초기에 분리했다가 focus_shift ↔ camera_move 경계가 모호해 통합) |
| **food_motion** | `steam_rise`, `sauce_pour`, `cheese_pull`, `crust_crumble`, `item_appear` | 음식 자체의 미세 모션 + 오브젝트 추가/출현 |
| **drink_motion** | `foam_settle`, `ripple`, `ice_melt`, `condensation_drip` | 음료 출렁/거품/결로 |
| **menu_showcase** | `plate_spin`, `top_down_reveal`, `hero_push_in` | 메뉴 광고 프레이밍 |
| **ambiance** | `bokeh_breathe`, `string_lights_flicker`, `sunset_warm` | 배경 분위기 미세 모션 |
| **text_overlay** | (Phase 5+) | 자막/스티커 — 현재 지원 안 함 |

**조명 서브카테고리 (camera_move 하위) 가이드:**
- `rim_light` — 인물/피사체 윤곽선만 빛나는 역광 효과. AI/유저 모두 쉽게 인지
- `golden_hour` — 일출/일몰 톤. 따뜻한 색온도, 긴 그림자
- `silhouette` — 강한 역광으로 피사체가 검은 실루엣. 광고 임팩트 강함
- (broad/short lighting 등 인물 사진 전문 용어는 제외 — 차이가 미묘하고 일관된 결과 나오기 어려움)

**규칙:**
- 새 subcategory 는 **실험 3건 이상 안정적으로 나오면** 추가
- category 추가는 PR 논의 후 (Gallery UI 필터 영향)
- category/subcategory 는 `configs/experiments/*.yaml` 의 `template:` 블록에 필수

---

## Intent (선택)

| intent | 용도 |
|---|---|
| `product_showcase` | 음식/메뉴 등 상품 어필 |
| `meme` | 바이럴/밈 영상 |
| `tutorial` | 정보/가이드 |
| `ambiance` | 분위기용 배경 영상 |
| `portrait` | 인물 중심 |

미분류면 `null`.

---

## Experiment YAML (template 블록)

기존 YAML 에 `template:` 블록 추가:

```yaml
experiment: wan_vace_coffee_man_offer_drink
notes: "남자+아이스커피 → 커피를 카메라 쪽으로 내미는 액션"

template:
  category: person_action
  subcategory: offer_drink
  intent: product_showcase

model_config: configs/models/wan2_1_vace_14b.yaml
preset: configs/presets/smoke_test.yaml

input:
  mode: i2v
  image: assets/samples/coffee_man.png
  prompt: "..."
  negative_prompt: "..."

run:
  seed: 42
  num_inference_steps: 40
  guidance_scale: 5.0
```

`template` 블록은 없어도 실행은 됨 (기본: category=null). 단 Gallery 필터에서 빠짐.

---

## 승격 플로우 (실험 → 템플릿)

실험 결과가 "프로덕트에 쓸 만하다" 고 판단되면 템플릿으로 승격.

```
outputs/<exp>/<run_id>/meta.json  (template_id=null)
       │
       ▼  [Streamlit Gallery "Promote" 버튼 — Phase 4 구현]
       │
templates/<template_id>.yaml      (영구 자산)
meta.json 업데이트 (template_id, promoted_at)
```

### templates/ 포맷 (초안)

```yaml
template_id: tpl_drink_ripple_001
created_at: 2026-04-15T13:00:00
source_run_id: wan_vace_beer_drink_ripple_20260414-065811_seed42

category: drink_motion
subcategory: foam_settle
intent: product_showcase

prompt_template: |
  {subject} foam slowly settling with tiny bubbles rising through the {color} lager,
  glass condensation glistening, subtle liquid motion, moody warm pub lighting
# {subject}/{color} 등은 런타임에 유저 컨텍스트로 치환 (선택)

negative_prompt: "low quality, blurry, watermark, distorted, jittery, glitchy, text, logo"

params:
  seed: 42
  num_inference_steps: 40
  guidance_scale: 5.0

model:
  name: wan2_1_vace_14b
  quant: gguf_q4_k_m
  preset: smoke_test

composition_hint:
  aspect: "9:16"
  reference_image: templates/tpl_drink_ripple_001/ref.png  # 대표 첫 프레임
  guidance: "맥주잔이 프레임 중앙, 상단 1/3 은 거품, 배경은 어두운 단색"
```

### 승격 기준 (주관적, 업데이트 예정)

- 결과물이 목적대로 움직이는가 (저품질/뭉개짐 없음)
- 인풋 이미지 변경 시에도 재현성 어느 정도 있는가 (최소 2~3장 테스트)
- 프롬프트가 **피사체 비의존적**으로 일반화되는가 ({subject} 치환 가능)

---

## Frame Extraction (Phase 4 prep)

유저 업로드가 아닌 **우리가 기준으로 가진 템플릿 영상** → 대표 프레임 추출 → 프롬프트 생성 파이프라인에 활용.

### 추출 전략

| 영상 길이 | 추출 프레임 수 | 시점 |
|---|---|---|
| ≤ 5s | 3장 | 0%, 50%, 95% |
| 5~10s | 5장 | 0%, 25%, 50%, 75%, 95% |
| > 10s | 7장 | 0%, 15%, 35%, 50%, 65%, 85%, 95% |

**마지막을 100% 가 아닌 95%** 로 하는 이유: 많은 영상의 마지막 프레임이 fade-to-black 이라 대표성 낮음.

### 스크립트 (`scripts/extract_frames.py` — Phase 4 에서 구현)

```bash
python scripts/extract_frames.py \
  --video templates/source/cooking_reel.mp4 \
  --out templates/source/cooking_reel_frames/ \
  --count 5
```

출력: `frame_00.png`, `frame_02.png`, ..., `frame_95.png` (percent 기준 이름)

### VLM 호출 (Phase 4 에서 구현)

추출된 프레임들을 `gpt-5-mini` 에 묶어서 전달 → motion/composition/mood caption 추출 → 프롬프트 후보 생성.

```python
# scripts/video_to_prompt.py (예정)
prompt_candidates = vlm_extract(frames=[...], n=3, mood_hint="warm, cinematic")
```

---

## 운영 원칙

- **카테고리 쏠림 경계**: 한 category 가 50% 넘으면 다른 쪽 확장 필요 신호
- **실패 실험도 자산**: "이 조합은 안 된다" 는 정보도 `tags: ["failure", "low_motion"]` 로 남김
- **시즌 태그**: 시즌/이벤트성 템플릿은 `tags: ["summer", "halloween"]` 로 별도 관리
