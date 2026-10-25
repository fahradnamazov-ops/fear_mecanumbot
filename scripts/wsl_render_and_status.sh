#!/usr/bin/env bash
set -eo pipefail
set +u
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
set -u

python3 "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/render_mujoco_still.py"

echo "--- fear logs ---"
grep 'fear=' "${HOME}/mecanumbot_ws/log_fear_sim/fear_view.log" 2>/dev/null | tail -n 5 || true
echo "--- nodes ---"
ros2 node list 2>/dev/null || true
echo DONE
