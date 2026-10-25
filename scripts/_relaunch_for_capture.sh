#!/usr/bin/env bash
set +e
ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
LOG="$ROOT/output/live_session_real_viewer.log"
bash "$ROOT/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 1
rm -f "$LOG"
# Keep sim alive after this script exits (nohup + disown).
nohup bash "$ROOT/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 </dev/null &
disown
echo "LAUNCHED_PID=$!"
for i in $(seq 1 180); do
  if grep -Eiq 'policy=rl_dqn|Fear action policy: dqn' "$LOG" 2>/dev/null; then
    echo "DQN_READY"
    # Confirm mujoco io still alive
    if pgrep -f mecanumbot_sim_mujoco_io_node >/dev/null 2>&1; then
      echo "SIM_ALIVE"
      exit 0
    fi
  fi
  sleep 1
done
echo "TIMEOUT"
tail -n 80 "$LOG"
exit 1
