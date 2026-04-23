#!/bin/bash
# Wait for current Round 9 batch to finish ("[batch] done" in its log),
# then launch Round 9 extension (4 more motion showcase runs).
#
# Usage (host):
#   nohup bash scripts/wait_and_launch_round9_ext.sh > logs/wrapper_round9_ext.log 2>&1 &
#   disown
set -u

REPO_DIR="/home/youuchul/work/i2v-motion-experiments"
CURRENT_LOG="${CURRENT_LOG:-logs/batch_round9_20260420_101315.log}"
POLL_SECS="${POLL_SECS:-120}"
COOLDOWN_SECS="${COOLDOWN_SECS:-30}"

cd "$REPO_DIR"

echo "[wrapper] start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[wrapper] waiting for '[batch] done' in $CURRENT_LOG (poll ${POLL_SECS}s)"

until grep -q "\[batch\] done" "$CURRENT_LOG" 2>/dev/null; do
  sleep "$POLL_SECS"
done

echo "[wrapper] current batch finished at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[wrapper] cooldown ${COOLDOWN_SECS}s for GPU memory cleanup"
sleep "$COOLDOWN_SECS"

bash scripts/launch_round9_ext_overnight.sh
echo "[wrapper] exit $(date -u +%Y-%m-%dT%H:%M:%SZ)"
