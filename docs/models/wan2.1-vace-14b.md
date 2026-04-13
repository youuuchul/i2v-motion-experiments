# Wan2.1-VACE-14B

통합 비디오 생성 모델 (T2V / I2V / R2V / V2V / MV2V). 본 프로젝트 1차 실험 모델.

## 스펙
- **라이선스:** Apache 2.0
- **네이티브 해상도:** 480P (832×480), 720P (1280×720) — **16:9 가로 중심**
- **네이티브 fps / 길이:** 16 fps, 기본 81 frames ≈ 5.06s
- **Checkpoint:** `Wan-AI/Wan2.1-VACE-14B-diffusers`

## 프로젝트 타깃과의 갭
| 항목 | 프로젝트 타깃 | VACE 네이티브 | 대응 |
|---|---|---|---|
| 종횡비 | 9:16 (576×1024) | 16:9 | 비네이티브 — 품질 실험적, 프롬프트/소스 이미지 비율 중요 |
| fps | 24 | 16 | `spec.fps` 저장 시 리샘플 (현 어댑터는 num_frames 기준으로만 생성) |
| 길이 | 5s | 5.06s | 거의 일치 |

## L4 24GB 운용
- `dtype=float16`
- `enable_model_cpu_offload=True`
- `enable_vae_slicing=True`
- 720P는 비권장. 480P·9:16 근사 해상도로 진행.
- OOM 시: quantization (bnb 8bit/4bit) 또는 `sequential_cpu_offload` 검토.

## 대안
I2V만 필요하면 `Wan-AI/Wan2.1-I2V-14B-480P`가 더 직접적. VACE 선택 이유는 레퍼런스/에디팅까지 포괄하는 확장성.
