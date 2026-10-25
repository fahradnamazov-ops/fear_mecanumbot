#!/usr/bin/env bash
set +e
source /opt/ros/humble/setup.bash
cd "${HOME}/mecanumbot_ws"
colcon build --packages-select mecanumbot_sim mecanumbot_fear_hri_behaviour --symlink-install
source "${HOME}/mecanumbot_ws/install/setup.bash"
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw

kill $(pgrep -f mecanumbot_sim_mujoco_io_node) 2>/dev/null
kill $(pgrep -f fear_hri_bt_node) 2>/dev/null
sleep 2

echo "============================================"
echo " Fear HRI + brick carry (Csenge MuJoCo)"
echo " Watch: MuJoCo : mecanumbot"
echo "============================================"

ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco mode:=truth_twin scenario:=fear_hri_brick_carry \
  show_viewer:=true use_rviz:=false &
SIM_PID=$!

for i in $(seq 1 60); do
  if ros2 topic list 2>/dev/null | grep -q '/mecanumbot/scan'; then
    echo "scan ready ($i)"; break
  fi
  sleep 1
done

ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py &
echo "sim=$SIM_PID — robot will pick bricks when fear is low (task)"
wait
