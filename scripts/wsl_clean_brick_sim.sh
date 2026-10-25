#!/usr/bin/env bash
# Csenge-aligned Fear HRI live launch:
#   - mecanumbot_remote MuJoCo (fear_hri_brick_carry)
#   - truth_twin oracle subject + mecanumbot_sim_nav_shim (Nav2 Approach)
#   - Fear BT with Double DQN + brick-carry task
set +e
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw

echo "Stopping old sim processes..."
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 1

colcon build --packages-select mecanumbot_fear_hri_behaviour mecanumbot_sim --symlink-install --base-paths "${HOME}/mecanumbot_ws/src" 2>/dev/null
cd "${HOME}/mecanumbot_ws" && colcon build --packages-select mecanumbot_fear_hri_behaviour mecanumbot_sim --symlink-install
source "${HOME}/mecanumbot_ws/install/setup.bash"

export FEAR_DQN_MODEL="${FEAR_DQN_MODEL:-/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz}"
# Back-compat alias (ignored if .npz not present; live loader prefers FEAR_DQN_MODEL)
export FEAR_Q_MODEL="${FEAR_Q_MODEL:-$FEAR_DQN_MODEL}"
export PYTHONPATH="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot:${PYTHONPATH:-}"
# Csenge: catch_attention is IRL-only (sim subject cannot react)
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
# Force MuJoCo free-camera arena overview every frame (reviewable capture).
export FEAR_VIEWER_OVERVIEW=1
# Set FEAR_TEST_THAW=1 for a forced freeze→thaw demo on launch
export FEAR_TEST_THAW="${FEAR_TEST_THAW:-0}"

if [[ ! -f "$FEAR_DQN_MODEL" ]]; then
  echo "ERROR: Double DQN weights missing: $FEAR_DQN_MODEL"
  echo "Train first: bash fear_mecanumbot/scripts/wsl_train_dqn_fast.sh"
  exit 1
fi

echo "============================================"
echo " Fear HRI (Csenge stack + Double DQN)"
echo "  MuJoCo fear_hri_brick_carry + nav_shim"
echo "  DQN-model: ${FEAR_DQN_MODEL}"
echo "============================================"
ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco mode:=truth_twin scenario:=fear_hri_brick_carry \
  show_viewer:=true use_rviz:=false &
SIM_PID=$!
for i in $(seq 1 45); do
  ros2 topic list 2>/dev/null | grep -q '/sim/robot_pose' && echo "robot_pose ready" && break
  sleep 1
done

# Csenge Nav2 Approach path in sim (without Doglike leading BT fighting cmd_vel)
ros2 run mecanumbot_sim mecanumbot_sim_nav_shim_node --ros-args \
  -p use_sim_time:=true \
  -p odom_topic:=/mecanumbot/odom \
  -p goal_topic:=/goal_pose \
  -p cmd_vel_topic:=/cmd_vel \
  -p amcl_pose_topic:=/amcl_pose \
  -p navigate_to_pose_action:=navigate_to_pose \
  -p navigate_through_poses_action:=navigate_through_poses &
SHIM_PID=$!
sleep 2

ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py &
echo "sim=$SIM_PID nav_shim=$SHIM_PID"
wait
