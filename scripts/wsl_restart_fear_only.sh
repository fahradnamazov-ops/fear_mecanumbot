#!/usr/bin/env bash
set +e
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
export DISPLAY="${DISPLAY:-:0}"
export FEAR_DQN_MODEL="${FEAR_DQN_MODEL:-/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz}"
export FEAR_Q_MODEL="${FEAR_Q_MODEL:-$FEAR_DQN_MODEL}"
export PYTHONPATH="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot:${PYTHONPATH:-}"
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
# Only kill fear BT, keep MuJoCo running
pgrep -af fear_hri_bt_node | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 2
echo "Restarting Fear BT (Double DQN brick carry)..."
echo "DQN-model: ${FEAR_DQN_MODEL}"
exec ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
