#!/usr/bin/env bash
# Record full Double DQN brick-carry demo video for Csenge.
# Stops when ALL BRICKS DONE (or RECORD_MAX_S timeout).
set +e
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
export FEAR_TEST_THAW=0
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
export FEAR_DQN_MODEL="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz"

STAMP="$(date +%Y%m%d_%H%M)"
OUT_DIR="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output"
DESKTOP="/mnt/c/Users/Fahrad/Desktop"
VIDEO="${OUT_DIR}/csenge_dqn_brick_carry_${STAMP}.mp4"
DESKTOP_COPY="${DESKTOP}/Csenge_FearHRI_DQN_brick_carry_${STAMP}.mp4"
LOG="/tmp/fear_csenge_record.log"
FFLOG="/tmp/fear_csenge_ffmpeg.log"
RECORD_MAX_S="${RECORD_MAX_S:-900}"

mkdir -p "$OUT_DIR"
rm -f "$LOG" "$FFLOG" "$VIDEO"

if [[ ! -f "$FEAR_DQN_MODEL" ]]; then
  echo "FAIL: missing $FEAR_DQN_MODEL"
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg
fi

bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
pkill -f 'ffmpeg.*x11grab' 2>/dev/null || true
sleep 2

echo "Launching Fear HRI Double DQN brick carry..."
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 &
LAUNCH_PID=$!

# Wait for MuJoCo / Fear BT before recording
READY=0
for i in $(seq 1 90); do
  if grep -Eiq 'Fear action policy: dqn|policy=rl_dqn|DQN-model' "$LOG" 2>/dev/null; then
    READY=1
    break
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "FAIL: launcher exited before DQN load"
    tail -n 80 "$LOG"
    exit 1
  fi
  sleep 1
done
if [[ "$READY" -ne 1 ]]; then
  echo "FAIL: DQN policy not ready to record"
  tail -n 80 "$LOG"
  exit 1
fi
sleep 3

echo "Recording display ${DISPLAY} → $VIDEO (max ${RECORD_MAX_S}s)"
ffmpeg -y -f x11grab -framerate 12 -video_size 1280x720 -i "${DISPLAY}.0" \
  -t "$RECORD_MAX_S" -pix_fmt yuv420p -an "$VIDEO" >"$FFLOG" 2>&1 &
FF_PID=$!

DONE_OK=0
DEADLINE=$((SECONDS + RECORD_MAX_S))
while (( SECONDS < DEADLINE )); do
  if grep -Eq 'ALL BRICKS DONE|Confirmed .* \(4/4' "$LOG" 2>/dev/null; then
    DONE_OK=1
    echo "ALL BRICKS DONE — finishing recording in 4s"
    sleep 4
    break
  fi
  if ! kill -0 "$FF_PID" 2>/dev/null; then
    echo "WARN: ffmpeg stopped early"
    break
  fi
  sleep 3
done

kill -INT "$FF_PID" 2>/dev/null || true
wait "$FF_PID" 2>/dev/null || true
sleep 1

# Stop sim so the machine is clean after the clip
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true

if [[ ! -f "$VIDEO" ]] || [[ ! -s "$VIDEO" ]]; then
  echo "FAIL: video missing or empty"
  tail -n 40 "$FFLOG"
  exit 1
fi

cp -f "$VIDEO" "$DESKTOP_COPY"
BYTES=$(wc -c <"$VIDEO" | tr -d ' ')
echo "============================================"
echo " VIDEO READY FOR CSENGE"
echo "  $DESKTOP_COPY"
echo "  also: $VIDEO"
echo "  size: ${BYTES} bytes"
echo "  bricks_done: $DONE_OK"
echo "============================================"
ls -la "$DESKTOP_COPY" "$VIDEO"
[[ "$DONE_OK" -eq 1 ]]
