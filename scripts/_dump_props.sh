#!/usr/bin/env bash
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
timeout 4 ros2 topic echo /sim/props --once 2>/dev/null | grep -E 'name:|kind:|^      x:|^      y:' | head -120
