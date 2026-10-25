#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/bin:/bin:/home/fahrad/.local/bin:${PATH:-}"
echo "=== ws src ==="
ls -la /home/fahrad/mecanumbot_ws/src 2>/dev/null || echo "no src"
echo "=== find rl_policy ==="
find /home/fahrad/mecanumbot_ws -name 'rl_policy.py' 2>/dev/null || true
find /mnt/c/Users/Fahrad/Desktop/AI\ Lab -name 'rl_policy.py' 2>/dev/null | head
source /opt/ros/humble/setup.bash
source /home/fahrad/mecanumbot_ws/install/setup.bash
python3 <<'PY'
import inspect
import mecanumbot_fear_hri_behaviour.behaviours.rl_policy as r
print("installed_file", r.__file__)
src = inspect.getsource(r.DqnPolicy.act)
print("has_clear_gate", "Person clearly clear" in src)
print("has_avoid_mask", "q[1] = -1e9" in src)
PY
