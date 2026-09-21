#!/usr/bin/env bash
# Launch MuJoCo truth twin with the Fear HRI scenario.
# Run from a built ROS 2 workspace that includes mecanumbot_bringup and mecanumbot_sim.
# Ensure fear_hri_brick_carry.yaml is installed under sim_scenarios (see docs/INTEGRATION.md).

set -euo pipefail
WORKSPACE="${WORKSPACE:-$(pwd)}"
SCENARIO="${SCENARIO:-fear_hri_brick_carry}"

source "$WORKSPACE/install/setup.bash"
ros2 launch mecanumbot_bringup sim.launch.py \
  mode:=truth_twin \
  scenario:="${SCENARIO}" \
  use_rviz:=true
