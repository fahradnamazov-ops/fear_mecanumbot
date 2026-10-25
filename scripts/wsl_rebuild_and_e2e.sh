#!/usr/bin/env bash
set +u
source /opt/ros/humble/setup.bash
source /home/fahrad/mecanumbot_ws/install/setup.bash
set -u
cd /home/fahrad/mecanumbot_ws
colcon build --packages-select mecanumbot_fear_hri_behaviour --symlink-install
echo BUILD_EXIT=$?
python3 <<'PY'
import inspect
import mecanumbot_fear_hri_behaviour.behaviours.rl_policy as r
print("installed_file", r.__file__)
src = inspect.getsource(r.DqnPolicy.act)
print("has_clear_gate", "Person clearly clear" in src)
PY
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 2
cd "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
exec bash scripts/wsl_e2e_dqn.sh
