#!/usr/bin/env bash
set -euo pipefail
SRC_FILE="/mnt/c/Users/Fahrad/Desktop/AI Lab/mecanumbot_behaviours/mecanumbot_fear_hri_behaviour/mecanumbot_fear_hri_behaviour/behaviours/rl_policy.py"
echo "source has clear-gate: $(grep -c 'Person clearly clear' "$SRC_FILE" || true)"
find "$HOME/mecanumbot_ws/src" -name 'rl_policy.py' 2>/dev/null | while read -r dest; do
  echo "sync -> $dest"
  cp -f "$SRC_FILE" "$dest"
done
# Also common Desktop AI Lab path used as --base-paths
find "/mnt/c/Users/Fahrad/Desktop/AI Lab" -path '*mecanumbot_fear_hri_behaviour*behaviours/rl_policy.py' 2>/dev/null | while read -r dest; do
  if [[ "$dest" != "$SRC_FILE" ]]; then
    echo "sync -> $dest"
    cp -f "$SRC_FILE" "$dest"
  fi
done
echo DONE_SYNC
