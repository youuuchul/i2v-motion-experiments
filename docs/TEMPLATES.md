# Template Taxonomy & Promotion Flow

프로덕트 핵심 개념: **유저 이미지 + 템플릿 → 릴스 영상**. 템플릿은 우리 실험으로 검증된 (프롬프트 + 생성 파라미터) 묶음.

---

## 🎯 Active Motion Templates (v2 정책, 2026-04-16 확정)

**이제부터 신규 실험은 아래 6개 모션 중 하나로만 진행한다.** 15+ 개로 흩어져 있던 subcategory를 리소스·일관성 이유로 6개 프리미티브로 압축.

| # | motion_template | 카테고리 | 설명 |
|---|---|---|---|
| 1 | `consume_product` | Subject | 손이 제품을 입으로: 마시기 / 한 입 베어물기. F&B 실사용 모션 |
| 2 | `lift_to_camera` | Subject | 제품을 들어 카메라 쪽으로 보여주기 (offer / gesture / menu_hero 포함) |
| 3 | `dolly_in` | Camera | 천천히 줌인 / push-in |
| 4 | `orbit_pan` | Camera | 좌↔우 패닝 / 약한 오빗 |
| 5 | `steam_rise` | Product micro | 김·증기 상승 |
| 6 | `surface_shimmer` | Product micro | 표면 윤기 / 액체 파동 (glaze + ripple 통합) |

**규칙:**
- 새 실험 config의 `template` 블록은 위 6개 중 하나에 맵핑되어야 함
- 6개로 커버 안 되는 케이스는 **신규 모션 추가 PR** 논의부터
- 조명/광학/분위기(rim_light, golden_hour, silhouette, bokeh, focus_shift)는 **모션이 아님** → `configs/presets/lighting/*.yaml`로 분리해 모션과 직교 조합
- face_reveal은 **실험 품질 불안정**으로 폐기

**Why:** L4 한 장(리소스 상한) × 카테고리 혼잡 감당 불가 → 6개 × 샘플 3장 = 18런 / 라운드로 고정.

---

## 🎬 Meme Templates (v2 정책, 2026-04-16 확정)

모션 템플릿과 **직교**하는 축. 모션은 "프레임 내 움직임 프리미티브", 밈은 "포맷/내러티브"다. 한 실험은 motion_template + meme_template 각각 0~1개를 가질 수 있음.

| # | meme_template | 입력 | 포맷 설명 | 생성 방식 | 참고 |
|---|---|---|---|---|---|
| 1 | `meme_ai_character` | 제품 사진 | **제품 자체가 캐릭터가 되는 밈**. (a) 제품이 일어나/변형돼 캐릭터화되거나, (b) 처음부터 캐릭터 형태. 외부 캐릭터가 **아니라** 제품 그 자체의 의인화/캐릭터화 | **프롬프트만으로 가능** (i2v + text). 얼굴·팔이 제품 위에 자라는 "feature emergence" 필요 | [reel 1 (올리브오일 병 의인화)](https://www.instagram.com/reels/DWnY1wGEurB/) · [reel 2 (클레이 바나나/감자/냉장고)](https://www.instagram.com/reels/DW0T0Qfk1Mr/) |
| 2 | `meme_dance_ref` | 인물 사진 + **레퍼런스 춤 영상** | 사진 속 인물이 유행 춤(예: 붐샤카라카)을 따라함 | **레퍼런스 영상 필요 — 표준 API 미지원**. PoC 트랙 (아래 참고) | [short](https://www.youtube.com/shorts/0qKKrIXT1Lo) |
| 3 | `meme_ai_animal` | 제품/환경 사진 | **외부 캐릭터 또는 동물이 씬에 등장해 제품과 상호작용**. 사람형 3D 마스코트·픽사풍 캐릭터·귀여운 동물 등이 프레임에 들어와서 반응. (이전 #1의 "AI 캐릭터 등장" 밈은 이 #3에 속함 — 제품은 그대로 있고 외부 엔티티가 추가되는 구조) | **프롬프트만으로 가능** (i2v + text, 또는 t2v) | [short (시장 고구마 파는 비숑)](https://www.youtube.com/shorts/Ib766UdgKtc) |

> **중요 구분 — #1 vs #3:**
> - `meme_ai_character` (#1) = **제품 그 자체가 캐릭터**. 맥주병 위에 얼굴이 자람, 클레이 바나나 캐릭터 등. 프레임의 주인공이 제품=캐릭터.
> - `meme_ai_animal` (#3) = **외부 캐릭터/동물이 방문**. 치킨 옆에 다람쥐가 등장, 맥주잔 뒤에서 픽사 마스코트가 튀어나옴. 제품은 배경으로 유지되고 외부 엔티티가 추가됨.
> - 이름 `meme_ai_animal` 은 유지하지만 **범위는 character+animal 양쪽**. 향후 빈번하면 `meme_ai_guest` 로 rename 검토.

### ❗ 레퍼런스-영상 필요 케이스 처리 방안 (meme_dance_ref)

"image + reference video → video" 는 Wan VACE 표준 i2v 파이프라인에 없음. 세 가지 PoC 후보 (별도 트랙):

| 대안 | 방식 | 리스크 | 영상 길이 확장 |
|---|---|---|---|
| **A. Control conditioning** | 레퍼런스에서 pose/depth/optical-flow 추출 → conditioning 주입 (ControlNet 계열) | VACE가 실제로 control video 입력 지원하는지 확인 필요 (문서상 "all-in-one" 주장 있음) | 자연스러움 |
| **B. 키프레임 체이닝** | 레퍼런스에서 키프레임 추출 → 키프레임 간 i2v + 프레임 보간 | 보간 품질, 연결부 끊김 | 길이 확장 같이 해결 |
| **C. 클립 연결** | 짧은 5s 클립 여러 개 생성 → last-frame→first-frame 체이닝 | 샷 간 identity 유지 | 단순 연장만 |

**현재 상태:** A/B/C 중 1개 PoC 착수 필요. 배치 실험 범위에서 제외.

#### 트래킹 중인 레퍼런스 댄스 밈

| id | 레퍼런스 | 자산 경로 | 안무 시퀀스 (5s beat) |
|---|---|---|---|
| `boomshakalaka` | https://www.youtube.com/shorts/0qKKrIXT1Lo | `assets/memes/dance_ref/frames/` (구 src.mp4) | 좌우 스웨이 → 팔 위로 흔들 → 주먹 펌프 → 홉 → 포즈 |
| `boat_dance` | https://www.youtube.com/shorts/Or_1yQGAjCQ | `assets/memes/dance_ref/boat_dance/` (source.webm, frames/, start_frame_kid_standing.png) | 정적 서기 → 양손 앞으로 펴고 아래 흔들 → 양손 회전 → 앞뒤 양팔 뻗기 → 수영 스트로크 → 한 팔 앞으로 쭉 |

**boat_dance (드래곤 보트 "레전드 꼬마 선장") 안무 디테일:**
드래곤 보트 뱃머리에 선 꼬마(검은 전통 의상 + 뾰족한 모자 + 선글라스)가 뒤에서 노 젓는 팀을 지휘하듯 6단계 안무를 수행.
1. **0.0–0.8s** 정적 서기 — 양손 가볍게 앞으로 내리고 정면을 본다
2. **0.8–1.6s** 양손을 앞으로 살짝 펴고 아래쪽에서 좌우로 가볍게 흔든다 (지휘)
3. **1.6–2.5s** 양손을 앞에서 원을 그리듯 돌린다 (패들 rotation 모사)
4. **2.5–3.3s** 한쪽 팔은 앞으로, 반대쪽 팔은 뒤로 크게 벌린다 (런지 자세)
5. **3.3–4.1s** 앞뒤 팔을 교대하며 수영 스트로크 동작
6. **4.1–5.0s** 마지막 한 팔(오른팔)을 앞쪽 카메라 방향으로 쭉 뻗으며 마무리 포즈

**규칙 재확인 (critical):** `meme_dance_ref` 실험의 i2v 입력 이미지는 **반드시 `assets/samples/*` 자체 샘플만 사용**. 레퍼런스 프레임(`assets/memes/dance_ref/*/frames/*`, `start_frame_*`)을 입력으로 쓰는 것은 원칙적 **금지**. 단 벤치마크 용 **1회성 ref-frame baseline** 은 실험 로그에 예외 사유 명시 후 허용 (`tags: ["ref_frame_exception_1shot"]`). 나머지 실험은 모두 자체 샘플.

### Meme 프롬프트 템플릿 (슬롯 DSL)

`meme_ai_character`, `meme_ai_animal` 처럼 프롬프트로 해결되는 케이스는 `src/i2v/prompts/` 아래 슬롯 빌더를 둘 예정:

```
{appear_from} 에서 {subject}({style}) 가 나타나
{target} 을/에 {interaction_verb},
camera: {camera_motion}, lighting: {light}
```

슬롯:
- `appear_from` — behind the glass / top of frame / side
- `subject` + `style` — a small 3D pixar-style mascot / a cartoon squirrel / a chibi anime girl
- `target` — 제품/음식
- `interaction_verb` — sniff / lick / reach / dance / taste
- `camera_motion` — static / dolly-in / orbit-pan

---

## 🏷 Canonical category / subcategory / intent (v2)

신규 실험 config의 `template` 블록은 아래 정규화 값만 사용한다 (2026-04-16~).

### category (2개)
| value | 의미 |
|---|---|
| `motion` | 활성 6개 모션 프리미티브 중 하나 사용 |
| `meme` | 활성 3개 밈 포맷 중 하나 사용 |

### subcategory (9개 = motion 6 + meme 3)
| value | category | 비고 |
|---|---|---|
| `consume_product` | motion | |
| `lift_to_camera` | motion | |
| `dolly_in` | motion | |
| `orbit_pan` | motion | |
| `steam_rise` | motion | |
| `surface_shimmer` | motion | |
| `meme_ai_character` | meme | **제품 자체 캐릭터화**. 하위 태그(선택): `realistic_food_anthropomorph` / `claymation_character` / `product_transform` |
| `meme_ai_animal` | meme | **외부 캐릭터/동물 등장** (범위 확장). 하위 태그(선택): `external_animal` / `external_mascot` / `external_character` |
| `meme_dance_ref` | meme | 레퍼런스 영상 요구 — PoC 트랙 |

### intent (5개)
| value | 쓰임 |
|---|---|
| `product_showcase` | 제품/메뉴 어필 (motion 기본) |
| `meme` | 바이럴/밈 포맷 (meme 기본) |
| `portrait` | 인물 중심 |
| `ambiance` | 분위기/배경 |
| `tutorial` | 정보/가이드 |

### 배치 블록 예시
```yaml
template:
  motion_template: null                   # motion 실험이면 값 채움
  meme_template: meme_ai_character        # meme 실험이면 값 채움
  category: meme                          # subcategory 가 meme_* 이면 meme
  subcategory: meme_ai_character          # = meme_template 값과 일치
  intent: meme
```

`motion_template` / `meme_template` 는 기계 쿼리용 전용 필드, `category` / `subcategory` 는 human-readable. 값은 반드시 일치.
legacy v1 taxonomy 는 문서 하단 **Archived taxonomy** 에 보존.

---

## 📌 기존 config → 6개 템플릿 맵핑

아래 config들은 **삭제하지 않음**. 자산(프롬프트·이미지)은 라이브러리로 보존하고, 여기서 활성 6개 중 어디로 귀속되는지만 선언한다. `archived` 표시된 건 신규 실험에서 사용하지 않음 (기존 결과물·자산은 보존).

| 기존 config | motion_template | 메모 |
|---|---|---|
| wan_vace_beer_drink_ripple | `surface_shimmer` | |
| wan_vace_beer_food_glaze | `surface_shimmer` | sauce_pour → shimmer 계열로 통합 |
| wan_vace_beer_food_steam | `steam_rise` | |
| wan_vace_beer_man_topview_face_reveal | `archived` | face_reveal 품질 실패 — 폐기 |
| wan_vace_beer_man_topview_lift | `lift_to_camera` | |
| wan_vace_beer_man_topview_steam | `steam_rise` | |
| wan_vace_beer_menu_hero | `dolly_in` | hero_push_in = dolly_in 변형 |
| wan_vace_coffee_man_dolly_in | `dolly_in` | |
| wan_vace_coffee_man_dolly_pan | `orbit_pan` | |
| wan_vace_coffee_man_offer_drink | `lift_to_camera` | offer_drink는 lift 계열 |
| wan_vace_coffee_man_rim_light | `archived` | 조명 프리셋 — motion 아님 |
| wan_vace_coffee_man_silhouette | `archived` | 조명 프리셋 |
| wan_vace_man_box_face_reveal | `archived` | face_reveal 폐기 |
| wan_vace_man_box_gesture_point | `lift_to_camera` | 제품 제시 제스처로 통합 |
| wan_vace_man_box_lift_to_camera | `lift_to_camera` | |
| wan_vace_sample_ambiance_bokeh | `archived` | ambiance — motion 아님 |
| wan_vace_sample_drink_ripple | `surface_shimmer` | |
| wan_vace_sample_focus_shift | `archived` | lens/focus — motion 아님 |
| wan_vace_sample_gesture_point | `lift_to_camera` | |
| wan_vace_sample_golden_hour | `archived` | 조명 프리셋 |
| wan_vace_sample_offer_drink | `lift_to_camera` | |

**카운트:** lift_to_camera 6 / surface_shimmer 3 / steam_rise 2 / dolly_in 2 / orbit_pan 1 / consume_product 0(신규, 미존재) / archived 7.

**TODO:** `consume_product` 샘플 config 1건 신규 작성해 L4 품질 검증.

---

## 📚 Archived taxonomy (legacy reference)

아래 category/subcategory 체계는 v1 시기(2026-04-15까지) 실험 YAML 작성에 쓰였다. **신규 실험에는 더 이상 쓰지 않음**. 기존 meta.json / index.jsonl 의 `template.category`, `template.subcategory` 필드는 이 표를 근거로 해석한다.

### (legacy) Category / Subcategory

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

**규칙 (legacy — 신규 실험에 적용 안 함):**
- ~~새 subcategory 는 실험 3건 이상 안정적으로 나오면 추가~~
- ~~category 추가는 PR 논의 후~~
- ~~category/subcategory 는 template: 블록에 필수~~

신규 실험 규칙은 본 문서 상단 **Active Motion Templates (6)** 참조.

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
