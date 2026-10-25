#!/usr/bin/env bash
set -eo pipefail
set +u
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
set -u
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"

# Headless-friendly MuJoCo unless a display is present
if [ -n "${DISPLAY:-}" ] && [ "${DISPLAY}" != "" ]; then
  export MUJOCO_GL=glfw
  SHOW_VIEWER=true
else
  export MUJOCO_GL=egl
  SHOW_VIEWER=false
fi

LOGDIR="${HOME}/mecanumbot_ws/log_fear_sim"
mkdir -p "$LOGDIR"
pkill -f mecanumbot_sim_mujoco_io_node 2>/dev/null || true
pkill -f fear_hri_bt_node 2>/dev/null || true
pkill -f mecanumbot_sensorproc_node 2>/dev/null || true
sleep 1

echo "MUJOCO_GL=$MUJOCO_GL SHOW_VIEWER=$SHOW_VIEWER DISPLAY=${DISPLAY:-none}"
echo ">>> Launching MuJoCo truth_twin + fear_hri_brick_carry"
ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco \
  mode:=truth_twin \
  scenario:=fear_hri_brick_carry \
  show_viewer:=${SHOW_VIEWER} \
  use_rviz:=false \
  >"${LOGDIR}/sim.log" 2>&1 &
SIM_PID=$!
echo "sim launcher pid=$SIM_PID"

echo ">>> Waiting for /mecanumbot/scan ..."
for i in $(seq 1 40); do
  if ros2 topic list 2>/dev/null | grep -q '/mecanumbot/scan\|/scan'; then
    echo "topics up at try $i"
    break
  fi
  sleep 1
done

echo ">>> Launching Fear HRI tree"
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py \
  >"${LOGDIR}/fear.log" 2>&1 &
FEAR_PID=$!
echo "fear launcher pid=$FEAR_PID"

echo ">>> Collecting 30s of runtime..."
sleep 30

echo "===== topic list (mecanumbot/sim) ====="
ros2 topic list 2>/dev/null | grep -E 'scan|fear|sim|cmd_vel|mecanumbot' || ros2 topic list | head -50

echo "===== sim.log (tail) ====="
tail -n 50 "${LOGDIR}/sim.log" || true
echo "===== fear.log (grep fear=) ====="
grep -E 'fear=|Fear|error|Error|Traceback' "${LOGDIR}/fear.log" | tail -n 40 || true
echo "===== fear.log (tail) ====="
tail -n 30 "${LOGDIR}/fear.log" || true

echo "PIDs sim=$SIM_PID fear=$FEAR_PID"
echo ">>> DONE_LAUNCH"
