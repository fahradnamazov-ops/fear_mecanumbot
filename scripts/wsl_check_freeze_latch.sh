#!/usr/bin/env bash
# Acceptance checks: freeze-on-catch, no false freeze when clear, no fear throttle.
set -euo pipefail
export PATH="/usr/bin:/bin:/home/fahrad/.local/bin:${PATH:-}"
BEH="/mnt/c/Users/Fahrad/Desktop/AI Lab/mecanumbot_behaviours/mecanumbot_fear_hri_behaviour"
ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
export PYTHONPATH="${BEH}:${ROOT}:${HOME}/.local/lib/python3.10/site-packages"
# ROS msgs only needed if we import brick_carry; prefer source scan instead.
set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash 2>/dev/null || true
set -u

python3 <<'PY'
import importlib
from pathlib import Path
from mecanumbot_fear_hri_behaviour.behaviours import rl_policy

importlib.reload(rl_policy)
rl_policy._POLICY = None
rl_policy._LOAD_TRIED = False
pol = rl_policy.get_policy()
assert pol is not None, "DQN weights missing"

# 1) Hard freeze when person caught
feat = rl_policy.features_live(
    fear_level=10.0, min_range=0.45, has_brick=True, target_dist_m=1.0,
    person_dx=0.4, person_dy=0.0, risk=0.5,
    cost_middle=0.2, cost_north=0.5, cost_south=0.8,
)
act = pol.act(feat, catch_attention_enabled=False)
assert act == "freeze", act
print("PASS freeze_at_0.45m ->", act)

# 2) Clear + residual fear → still task (never freeze stall at ~1.2 m)
feat2 = rl_policy.features_live(
    fear_level=0.0, min_range=1.19, has_brick=True, target_dist_m=1.0,
    person_dx=1.0, person_dy=0.0, risk=0.0,
    cost_middle=0.0, cost_north=0.8, cost_south=1.0,
)
act2 = pol.act(feat2, catch_attention_enabled=False)
assert act2.startswith("task"), "false freeze at 1.19m fear=0: %s" % act2
print("PASS clear_1.19m_fear0 ->", act2)

feat2b = rl_policy.features_live(
    fear_level=41.0, min_range=1.16, has_brick=True, target_dist_m=1.0,
    person_dx=1.0, person_dy=0.0, risk=0.0,
    cost_middle=0.2, cost_north=0.5, cost_south=0.8,
)
act2b = pol.act(feat2b, catch_attention_enabled=False)
assert act2b != "freeze", "residual fear must not freeze at 1.16m: %s" % act2b
print("PASS clear_1.16m_fear41 ->", act2b)

feat3 = rl_policy.features_live(
    fear_level=5.0, min_range=1.5, has_brick=True, target_dist_m=1.0,
    person_dx=1.0, person_dy=0.0, risk=0.0,
    cost_middle=0.0, cost_north=0.8, cost_south=1.0,
)
act3 = pol.act(feat3, catch_attention_enabled=False)
assert act3.startswith("task"), act3
print("PASS clear_far ->", act3)

# 3) Close band still biases freeze/avoid when afraid
feat4 = rl_policy.features_live(
    fear_level=40.0, min_range=0.70, has_brick=True, target_dist_m=1.0,
    person_dx=0.5, person_dy=0.0, risk=0.4,
    cost_middle=0.3, cost_north=0.5, cost_south=0.6,
)
act4 = pol.act(feat4, catch_attention_enabled=False)
assert act4 in ("freeze", "avoid"), "expected freeze/avoid near person, got %s" % act4
print("PASS close_0.70m_fear40 ->", act4)

# 4) Task speed path must not multiply by fear_level (read source; no ROS import)
bc = Path(
    "/mnt/c/Users/Fahrad/Desktop/AI Lab/mecanumbot_behaviours/"
    "mecanumbot_fear_hri_behaviour/mecanumbot_fear_hri_behaviour/behaviours/brick_carry.py"
).read_text(encoding="utf-8")
# Extract _task_speed and _drive_toward bodies roughly
assert "def _task_speed" in bc and "def _drive_toward" in bc
task_speed = bc.split("def _task_speed", 1)[1].split("def _drive_routed", 1)[0]
drive = bc.split("def _drive_toward", 1)[1].split("def _task_target_xy", 1)[0]
assert "fear_level" not in task_speed, "fear throttle leaked into _task_speed"
assert "fear_level" not in drive, "fear throttle leaked into _drive_toward"
assert "Fear does NOT slow" in drive
print("PASS no_fear_throttle in task speed paths")

# 5) Freeze latch constant present
assert rl_policy.FREEZE_CATCH_M <= 0.55 + 1e-9
print("PASS FREEZE_CATCH_M=%.2f" % rl_policy.FREEZE_CATCH_M)
print("PASS freeze+no_fear_throttle checks")
PY
