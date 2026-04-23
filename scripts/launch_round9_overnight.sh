#!/bin/bash
# Round 9 overnight batch (9 runs × ~60min ≈ 9h):
#   3 × meme_ai_character (food → character)
#   3 × meme_ai_animal    (external guest / animal)
#   3 × motion showcase   (steam_rise, surface_shimmer, dolly_in)
#
# Launch inside existing docker container `streamlit` (has GPU + bind of repo).
# Usage (host):
#   bash scripts/launch_round9_overnight.sh
set -u

CONTAINER_NAME="${CONTAINER_NAME:-streamlit}"
REPO_DIR="/home/youuchul/work/i2v-motion-experiments"
cd "$REPO_DIR"

TS=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/batch_round9_${TS}.log"

CONFIGS=(
  configs/experiments/wan_vace_meme_char_pizza_fold_walk.yaml
  configs/experiments/wan_vace_meme_char_japan_chicken_mic_karaoke.yaml
  configs/experiments/wan_vace_meme_char_beer_cheers_duo.yaml
  configs/experiments/wan_vace_meme_animal_bear_beer_peek.yaml
  configs/experiments/wan_vace_meme_animal_cat_pizza_steal.yaml
  configs/experiments/wan_vace_meme_animal_corgi_coffee_beg.yaml
  configs/experiments/wan_vace_pizza_steam_rise.yaml
  configs/experiments/wan_vace_japan_beer_surface_shimmer.yaml
  configs/experiments/wan_vace_pizza_dolly_in.yaml
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

echo "[launch] $(date -u +%Y-%m-%dT%H:%M:%SZ) launching Round 9 (9 runs) → $LOG_FILE"

docker exec -d "$CONTAINER_NAME" bash -lc "cd /workspace && python scripts/run_batch.py \
  --configs \
    ${CONFIGS[0]} \
    ${CONFIGS[1]} \
    ${CONFIGS[2]} \
    ${CONFIGS[3]} \
    ${CONFIGS[4]} \
    ${CONFIGS[5]} \
    ${CONFIGS[6]} \
    ${CONFIGS[7]} \
    ${CONFIGS[8]} \
  --sync-after-each --sync-after-batch \
  > $LOG_FILE 2>&1"

echo "[launch] docker exec -d returned $?"
echo "[launch] tail the log: tail -f $LOG_FILE"
