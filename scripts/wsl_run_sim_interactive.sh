#!/usr/bin/env bash
# Interactive MuJoCo Fear simulation — keep this terminal open.
set -eo pipefail
set +u
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
set -u

pkill -f mecanumbot_sim_mujoco_io_node 2>/dev/null || true
pkill -f fear_hri_bt_node 2>/dev/null || true
sleep 1

echo "============================================"
echo " MuJoCo Fear HRI simulation"
echo " A 3D viewer window should open on Windows."
echo " Leave this terminal running."
echo "============================================"

ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco \
  mode:=truth_twin \
  scenario:=fear_hri_brick_carry \
  show_viewer:=true \
  use_rviz:=false &
SIM_PID=$!

for i in $(seq 1 45); do
  if ros2 topic list 2>/dev/null | grep -q '/mecanumbot/scan'; then
    break
  fi
  sleep 1
done

ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py &
FEAR_PID=$!

echo "sim=$SIM_PID fear=$FEAR_PID"
echo "Watch the MuJoCo window. Ctrl+C stops."
wait
