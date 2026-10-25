#!/usr/bin/env bash
# Train Double DQN on local disk (faster than /mnt/c), then copy weights back.
set -euo pipefail
SRC="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
WORK="${HOME}/fear_dqn_train"
rm -rf "$WORK"
mkdir -p "$WORK"
cp -a "$SRC/fear_mecanumbot" "$WORK/"
cp -a "$SRC/scripts" "$WORK/"
mkdir -p "$WORK/models"
cp -f "$SRC/models/hri_q.npy" "$WORK/models/" 2>/dev/null || true
cd "$WORK"
export PYTHONPATH="$WORK${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/train_hri_dqn.py
cp -f models/hri_dqn.npz models/hri_dqn_eval.json "$SRC/models/"
echo "copied weights to $SRC/models"
cat models/hri_dqn_eval.json
