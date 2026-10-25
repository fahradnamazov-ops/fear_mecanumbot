#!/usr/bin/env bash
# End-to-end Fear HRI brick carry with Double DQN.
# PASS only if logs contain DQN load + ALL BRICKS DONE.
set +e
LOG="/tmp/fear_e2e_dqn.log"
rm -f "$LOG"
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
export FEAR_TEST_THAW=0
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
export FEAR_DQN_MODEL="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz"

if [[ ! -f "$FEAR_DQN_MODEL" ]]; then
  echo "FAIL: missing $FEAR_DQN_MODEL"
  exit 1
fi

bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 2

echo "Launching e2e (log=$LOG)..."
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 &
LAUNCH_PID=$!
echo "launcher_pid=$LAUNCH_PID"

DEADLINE=$((SECONDS + 900))
DQN_OK=0
DONE_OK=0
while (( SECONDS < DEADLINE )); do
  if grep -Eiq 'Fear action policy: dqn|SelectFear: RL dqn loaded|policy=rl_dqn|DQN-model' "$LOG"; then
    DQN_OK=1
  fi
  if grep -Eq 'ALL BRICKS DONE|Confirmed .* \(4/4' "$LOG"; then
    DONE_OK=1
    break
  fi
  if grep -q 'Fear action policy: dqn' "$LOG"; then
    if ! pgrep -af fear_hri_bt_node | grep -v grep >/dev/null; then
      echo "FAIL: fear_hri_bt_node died after DQN load"
      tail -n 120 "$LOG"
      exit 1
    fi
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "FAIL: launcher exited early"
    tail -n 100 "$LOG"
    exit 1
  fi
  sleep 5
done

echo "----- evidence (policy) -----"
grep -Ein 'dqn|FEAR_DQN|DQN-model|policy=' "$LOG" | tail -n 40
echo "----- evidence (bricks) -----"
grep -Ein 'ALL BRICKS|delivered=|Confirmed|Grabbed|route RL|task:seek' "$LOG" | tail -n 60

if [[ "$DQN_OK" -ne 1 ]]; then
  echo "FAIL: Double DQN load not evidenced in logs"
  tail -n 100 "$LOG"
  exit 1
fi
if [[ "$DONE_OK" -ne 1 ]]; then
  echo "FAIL: ALL BRICKS DONE not reached within timeout"
  exit 1
fi

echo "PASS: e2e Double DQN + ALL BRICKS DONE"
exit 0
