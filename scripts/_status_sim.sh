#!/usr/bin/env bash
set +e
echo "=== processes ==="
ps -ef | grep -E 'mujoco|fear_hri|ros2 launch|nav_shim' | grep -v grep | head -20
echo "=== log tail ==="
tail -n 15 "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output/live_session_real_viewer.log" 2>/dev/null
