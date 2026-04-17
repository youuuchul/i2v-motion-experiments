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
| (대기) | pig_streetfood_t2v | **t2v** | `sample.png` (placeholder) | — | 5s | — | **텍스트만** 돼지 포차 |
| (대기) | guest_pixar_mascot_beer | i2v | `beer.png` (자체) | — | 5s | — | 외부 픽사 마스코트가 씬에 등장 (외부 character 변형, #3 범위 확장 검증) |
| (대기) | guest_chibi_coffee | i2v | `coffee_man.png` (자체) | — | 5s | — | 외부 치비 애니메 캐릭터 등장 |

### meme_dance_ref (#2 — 댄스) × 5

| (대기) | 실험 | mode | 원본 이미지 | 레퍼런스 소스 | dur | 의도 |
|---|---|---|---|---|---|---|
| — | dance_ref_frame0 | i2v | `dance_ref/frame_0.jpg` ⚠️ | [YT short](https://www.youtube.com/shorts/0qKKrIXT1Lo) | 5s | ⚠️ 레퍼런스 프레임 직접 사용 — 비교 기준용. 자체 샘플 아님 |
| — | dance_ref_frame50 | i2v | `dance_ref/frame_50.jpg` ⚠️ | 동일 | 5s | ⚠️ 중간 프레임 이어가기 비교 |
| — | dance_t2v_freestyle | t2v | `sample.png` (placeholder) | 동일 | 5s | **텍스트만** 댄스 묘사 생성 |
| — | dance_coffee_man_subtle | i2v | `coffee_man.png` (자체 ✓) | 동일 | 5s | 자체 샘플 + 서틀 그루브 프롬프트 |
| — | dance_man_object_subtle | i2v | `man_object.png` (자체 ✓) | 동일 | 5s | 자체 샘플 + 스피커 리듬 |

**VRAM 관측**: 5초 = 17.14GB (3초 14.96GB 대비 +2.2GB). L4 24GB 내 안전.
**런타임**: 5초 = ~60분/런 (3초 ~33분 대비 1.8×).

---

## 다음 배치 (준비 완료, 미실행)

### 댄스 밈 v2 — 자체 샘플만 사용 × 6

| config | input_type | 스타일 |
|---|---|---|
| dance_coffee_man_boom | coffee_man.png ✓ | 하이에너지 붐샤카라카 |
| dance_man_object_boom | man_object.png ✓ | 하이에너지 스피커 프롭 |
| dance_man_box_boom | man_box.JPG ✓ | 하이에너지 박스 들고 |
| dance_coffee_man_groove | coffee_man.png ✓ | 서틀 상체 그루브 |
| dance_man_object_groove | man_object.png ✓ | 서틀 스피커 리듬 |
| dance_ref_frame0_test | frame_0.jpg (ref) ⚠️ | PoC 비교용 1회 |

**규칙**: 댄스 밈 i2v base = **자체 샘플만**. 레퍼런스 영상 프레임 직접 사용 금지 (비교 테스트 제외).
