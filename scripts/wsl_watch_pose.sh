#!/usr/bin/env bash
source /opt/ros/humble/setup.bash
source ~/mecanumbot_ws/install/setup.bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  timeout 2 ros2 topic echo /sim/robot_pose --once 2>/dev/null | python3 -c "
import sys
t=sys.stdin.read().splitlines()
for i,l in enumerate(t):
  if 'position:' in l:
    print('x=', t[i+1].split(':')[1].strip(), 'y=', t[i+2].split(':')[1].strip())
    break
"
  sleep 3
done
