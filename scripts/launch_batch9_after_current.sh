#!/bin/bash
# Wait for the currently-running run_batch.py (PID $PID_TO_WAIT) to finish,
# then launch Batch 9 (Round 8: boat_dance × 7 + meme_ai_character × 5 = 12 runs)
# inside the existing docker container `streamlit`.
#
# Launch in nohup so VS Code / SSH disconnects don't kill the waiter:
#   cd /home/youuchul/work/i2v-motion-experiments
#   nohup bash scripts/launch_batch9_after_current.sh > logs/wrapper_batch9.log 2>&1 &
#   disown

set -u

PID_TO_WAIT="${PID_TO_WAIT:-476092}"
POLL_SECS="${POLL_SECS:-60}"
COOLDOWN_SECS="${COOLDOWN_SECS:-30}"
CONTAINER_NAME="${CONTAINER_NAME:-streamlit}"
REPO_DIR="/home/youuchul/work/i2v-motion-experiments"

cd "$REPO_DIR"

echo "[wrapper] start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[wrapper] waiting for PID $PID_TO_WAIT to exit (poll ${POLL_SECS}s)"

# Poll host-side PID. If PID doesn't exist at start (already finished), skip wait.
if kill -0 "$PID_TO_WAIT" 2>/dev/null; then
  while kill -0 "$PID_TO_WAIT" 2>/dev/null; do
    sleep "$POLL_SECS"
  done
else
  echo "[wrapper] PID $PID_TO_WAIT already gone — launching immediately"
fi

echo "[wrapper] PID $PID_TO_WAIT exited at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[wrapper] cooldown ${COOLDOWN_SECS}s for GPU memory cleanup"
sleep "$COOLDOWN_SECS"

TS=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/batch_round8_${TS}.log"

# Verify container is up
if ! docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q true; then
  echo "[wrapper] ERROR: container $CONTAINER_NAME is not running. aborting."
  exit 1
fi

# Verify all configs exist inside the container view (/workspace is bind of $REPO_DIR)
CONFIGS=(
  configs/experiments/wan_vace_meme_dance_boat_ref_frame.yaml
  configs/experiments/wan_vace_meme_dance_boat_boat_kid_a.yaml
  configs/experiments/wan_vace_meme_dance_boat_boat_kid_b.yaml
  configs/experiments/wan_vace_meme_dance_boat_coffee_man_a.yaml
  configs/experiments/wan_vace_meme_dance_boat_coffee_man_b.yaml
  configs/experiments/wan_vace_meme_dance_boat_man_object_a.yaml
  configs/experiments/wan_vace_meme_dance_boat_man_object_b.yaml
  configs/experiments/wan_vace_meme_char_pizza_standup_talk.yaml
  configs/experiments/wan_vace_meme_char_pizza_camera_bump.yaml
  configs/experiments/wan_vace_meme_char_japan_chicken_standup_talk.yaml
  configs/experiments/wan_vace_meme_char_japan_beer_feed_chicken.yaml
  configs/experiments/wan_vace_meme_char_japan_two_beers_dance_chicken.yaml
)
for cfg in "${CONFIGS[@]}"; do
  if [ ! -f "$REPO_DIR/$cfg" ]; then
    echo "[wrapper] ERROR: missing $cfg — aborting"
    exit 2
  fi
done

echo "[wrapper] launching batch at $(date -u +%Y-%m-%dT%H:%M:%SZ), log=$LOG_FILE"

# Use docker exec -d to detach: new python runs in container, survives this script exit
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
    ${CONFIGS[9]} \
    ${CONFIGS[10]} \
    ${CONFIGS[11]} \
  --sync-after-each --sync-after-batch \
  > $LOG_FILE 2>&1"

echo "[wrapper] docker exec -d returned $?. exit $(date -u +%Y-%m-%dT%H:%M:%SZ)"
