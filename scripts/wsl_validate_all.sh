#!/usr/bin/env bash
set -euo pipefail
ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== PYTEST ==="
python3 -m pytest -q tests
echo "PYTEST_EXIT=0"

echo "=== VALIDATE_DQN ==="
python3 scripts/validate_dqn.py
echo "VAL_EXIT=0"

echo "=== LOAD_DEFAULT ==="
python3 - <<'PY'
from fear_mecanumbot.policy import load_default_agent
from fear_mecanumbot.dqn import DQNAgent
a = load_default_agent()
assert isinstance(a, DQNAgent), type(a)
print("load_default_agent=DQNAgent OK")
PY

echo "=== RUN_HRI_RL ==="
python3 scripts/run_hri_rl.py

echo "ALL_OFFLINE_CHECKS_PASSED"
