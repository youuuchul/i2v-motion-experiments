#!/bin/bash
# Round 9 extension — 4 motion showcase runs to cover pizza/japan/beer remaining primitives.
# 아침 9시까지 여유 추가 배치 (약 4시간).
set -u

CONTAINER_NAME="${CONTAINER_NAME:-streamlit}"
REPO_DIR="/home/youuchul/work/i2v-motion-experiments"
cd "$REPO_DIR"

TS=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/batch_round9_ext_${TS}.log"

CONFIGS=(
  configs/experiments/wan_vace_pizza_lift_to_camera.yaml
  configs/experiments/wan_vace_pizza_orbit_pan.yaml
  configs/experiments/wan_vace_japan_consume_product.yaml
  configs/experiments/wan_vace_beer_dolly_in.yaml
)

for cfg in "${CONFIGS[@]}"; do
  if [ ! -f "$REPO_DIR/$cfg" ]; then
    echo "[launch] ERROR: missing $cfg" >&2
    exit 2
  fi
done

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q true; then
  echo "[launch] ERROR: container $CONTAINER_NAME is not running" >&2
  exit 1
fi

echo "[launch] $(date -u +%Y-%m-%dT%H:%M:%SZ) launching Round 9 extension (4 runs) → $LOG_FILE"

docker exec -d "$CONTAINER_NAME" bash -lc "cd /workspace && python scripts/run_batch.py \
  --configs \
    ${CONFIGS[0]} \
    ${CONFIGS[1]} \
    ${CONFIGS[2]} \
    ${CONFIGS[3]} \
  --sync-after-each --sync-after-batch \
  > $LOG_FILE 2>&1"

echo "[launch] docker exec -d returned $?"
