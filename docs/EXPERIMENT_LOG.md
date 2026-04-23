# Experiment Log

실험 기록 타임라인. 배치별/실험별 의도와 결과를 추적한다.

**각 실험 엔트리에 반드시 포함할 항목:**
- **원본 소스**: i2v base 이미지 경로 (자체 샘플인지, 레퍼런스 프레임인지 명시). source_reference URL 있으면 기재.
- **소속 템플릿**: motion_template 또는 meme_template (docs/TEMPLATES.md 기준 9개 중 하나)
- **생성 duration**: 생성된 영상 길이 (3s / 5s / ...)
- **레이턴시**: wall_sec (모델 로드 제외 순수 생성+저장 시간)
- **의도/가설**: 이 실험을 왜 돌렸는지 한 줄

Streamlit Gallery(`http://<HOST>:8501`)에서 영상과 함께 확인 가능.

> **자동 업데이트 규칙**: 새 배치 실행/완료 시 이 문서에 해당 배치 섹션 추가. `CLAUDE.md` 참조.

---

## 집계 (2026-04-17 기준)

| 항목 | 값 |
|---|---|
| 총 런 수 | 43+ |
| 성공 (ok) | 43+ |
| 실패 (error) | 0 |
| 모델 | Wan2.1-VACE-14B (Q4_K_M + bnb4 T5) |
| GPU | L4 24GB |
| smoke 해상도 | 432×768 · 16fps |

---

## Batch 1 — Legacy baseline (2026-04-14)

첫 파이프라인 검증. smoke 해상도(432×768), 3초, seed 42. legacy v1 taxonomy.

| 시간 (UTC) | 실험 | mode | 템플릿 | wall | VRAM |
|---|---|---|---|---|---|
| 04-14 03:18 | smoke_wan2_1_vace_14b | i2v | — | — | — |
| 04-14 06:58 | beer_drink_ripple | i2v | drink_motion/ripple | 33m | 14.96GB |
| 04-14 07:31 | beer_food_steam | i2v | food_motion/steam | 36m | 14.96GB |
| 04-14 08:07 | coffee_man_dolly_pan | i2v | camera_move/dolly_pan | 37m | 14.96GB |
| 04-14 08:44 | coffee_man_offer_drink | i2v | person_action/offer | 37m | 14.96GB |
| 04-14 09:21 | sample_drink_ripple | i2v | drink_motion/ripple | 37m | 14.96GB |
| 04-14 09:58 | sample_focus_shift | i2v | camera_move/focus | 37m | 14.96GB |
| 04-14 10:35 | sample_offer_drink | i2v | person_action/offer | 36m | 14.96GB |

**관찰**: 파이프 동작 확인. 런당 ~33-37분, VRAM 14.96GB 안정.

---

## Batch 2 — v2 taxonomy + category expansion (2026-04-15)

카테고리 확장(5) + 조명(3) + 탑뷰 새 이미지(3) + man_box(3). v2 taxonomy 도입.

| 시간 (UTC) | 실험 | mode | 템플릿 | wall | 비고 |
|---|---|---|---|---|---|
| 04-15 01:39 | sample_gesture_point | i2v | person_action/gesture | 33m | |
| 04-15 04:17 | coffee_man_dolly_in | i2v | camera_move/dolly_in | 33m | |
| 04-15 04:50 | beer_food_glaze | i2v | food_motion/sauce_pour | 37m | |
| 04-15 05:27 | beer_menu_hero | i2v | menu_showcase/hero | 37m | |
| 04-15 06:04 | sample_ambiance_bokeh | i2v | ambiance/bokeh | 36m | |
| 04-15 06:40 | coffee_man_rim_light | i2v | camera_move/rim_light | 35m | 조명 프리셋 |
| 04-15 07:16 | sample_golden_hour | i2v | camera_move/golden_hour | 35m | 조명 |
| 04-15 07:51 | coffee_man_silhouette | i2v | camera_move/silhouette | 36m | 조명 |
| 04-15 08:32 | beer_man_topview_steam | i2v | food_motion/steam | 33m | 탑뷰 (exif_broken) |
| 04-15 09:05 | beer_man_topview_lift | i2v | person_action/lift | 36m | 탑뷰, challenging |
| 04-15 09:40 | beer_man_topview_face_reveal | i2v | person_action/face_reveal | 36m | **품질 실패 → archived** |
| 04-15 10:51 | beer_man_topview_steam (재실행) | i2v | food_motion/steam | 33m | exif 수정 후 재실행 |
| 04-15 11:24 | beer_man_topview_lift (재실행) | i2v | person_action/lift | 36m | |
| 04-15 12:00 | beer_man_topview_face_reveal (재실행) | i2v | person_action/face_reveal | 37m | 여전히 불안정 |
| 04-15 13:35 | man_box_face_reveal | i2v | person_action/face_reveal | 33m | face_reveal 최종 판단용 |
| 04-15 14:07 | man_box_lift_to_camera | i2v | person_action/lift | 35m | |
| 04-15 14:43 | man_box_gesture_point | i2v | person_action/gesture | 36m | |

**결정**: face_reveal 품질 불안정 → **모션 템플릿에서 폐기**. consume_product 으로 대체.

---

## Batch 3 — Motion template v2 (2026-04-16 AM)

모션 템플릿 6종 확정 후 man_object.png(Marshall 스피커)로 4종 검증 + coffee_consume_drink 1종.

| 시간 (UTC) | 실험 | motion_template | input_type | wall |
|---|---|---|---|---|
| 04-16 06:10 | man_object_lift_to_camera | lift_to_camera | man_object.png | 33m |
| 04-16 06:43 | man_object_dolly_in | dolly_in | man_object.png | 36m |
| 04-16 07:19 | man_object_orbit_pan | orbit_pan | man_object.png | 36m |
| 04-16 07:55 | man_object_surface_shimmer | surface_shimmer | man_object.png | 36m |
| 04-16 08:31 | coffee_consume_drink | consume_product | coffee_man.png | 35m |

**비고**: consume_product(face_reveal 대체) + 스피커 이미지로 모션 프리미티브 4종 검증. steam_rise 는 스피커와 안 맞아 제외 (기존 beer_food_steam 으로 커버).

---

## Batch 4 — 추가 모션 + 밈 v1 (2026-04-16 PM)

유저가 추가 실행 (face_reveal/gesture_point 재시도 + coffee_man_lift + 밈 v1 generic 2건).

| 시간 (UTC) | 실험 | template | input_type | wall |
|---|---|---|---|---|
| 04-16 11:33 | man_object_face_reveal | face_reveal | man_object.png | 33m |
| 04-16 12:06 | man_object_gesture_point | gesture_point | man_object.png | 36m |
| 04-16 12:42 | coffee_man_lift_to_camera | lift_to_camera | coffee_man.png | 37m |
| 04-16 13:19 | beer_meme_ai_animal | meme_ai_animal | beer.png | 37m |
| 04-16 13:56 | beer_meme_ai_character | meme_ai_animal (retag) | beer.png | 36m |

**비고**: 밈 v1 generic = 외부 마스코트/다람쥐 등장 프롬프트 (3초). taxonomy 재정의 후 둘 다 meme_ai_animal 로 재분류.

---

## Batch 5 — 밈 첫 시도 3초 (2026-04-16 15:45)

meme_ai_character v1 프롬프트 (얼굴만 emergence), 3초 smoke.

| 시간 (UTC) | 실험 | meme_template | input_type | wall | 비고 |
|---|---|---|---|---|---|
| 04-16 15:45 | meme_char_beer_bottle_angry (v1) | meme_ai_character | beer.png | 33m | 3초, 얼굴만 |

**결정**: "눈만 달려서 움직이는 것" 불충분 → **풀바디 스탠드업 + 구체 행동(말하기/걷기/날기)** 프롬프트로 전면 재작성. duration 3s → 5s.

---

## Batch 6 — 밈 5초 풀바디 + t2v (2026-04-16 16:30 ~ 진행 중)

17개 config, 5초 preset (meme_5s.yaml). 3개 밈 템플릿 동시 검증.

### meme_ai_character (#1 — 제품 자체 캐릭터화) × 5

| 시간 (UTC) | 실험 | 원본 이미지 | 레퍼런스 소스 | dur | wall | 의도 |
|---|---|---|---|---|---|---|
| 04-16 16:34 | beer_bottle_angry (v2) | `beer.png` (자체) | — | 5s | 57m | 맥주병이 일어나 다리 자라 카메라로 걸어오며 외침. 풀바디 스탠드업 첫 검증 |
| 04-16 17:30 | beer_chicken_shock | `beer.png` (자체) | — | 5s | 60m | 치킨 조각에 날개 자라 비행 + squawk. 비행 모션 가능한지 검증 |
| 04-16 18:30 | refA_oil_bottle | `ai_character_1/frame_0.jpg` | [IG reel](https://www.instagram.com/reels/DWnY1wGEurB/) | 5s | 60m | 이미 얼굴/팔 있는 올리브오일 병 → 풀바디 rant + 카메라 스텝. 레퍼런스 프레임 시작 시 품질 이점 측정 |
| 04-16 19:30 | refB_banana | `ai_character_2/frame_25.jpg` | [IG reel](https://www.instagram.com/reels/DW0T0Qfk1Mr/) | 5s | 60m | 클레이 바나나 훅에서 뛰어내려 hop + 재잘. 클레이 스타일 유지 가능한지 |
| 04-16 20:31 | refB_potato | `ai_character_2/frame_75.jpg` | [IG reel](https://www.instagram.com/reels/DW0T0Qfk1Mr/) | 5s | 60m | 클레이 감자 봉지 열고 걸어나옴 + narrate. 래퍼 유지 + 풀바디 |

### meme_ai_animal (#3 — 외부 캐릭터/동물 등장) × 7

| 시간 (UTC) | 실험 | mode | 원본 이미지 | 레퍼런스 소스 | dur | wall | 의도 |
|---|---|---|---|---|---|---|---|
| 04-16 21:30 | ref_bichon_market | i2v | `ai_animal/frame_0.jpg` | [YT short](https://www.youtube.com/shorts/Ib766UdgKtc) | 5s | 60m | 비숑 고구마 시장 — 레퍼런스 프레임에서 시작해 자연스러운 미세 움직임 이어가기 |
| 04-16 22:30 | cat_cafe_t2v | **t2v** | `sample.png` (placeholder) | — | 5s | 60m | **이미지 없이 텍스트만** 고양이 바리스타. t2v 모드 실전 검증 |
| 04-16 23:30 | hamster_fruit_t2v | **t2v** | `sample.png` (placeholder) | — | 5s | 59m | **텍스트만** 햄스터 과일 장수. 동물 다양성 |
| 04-17 ~00:30 | dog_bakery_t2v | **t2v** | `sample.png` (placeholder) | — | 5s | ~60m | **텍스트만** 코기 제빵사 |
| 04-17 01:29 | pig_streetfood_t2v | **t2v** | `sample.png` (placeholder) | — | 5s | 60m | **텍스트만** 돼지 포차 |
| 04-17 02:29 | guest_pixar_mascot_beer | i2v | `beer.png` (자체) | — | 5s | 59m | 외부 픽사 마스코트가 씬에 등장 (외부 character 변형, #3 범위 확장 검증) |
| 04-17 03:29 | guest_chibi_coffee | i2v | `coffee_man.png` (자체) | — | 5s | 60m | 외부 치비 애니메 캐릭터 등장 |

### meme_dance_ref (#2 — 댄스) × 5

| 시간 (UTC) | 실험 | mode | 원본 이미지 | 레퍼런스 소스 | dur | wall | 의도 |
|---|---|---|---|---|---|---|---|
| 04-17 04:28 | dance_ref_frame0 | i2v | `dance_ref/frame_0.jpg` ⚠️ | [YT short](https://www.youtube.com/shorts/0qKKrIXT1Lo) | 5s | 60m | ⚠️ **규칙 위반 (사후 폐기)** — 레퍼런스 프레임 직접 입력. 새 규칙: 프레임은 프롬프트 참고용만 |
| 04-17 05:28 | dance_ref_frame50 | i2v | `dance_ref/frame_50.jpg` ⚠️ | 동일 | 5s | 59m | ⚠️ 동일 규칙 위반 |
| 04-17 06:28 | dance_t2v_freestyle | t2v | `sample.png` (placeholder) | 동일 | 5s | 60m | **텍스트만** 댄스 묘사 — t2v 남발 피드백 이후 마지막 t2v |
| 04-17 07:29 | dance_coffee_man_subtle | i2v | `coffee_man.png` (자체 ✓) | 동일 | 5s | 60m | 자체 샘플 + 서틀 상체 그루브 |
| (kill됨) | dance_man_object_subtle | i2v | `man_object.png` (자체 ✓) | 동일 | 5s | — | Round 6 배치로 이월 |

**VRAM 관측**: 5초 = 17.14GB (3초 14.96GB 대비 +2.2GB). L4 24GB 내 안전.
**런타임**: 5초 = ~60분/런 (3초 ~33분 대비 1.8×).

---

## Batch 7 + 8 통합 런치 — Round 6 Dance Reproduction + Round 7 템플릿 확장 (2026-04-17 09:32 UTC)

단일 `run_batch.py` 호출로 20런 순차 실행. 모델 1회 로드. 도커 컨테이너 `streamlit` 내부에서 detached 실행 (세션 독립).

- **Log**: `logs/batch_round6_7_20260417_093203.log`
- **예상 런타임**: ~20시간 (1런 ≈ 60분)
- **규칙**: 모두 i2v + `assets/samples/*` 자체 샘플 only. 프레임 입력 전면 금지.

### Round 6 — Dance Reproduction × 8 (1~8)

**목적**: 자체 샘플 이미지 + 프롬프트 조합만으로 레퍼런스 댄스 ([붐샤카라카 YT short](https://www.youtube.com/shorts/0qKKrIXT1Lo)) 모션 재현. **2축 설계** — 프롬프트 전략 × 베이스 이미지.

**규칙 (강화)**: 댄스 밈 i2v base = **반드시 `assets/samples/*` 자체 샘플만**. 레퍼런스 프레임은 프롬프트 작성 참고용만, 생성 입력 이미지로 사용 금지 (예외 없음).

**프롬프트 전략**:
- `subtle` = 상체만 미세 그루브 (baseline)
- `boom` = 풀안무 상세 서술 (힙스웨이 + 팔 교차 + 피스트펌프 + 홉)
- `beat_matched` = 5초를 1초 단위로 쪼갠 시간 세그먼트 안무 (신규)
- `viral_label` = "trending TikTok viral dance" 간단 라벨 (신규)

| # | 실험 | 베이스 | 프롬프트 전략 | 의도 |
|---|---|---|---|---|
| 1 | dance_man_object_subtle | man_object.png | subtle | Batch6 에서 kill된 #17 재실행 (baseline) |
| 2 | dance_coffee_man_boom | coffee_man.png | boom | 프롬프트 풍부도 효과 (vs Batch6 subtle) |
| 3 | dance_coffee_man_beat_matched | coffee_man.png | beat_matched | 시간 세그먼트 기법 검증 |
| 4 | dance_coffee_man_viral_label | coffee_man.png | viral_label | 미니멀 프롬프트로 모델이 얼마나 해석하나 |
| 5 | dance_man_object_boom | man_object.png | boom | 베이스 변경, 프롭(스피커) 유지 |
| 6 | dance_man_box_boom | man_box.JPG | boom | 베이스 변경, 프롭(박스) 유지 |
| 7 | dance_sample_female_boom | sample.png | boom (여성) | **주체 성별 매칭** — 레퍼런스도 젊은 여성 |
| 8 | dance_sample_female_beat_matched | sample.png | beat_matched (여성) | 주체 매칭 + 시간 세그먼트 조합 |

**비교 포인트**:
- 2/3/4: 프롬프트 전략 효과 (coffee_man 고정)
- 2/5/6/7: 베이스 이미지 효과 (boom 고정)
- 7 vs 8: 여성 베이스에서 beat_matched 개선 여부
- 1 (#17 재실행) vs Batch6 #16: subtle 재현성

### Round 7 — Meme × 6 + Motion × 6 (9~20)

| # | 실험 | 베이스 | 카테고리 | 의도 |
|---|---|---|---|---|
| 9 | meme_char_beer_lazy_stretch | beer.png | meme_ai_character | 맥주병 하품+기지개 (평화로운 캐릭터 톤) |
| 10 | meme_char_beer_panic_run | beer.png | meme_ai_character | 맥주병 놀라서 도망 (급동작 검증) |
| 11 | meme_animal_squirrel_beer | beer.png | meme_ai_animal | 다람쥐가 맥주병에 관심 (외부 동물 등장) |
| 12 | meme_animal_fairy_coffee | coffee_man.png | meme_ai_animal | 픽시 요정 + 마법 가루 (외부 캐릭터 등장) |
| 13 | meme_dance_man_box_beat_matched | man_box.JPG | meme_dance_ref | man_box 베이스 + 시간 세그먼트 |
| 14 | meme_dance_sample_viral_label | sample.png | meme_dance_ref | 여성 주체 + 미니멀 라벨 |
| 15 | sample_consume_product | sample.png | motion/consume_product | **신규 프리미티브** (기존 0건) — 라떼 한 모금 |
| 16 | sample_lift_to_camera | sample.png | motion/lift_to_camera | 여성 샘플에서 lift 재현성 |
| 17 | man_box_dolly_in | man_box.JPG | motion/dolly_in | man_box 베이스 dolly-in |
| 18 | man_box_orbit_pan | man_box.JPG | motion/orbit_pan | man_box 베이스 좌↔우 팬 |
| 19 | sample_steam_rise | sample.png | motion/steam_rise | 라떼 김 상승 (drink 계열 steam) |
| 20 | coffee_man_surface_shimmer | coffee_man.png | motion/surface_shimmer | 아이스커피 응결수 + 표면 리플 |

**Round 7 목적**:
- 밈 3종 템플릿 각 2개씩 추가 — 액션 다양성 (평화/급동작/외부동물/외부캐릭터) 검증
- 모션 6 프리미티브 각 1개씩 — 특히 `consume_product` 신규 프리미티브 첫 샘플 확보

---

## Batch 9 — Round 8: boat_dance + meme_ai_character 확장 (2026-04-18 예정)

Batch 7+8 완료(= `coffee_man_surface_shimmer` 종료) 직후 자동 이어서 launch. 총 12런 순차, `run_batch.py` 단일 호출, 모델 1회 로드, `nohup` detached (VS Code/SSH 독립).

- **Launch 방식**: `scripts/launch_batch9_after_current.sh` — 현재 PID 모니터링 후 종료 확인되면 본 배치 시작
- **Log**: `logs/batch_round8_<timestamp>.log`
- **예상 런타임**: ~12시간 (1런 ≈ 60분)
- **자산 신규**: `assets/memes/dance_ref/boat_dance/` (source.webm, frames/, start_frame_kid_standing.png)

### Round 8-A — boat_dance meme × 7 (1~7)

**목적**: 신규 레퍼런스 "레전드 꼬마 선장" (드래곤 보트 지휘 댄스) 재현. 6단계 안무(정적→아래흔들→회전→앞뒤뻗기→수영→쭉뻗기)를 자체 샘플에서 프롬프트만으로 얼마나 살릴 수 있는가.

**레퍼런스**: [YT short Or_1yQGAjCQ](https://www.youtube.com/shorts/Or_1yQGAjCQ)

**규칙 재확인**: `meme_dance_ref` i2v base = `assets/samples/*` 자체 샘플만. 단 **1회성 ref-frame baseline(#1)** 은 user 명시 승인하의 예외 (`tags: ref_frame_exception_1shot`).

| # | 실험 | 베이스 | 변주 | 의도 |
|---|---|---|---|---|
| 1 | meme_dance_boat_ref_frame | `boat_dance/start_frame_kid_standing.png` ⚠️예외 | beat_matched | **ref-frame 1회 예외** — 원본 프레임에서 출발 시 재현도 벤치마크 |
| 2 | meme_dance_boat_boat_kid_a | `boat_kid.png` (자체 ✓) | beat_matched full-script | 자체 샘플 + 시간 세그먼트 풀스크립트 |
| 3 | meme_dance_boat_boat_kid_b | `boat_kid.png` (자체 ✓) | natural-sequence | 동일 베이스, 자연 서술 프롬프트 — A/B 비교 |
| 4 | meme_dance_boat_coffee_man_a | `coffee_man.png` (자체 ✓) | beat_matched | 카페 청년이 안무 따라할 때 coffee cup 유지 검증 |
| 5 | meme_dance_boat_coffee_man_b | `coffee_man.png` (자체 ✓) | reference-invoke | "legendary dragon-boat kid captain" 살짝 invoke — identity 유지 vs. 레퍼런스 강도 |
| 6 | meme_dance_boat_man_object_a | `man_object.png` (자체 ✓) | beat_matched (한손 dance) | 제품 보유 상태 + 편손 안무 |
| 7 | meme_dance_boat_man_object_b | `man_object.png` (자체 ✓) | both-hands (제품 겨드랑이) | 제품 겨드랑이 tuck + 양손 풀 시퀀스 |

**비교 포인트**:
- 1 vs 2: ref-frame 입력 vs 자체 샘플 — 레퍼런스 프레임 사용 효과 실증
- 2 vs 3: full-script vs natural-sequence 프롬프트 전략
- 4 vs 5: 자체 샘플 + 풀스크립트 vs 레퍼런스 invoke 문구
- 6 vs 7: 한손 vs 양손 안무 (오브젝트 유지 vs 동작 풍부도)

### Round 8-B — meme_ai_character 확장 × 5 (8~12)

**목적**: 제품 자체의 의인화 밈을 peferral 피자 + 일본 이자카야 닭꼬치/맥주 세트로 확장. 기존 beer/chicken/coffee 캐릭터 외 신규 제품군 검증 + 멀티 캐릭터 상호작용(닭꼬치×맥주) 탐색.

| # | 실험 | 베이스 | 포맷 | 의도 |
|---|---|---|---|---|
| 8 | meme_char_pizza_standup_talk | `pizza.png` | standup_talk | 피자가 반으로 접혀 일어나 치즈팔로 수다 — 평면 food 의인화 |
| 9 | meme_char_pizza_camera_bump | `pizza.png` | camera_bump (렌즈 묻기→닦이기) | 페퍼로니/치즈가 렌즈에 묻고 닦이는 POV 임팩트 연출 |
| 10 | meme_char_japan_chicken_standup_talk | `japan_beer_chicken.png` | standup_talk | 닭꼬치 하나가 꼬치째 서서 수다 — 꼬치 형태 의인화 |
| 11 | meme_char_japan_beer_feed_chicken | `japan_beer_chicken.png` | two_product_interaction | 맥주 캐릭터가 닭꼬치 집어 카메라에 먹여주기 (제품 간 상호작용) |
| 12 | meme_char_japan_two_beers_dance_chicken | `japan_beer_chicken.png` | multi_character + mirror_dance | 맥주 2잔이 동시 캐릭터화 → 각자 꼬치 들고 대칭 춤 |

**비교 포인트**:
- 8 vs 10: 서로 다른 food 형태(원형 피자 vs 꼬치) 의인화 난이도
- 9: 렌즈 smudge + wipe 라는 camera POV 특수 연출이 i2v 에서 얼마나 살아나는가
- 11 vs 12: 두 제품 상호작용 (비대칭 feed) vs 두 제품 동시 캐릭터화 (대칭 dance) — 멀티 캐릭터 제어 난이도

### 운영

- **모니터링**: `tail -f logs/batch_round8_*.log` 또는 Streamlit Gallery (`http://<HOST>:8501`) 에서 실시간 새 런 반영
- **VS Code 끊겨도**: nohup + disown, `outputs/index.jsonl` 자동 append, `sync_to_drive.py` 로 drive 백업
- **실패 시**: `scripts/resume_batch.sh` 로 남은 config 재개

---

## 스키마 정리 — v2 active taxonomy 재맵핑 (2026-04-20)

legacy v1 category/subcategory (drink_motion/ripple, camera_move/dolly_in, food_motion/steam 등) 로 저장되어 있던 **기존 35 index 엔트리 + 41 meta.json** 을 v2 활성 9개 템플릿으로 일괄 재맵핑.

- 스크립트: `scripts/normalize_taxonomy_v2active.py` (dry-run 지원, 원본은 `.pre_v2active.bak` 백업)
- 규칙: `docs/TEMPLATES.md` "기존 config → 6개 템플릿 맵핑" 표를 코드화
- 결과: index.jsonl 의 `template_category` 값이 `{motion, meme, archived}` 3개, `template_subcategory` 는 9개 활성 + archived subset 로 정리됨
- motion_template / meme_template 필드도 같이 채움 (null 이던 legacy 엔트리에 subcategory 기반 값 주입)

## 런타임/로깅 업그레이드 (2026-04-20)

- `run_batch.py` / `run_inference.py` 에 **load_sec / inference_sec / steps_per_sec** 측정 추가
- `meta.json → metrics.*` + `index.jsonl` 둘 다 flat 필드로 노출
- Streamlit Gallery 테이블에 `load_s / infer_s / steps/s` 컬럼 추가

## 스트림릿 사이드바 v2 정리 (2026-04-20)

- `category` 멀티셀렉트 옵션을 `[motion, meme, archived]` canonical 순서로 고정
- `subcategory` 는 선택된 category 따라 **CANONICAL_MOTION_SUBS (6)** / **CANONICAL_MEME_SUBS (3)** 로 정렬된 옵션 제공
- TEMPLATES.md v2 taxonomy와 1:1 매칭

---

## Batch 10 — Round 9: food→character + external guest + motion showcase (2026-04-20 KST 19:13 ~)

**사이즈**: 9 runs, meme_5s preset, seed 42, ~9시간 예상 (1런 ≈ 60분).
**Launch**: `scripts/launch_round9_overnight.sh` → `docker exec -d streamlit ... run_batch.py`
**Log**: `logs/batch_round9_20260420_101315.log`
**목적**: 댄스 제외. food 중심 의인화 + 외부 guest 캐릭터 + 모션 템플릿 showcase(정돈 데모).

### meme_ai_character × 3 (#1 — 제품 자체 캐릭터화)

| # | 실험 | 베이스 (자체 샘플) | 의도 |
|---|---|---|---|
| 1 | meme_char_pizza_fold_walk | pizza.png | 피자가 접혀 상체화 + 치즈 다리로 카메라 쪽 걷기 — 평면 food 의인화 이동 모션 |
| 2 | meme_char_japan_chicken_mic_karaoke | japan_beer_chicken.png | 닭꼬치가 꼬치를 마이크 삼아 노래 — "물건을 들고 퍼포먼스" 디테일 |
| 3 | meme_char_beer_cheers_duo | beer.png | 맥주병 1 → 2병으로 늘어나고 서로 건배 — 단일 제품 → 멀티 캐릭터 확장 |

### meme_ai_animal × 3 (#3 — 외부 캐릭터/동물 등장)

| # | 실험 | 베이스 (자체 샘플) | 외부 엔티티 | 의도 |
|---|---|---|---|---|
| 4 | meme_animal_bear_beer_peek | beer.png | 픽사풍 갈색 곰 | 배경에서 제품에 호기심 — 가장 순한 상호작용 |
| 5 | meme_animal_cat_pizza_steal | pizza.png | 오렌지 태비 새끼 고양이 | 피자 슬라이스로 앞발 뻗기 — "도둑질" 밈 포맷 |
| 6 | meme_animal_corgi_coffee_beg | coffee_man.png | 코기 강아지 | 테이블 옆에서 beg — 인물 동시 유지 난이도 검증 |

### motion showcase × 3 (템플릿 데모용 정돈 샘플)

| # | 실험 | 베이스 | motion_template | 의도 |
|---|---|---|---|---|
| 7 | pizza_steam_rise | pizza.png | steam_rise | 뜨거운 피자 김 — food steam 카테고리 pizza 샘플 0건이라 신규 |
| 8 | japan_beer_surface_shimmer | japan_beer_chicken.png | surface_shimmer | 차가운 맥주잔 결로수 타고 흐르기 — izakaya 씬 surface_shimmer |
| 9 | pizza_dolly_in | pizza.png | dolly_in | 피자 위 slow push-in hero shot — food dolly_in 0건이라 신규 |

**배치 결정 근거**:
- 댄스 실험은 Round 8-A (boat_dance × 7) 로 충분 커버, 사용자 지시로 이번엔 제외
- pizza 가 motion 템플릿 커버리지 구멍 (steam_rise / dolly_in 에 food 샘플 없었음)
- meme_ai_animal 외부 엔티티 다양성 확장 (곰/고양이/코기 — 크기·톤 다른 셋)

**레이턴시 측정**: 이 배치부터 wall_sec + load_sec + inference_sec + steps_per_sec 전부 기록 (Round 8 까진 wall_sec 만).

---

## Batch 10-Ext — Round 9 extension: motion showcase 확장 (2026-04-21 새벽 자동 이어받기)

**사이즈**: 4 runs, meme_5s preset, ~4시간. 아침 9시 KST 까지 여유 추가 배치.
**Launch 순서**: Round 9 본 배치 완료 대기 (`scripts/wait_and_launch_round9_ext.sh`) → 자동으로 `launch_round9_ext_overnight.sh` 호출.
**목적**: 6개 모션 프리미티브를 food(pizza, japan_beer_chicken, beer) subject 에 채우기 — 템플릿 데모용.

| # | 실험 | 베이스 (자체 샘플) | motion_template | 의도 |
|---|---|---|---|---|
| 1 | pizza_lift_to_camera | pizza.png | lift_to_camera | 슬라이스 들어올려 치즈 늘어남 + 카메라 쪽 이동 — pizza lift 샘플 최초 |
| 2 | pizza_orbit_pan | pizza.png | orbit_pan | 피자 주위 light orbit pan — pizza orbit 샘플 최초 |
| 3 | japan_consume_product | japan_beer_chicken.png | consume_product | 손이 들어와 닭꼬치 하나 집어 카메라 쪽 — izakaya consume 샘플 |
| 4 | beer_dolly_in | beer.png | dolly_in | 맥주병 hero push-in — beer subject 전용 dolly_in (legacy menu_hero 대체) |

**모션 커버리지 목표** (Round 9 본 + Ext 합쳐 food subject 매트릭스):
- pizza: steam_rise ✓ / dolly_in ✓ / lift_to_camera ✓ / orbit_pan ✓
- japan_beer_chicken: surface_shimmer ✓ / consume_product ✓
- beer: dolly_in ✓

6개 프리미티브 food 커버 확장 완료.

**결과 (2026-04-21 04:11 UTC = 13:11 KST, 완료)**: 13/13 ok, 0 err. 본 배치 ok=9 + 확장 ok=4.

| # | 실험 | category/sub | wall | load | infer | steps/s |
|---|---|---|---|---|---|---|
| 1 | meme_char_pizza_fold_walk | meme/meme_ai_character | 3379 | 183 | 3379 | 0.012 |
| 2 | meme_char_japan_chicken_mic_karaoke | meme/meme_ai_character | 3578 | 0 | 3578 | 0.011 |
| 3 | meme_char_beer_cheers_duo | meme/meme_ai_character | 3607 | 0 | 3606 | 0.011 |
| 4 | meme_animal_bear_beer_peek | meme/meme_ai_animal | 3592 | 0 | 3591 | 0.011 |
| 5 | meme_animal_cat_pizza_steal | meme/meme_ai_animal | 3555 | 0 | 3554 | 0.011 |
| 6 | meme_animal_corgi_coffee_beg | meme/meme_ai_animal | 3570 | 0 | 3570 | 0.011 |
| 7 | pizza_steam_rise | motion/steam_rise | 3581 | 0 | 3580 | 0.011 |
| 8 | japan_beer_surface_shimmer | motion/surface_shimmer | 3578 | 0 | 3578 | 0.011 |
| 9 | pizza_dolly_in | motion/dolly_in | 3580 | 0 | 3580 | 0.011 |
| 10 | pizza_lift_to_camera | motion/lift_to_camera | 3376 | 179 | 3375 | 0.012 |
| 11 | pizza_orbit_pan | motion/orbit_pan | 3551 | 0 | 3551 | 0.011 |
| 12 | japan_consume_product | motion/consume_product | 3596 | 0 | 3595 | 0.011 |
| 13 | beer_dolly_in | motion/dolly_in | 3607 | 0 | 3606 | 0.011 |

- 1런 평균 ≈ 3566s (59분 27초). VRAM 피크 18.25GB 안정 (L4 24GB 내).
- load_sec 기록 동작 확인: 본 배치 첫 런 183s, 확장 배치 첫 런 179s (이후 런은 0 — 모델 재사용 정상).
- 에러·OOM·간섭 없음. taxonomy v2 clean, 13/13 모두 {motion, meme} × {canonical subcategory} 로 저장.
