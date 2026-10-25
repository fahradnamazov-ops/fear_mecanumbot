#!/usr/bin/env bash
set -eo pipefail
set +u
source /opt/ros/humble/setup.bash
set -u
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"

WS="${HOME}/mecanumbot_ws"
cd "$WS"

echo ">>> rosdep install"
set +e
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
set -e

echo ">>> colcon build"
colcon build --symlink-install --packages-up-to \
  mecanumbot_bringup \
  mecanumbot_fear_hri_behaviour \
  --allow-overriding mecanumbot_sim || \
colcon build --symlink-install --packages-select \
  mecanumbot_msgs \
  mecanumbot_description \
  mecanumbot_core \
  mecanumbot_sim \
  mecanumbot_bringup \
  mecanumbot_bt_config \
  mecanumbot_movement_behaviours \
  mecanumbot_fear_hri_behaviour \
  --continue-on-error

set +u
source "${WS}/install/setup.bash"
set -u
echo ">>> packages"
ros2 pkg list | grep mecanumbot || true
echo ">>> DONE_BUILD"
