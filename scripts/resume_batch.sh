#!/usr/bin/env bash
# 미완료 실험만 골라서 재실행 + Drive sync.
#
# 동작:
# 1) configs/experiments/ 아래 baseline/v2/lighting 태그 후보 목록을 조회
# 2) outputs/index.jsonl 에서 status=ok 인 experiment 이름 set 추출
# 3) 둘의 차집합 = 아직 안 끝난 것 → run_batch 에 넘김
# 4) --sync-after-each 로 매 런 끝날 때마다 즉시 Drive 업로드 (중간에 또 끊겨도 보존)
#
# Usage:
#   bash scripts/resume_batch.sh                # 실행
#   bash scripts/resume_batch.sh --dry          # 목록만 확인

set -euo pipefail

DRY=0
[[ "${1:-}" == "--dry" ]] && DRY=1

REPO=/home/youuchul/work/i2v-motion-experiments
cd "$REPO"

# 후보 목록 (Phase 0 baseline + lighting). 새 카테고리 추가 시 여기 한 줄 추가.
CANDIDATES=(
  # baseline (1차 7개)
  wan_vace_beer_drink_ripple
  wan_vace_beer_food_steam
  wan_vace_coffee_man_dolly_pan
  wan_vace_coffee_man_offer_drink
  wan_vace_sample_drink_ripple
  wan_vace_sample_focus_shift
  wan_vace_sample_offer_drink
  # 카테고리 확장 (2차 5개)
  wan_vace_sample_gesture_point
  wan_vace_coffee_man_dolly_in
  wan_vace_beer_food_glaze
  wan_vace_beer_menu_hero
  wan_vace_sample_ambiance_bokeh
  # 조명 (3차 3개)
  wan_vace_coffee_man_rim_light
  wan_vace_sample_golden_hour
  wan_vace_coffee_man_silhouette
  # 탑뷰/일상사진 (4차 3개 - 난이도 높은 케이스)
  wan_vace_beer_man_topview_steam
  wan_vace_beer_man_topview_lift
  wan_vace_beer_man_topview_face_reveal
)

# index.jsonl 에서 완료된 experiment 추출
DONE_FILE=$(mktemp)
trap "rm -f $DONE_FILE" EXIT
if [ -f outputs/index.jsonl ]; then
  python3 - <<'PY' >"$DONE_FILE"
import json, pathlib
done = set()
for line in pathlib.Path("outputs/index.jsonl").read_text().splitlines():
    if not line.strip(): continue
    try:
        e = json.loads(line)
    except json.JSONDecodeError:
        continue
    # legacy 든 v2 든 status=ok 면 "비디오 있음"으로 간주 → skip
    if e.get("status") == "ok":
        name = e.get("experiment")
        if name: done.add(name)
for n in sorted(done):
    print(n)
PY
fi

# 차집합 → 실행 대상
TODO=()
for exp in "${CANDIDATES[@]}"; do
  if ! grep -qx "$exp" "$DONE_FILE"; then
    cfg="configs/experiments/${exp}.yaml"
    if [ -f "$cfg" ]; then
      TODO+=("$cfg")
    fi
  fi
done

echo "[resume] done (v2, status=ok): $(wc -l < $DONE_FILE) experiments"
echo "[resume] todo: ${#TODO[@]} experiments"
for c in "${TODO[@]}"; do echo "  - $c"; done

if [ ${#TODO[@]} -eq 0 ]; then
  echo "[resume] nothing to do."
  exit 0
fi

if [ "$DRY" -eq 1 ]; then
  echo "[resume] dry-run done. remove --dry to execute."
  exit 0
fi

# detached 컨테이너로 실행
sudo docker rm -f batch 2>/dev/null || true
sudo docker run -d --name batch --gpus all \
  -v "$REPO":/workspace \
  -v docker_hf_cache:/cache/huggingface -v docker_torch_cache:/cache/torch \
  -w /workspace --user "$(id -u):$(id -g)" \
  --env-file "$REPO/.env" \
  -e HF_HOME=/cache/huggingface -e TRANSFORMERS_CACHE=/cache/huggingface \
  -e TORCH_HOME=/cache/torch -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e HF_HUB_DISABLE_XET=1 \
  -e HOME=/tmp -e TRITON_CACHE_DIR=/tmp/.triton -e XDG_CACHE_HOME=/tmp/.cache \
  -e PYTHONPATH=src \
  i2v-motion:dev \
  bash -lc "python scripts/run_batch.py --configs ${TODO[*]} --sync-after-each --sync-after-batch 2>&1 | tee logs/batch_resume_\$(date +%Y%m%d_%H%M%S).log"

echo "[resume] launched detached container 'batch'. monitor with: sudo docker logs -f batch"
