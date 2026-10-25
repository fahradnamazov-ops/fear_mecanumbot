#!/usr/bin/env bash
set +e
for f in \
  /home/fahrad/mecanumbot_ws/src/mecanumbot_sim/mecanumbot_sim/mujoco_io_node.py \
  /home/fahrad/mecanumbot_ws/build/mecanumbot_sim/mecanumbot_sim/mujoco_io_node.py
do
  echo "==== $f ===="
  ls -la "$f"
  grep -n "apply_overview_camera\|_force_overview_cam\|^import os" "$f" | head -20
done
