#!/usr/bin/env bash
set -euo pipefail
export MUJOCO_GL=egl
export PATH="/usr/bin:/bin:/home/fahrad/.local/bin:${PATH:-}"
export PYTHONPATH="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot:/home/fahrad/.local/lib/python3.10/site-packages"
SCRIPT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/record_csenge_dqn_demo.py"
sed -i 's/\r$//' "$SCRIPT"
exec python3 "$SCRIPT"
