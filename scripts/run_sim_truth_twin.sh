#!/usr/bin/env bash
# Launch MuJoCo truth twin with fear_hri scenario (run from ROS workspace root).
# Requires: mecanumbot built, scenario copied or path passed.

set -euo pipefail
WORKSPACE="${WORKSPACE:-$(pwd)}"
SCENARIO="${SCENARIO:-fear_hri_brick_carry}"

source "$WORKSPACE/install/setup.bash"
ros2 launch mecanumbot_bringup sim.launch.py \
  mode:=truth_twin \
  scenario:="${SCENARIO}" \
  use_rviz:=true
