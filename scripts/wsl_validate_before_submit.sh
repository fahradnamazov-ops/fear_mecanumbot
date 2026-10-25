#!/usr/bin/env bash
# Full pre-submission validation. Exit 0 only if everything passes.
set -u
export PATH="/usr/bin:/bin:/home/fahrad/.local/bin:${PATH:-}"
ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
BEH="/mnt/c/Users/Fahrad/Desktop/AI Lab/mecanumbot_behaviours/mecanumbot_fear_hri_behaviour"
export PYTHONPATH="${ROOT}:${BEH}:${HOME}/.local/lib/python3.10/site-packages"
cd "$ROOT"

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

echo "======== 1) PYTEST ========"
if python3 -m pytest -q --tb=line; then
  pass "pytest"
else
  fail "pytest"
fi

echo "======== 2) ROUTE COST ========"
if python3 scripts/validate_route_cost.py; then
  pass "validate_route_cost"
else
  fail "validate_route_cost"
fi

echo "======== 3) DOUBLE DQN ========"
if python3 scripts/validate_dqn.py; then
  pass "validate_dqn"
else
  fail "validate_dqn"
fi

echo "======== 4) WEIGHTS FILE ========"
if [[ -f models/hri_dqn.npz ]]; then
  python3 - <<'PY'
from pathlib import Path
from fear_mecanumbot.dqn import DQNAgent
p = Path("models/hri_dqn.npz")
a = DQNAgent.load(p)
print("weights_ok", p.resolve(), "bytes", p.stat().st_size)
print("policy", type(a).__name__)
PY
  pass "weights load"
else
  fail "weights missing"
fi

echo "======== 5) V1 FINAL DEMO ========"
if python3 scripts/v1_final_demo.py > /tmp/fear_v1_final_demo.log 2>&1; then
  tail -n 25 /tmp/fear_v1_final_demo.log
  pass "v1_final_demo"
else
  tail -n 40 /tmp/fear_v1_final_demo.log
  fail "v1_final_demo"
fi

echo "======== 6) PROFESSOR DEMO VIDEO (regenerate + check 4/4) ========"
sed -i 's/\r$//' scripts/record_professor_demo.py
if python3 scripts/record_professor_demo.py > /tmp/fear_prof_demo.log 2>&1; then
  tail -n 15 /tmp/fear_prof_demo.log
  if grep -q "DONE delivered= 4" /tmp/fear_prof_demo.log; then
    pass "professor demo 4/4"
  else
    fail "professor demo not 4/4"
  fi
else
  tail -n 40 /tmp/fear_prof_demo.log
  fail "professor demo script"
fi

echo "======== 7) LIVE IMPORT (completion_cost + rl_policy) ========"
python3 - <<'PY'
from mecanumbot_fear_hri_behaviour.behaviours.completion_cost import (
    all_route_costs, cheapest_route, normalized_cost_features,
)
from mecanumbot_fear_hri_behaviour.behaviours import rl_policy
robot, target, person = (-1.35, -0.2), (1.35, -0.2), (0.0, -0.2)
c = all_route_costs(robot, target, person)
assert cheapest_route(robot, target, person) != "middle"
assert c["middle"][0] > c["north"][0]
n = normalized_cost_features(robot, target, person)
assert len(n) == 3
print("live_completion_cost_ok", {k: round(v[0], 2) for k, v in c.items()})
# policy load
p = rl_policy.get_policy()
print("live_policy", rl_policy.policy_kind(), "loaded", p is not None)
assert p is not None
act = rl_policy.select_action_rl(
    fear_level=0.0, min_range=1.5, has_brick=True, target_dist_m=2.0,
    person_dx=1.0, person_dy=0.0, risk=0.0,
    cost_middle=1.0, cost_north=0.0, cost_south=0.5,
    catch_attention_enabled=False,
)
print("live_select_action", act)
assert act is not None
print("LIVE_IMPORT_OK")
PY
if [[ $? -eq 0 ]]; then
  pass "live package imports"
else
  fail "live package imports"
fi

echo "======== 8) FREEZE LATCH + NO FEAR THROTTLE ========"
sed -i 's/\r$//' scripts/wsl_check_freeze_latch.sh
if bash scripts/wsl_check_freeze_latch.sh; then
  pass "freeze latch + no fear throttle"
else
  fail "freeze latch + no fear throttle"
fi

echo "======== SUMMARY ========"
if [[ "$FAIL" -eq 0 ]]; then
  echo "ALL_OFFLINE_AND_DEMO_CHECKS_PASSED"
  exit 0
fi
echo "SOME_CHECKS_FAILED"
exit 1
