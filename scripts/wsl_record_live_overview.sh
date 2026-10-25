#!/usr/bin/env bash
# Live MuJoCo Fear HRI session + elevated overview video (good camera).
set +e
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
export FEAR_TEST_THAW=0
export FEAR_DQN_MODEL="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz"

ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
LOG="$ROOT/output/live_session_win_record.log"
OUT="/mnt/c/Users/Fahrad/Desktop/FearHRI_live_session_for_Csenge.mp4"
REC_LOG="/tmp/fear_overview_rec.log"

source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
export PYTHONPATH="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot:${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export PATH="/usr/bin:/bin:${HOME}/.local/bin:${PATH}"

mkdir -p "$ROOT/output"
rm -f "$LOG" "$OUT" "$REC_LOG"
sed -i 's/\r$//' "$ROOT/scripts/record_live_session_overview.py"

bash "$ROOT/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 2

echo "Launching live MuJoCo Fear HRI..."
bash "$ROOT/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 &
LAUNCH_PID=$!

READY=0
for i in $(seq 1 150); do
  if grep -Eiq 'policy=rl_dqn|Fear action policy: dqn' "$LOG" 2>/dev/null; then
    READY=1
    break
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "FAIL: launcher died"
    tail -n 60 "$LOG"
    exit 1
  fi
  sleep 1
done
if [[ "$READY" -ne 1 ]]; then
  echo "FAIL: DQN not ready"
  exit 1
fi
echo "DQN ready — starting overview recorder (elevated camera)"
sleep 3

# Force EGL for the overview mirror (viewer stays glfw)
export MUJOCO_GL=egl
python3 "$ROOT/scripts/record_live_session_overview.py" >"$REC_LOG" 2>&1 &
REC_PID=$!

DONE=0
DEADLINE=$((SECONDS + 480))
while (( SECONDS < DEADLINE )); do
  if grep -Eq 'ALL BRICKS DONE' "$LOG" 2>/dev/null; then
    DONE=1
    echo "ALL BRICKS DONE — waiting for encoder"
  fi
  if ! kill -0 "$REC_PID" 2>/dev/null; then
    echo "Recorder finished"
    break
  fi
  sleep 3
done

wait "$REC_PID" 2>/dev/null
REC_EC=$?
bash "$ROOT/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true

if [[ ! -f "$OUT" ]] || [[ "$(wc -c <"$OUT" | tr -d ' ')" -lt 200000 ]]; then
  echo "FAIL: overview video missing/small"
  tail -n 80 "$REC_LOG"
  exit 1
fi

BYTES=$(wc -c <"$OUT" | tr -d ' ')
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT" 2>/dev/null || echo "?")
echo "============================================"
echo " LIVE OVERVIEW VIDEO READY"
echo "  $OUT"
echo "  size=${BYTES} duration=${DUR}s bricks_done=${DONE} rec_ec=${REC_EC}"
echo "============================================"
ls -la "$OUT"
[[ "$DONE" -eq 1 && "$REC_EC" -eq 0 ]]
