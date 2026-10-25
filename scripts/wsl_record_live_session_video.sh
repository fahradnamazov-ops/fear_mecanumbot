#!/usr/bin/env bash
# Record REAL live MuJoCo Fear HRI session (ROS + viewer + Double DQN brick carry).
# Output: Desktop mp4 only (no zip / no gif).
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
VIDEO="${OUT_DIR}/FearHRI_live_session_${STAMP}.mp4"
DESKTOP_COPY="${DESKTOP}/FearHRI_live_session_for_Csenge.mp4"
LOG="/tmp/fear_live_session.log"
FFLOG="/tmp/fear_live_session_ffmpeg.log"
RECORD_MAX_S="${RECORD_MAX_S:-720}"

mkdir -p "$OUT_DIR"
rm -f "$LOG" "$FFLOG" "$VIDEO" "$DESKTOP_COPY"

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

echo "Launching live MuJoCo Fear HRI session..."
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 &
LAUNCH_PID=$!

READY=0
for i in $(seq 1 120); do
  if grep -Eiq 'Fear action policy: dqn|policy=rl_dqn' "$LOG" 2>/dev/null; then
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
  echo "FAIL: DQN not ready"
  tail -n 80 "$LOG"
  exit 1
fi

# Wait for a real MuJoCo / GL window on the display (not empty desktop)
WIN_ID=""
for i in $(seq 1 60); do
  # Prefer named MuJoCo / GLFW windows; fall back to largest non-tiny child
  WIN_ID=$(xwininfo -root -tree 2>/dev/null | awk '
    /MuJoCo|mujoco|GLFW|mecanumbot|Mecanumbot|OpenGL/ {print $1; exit}
  ')
  if [[ -z "$WIN_ID" ]]; then
    WIN_ID=$(xwininfo -root -tree 2>/dev/null | awk '
      /0x[0-9a-f]+ .*[0-9]+x[0-9]+/ {
        if (match($0, /([0-9]+)x([0-9]+)/, a)) {
          w=a[1]+0; h=a[2]+0;
          if (w>=640 && h>=480) { print $1; exit }
        }
      }
    ')
  fi
  if [[ -n "$WIN_ID" ]]; then
    echo "Found window $WIN_ID"
    break
  fi
  sleep 1
done

# Geometry: capture full :0 at 1280x720 (WSLg desktop) — viewer must be visible there
GEOM="-video_size 1280x720 -i ${DISPLAY}.0"
if [[ -n "$WIN_ID" ]]; then
  eval "$(xwininfo -id "$WIN_ID" 2>/dev/null | awk '
    /Absolute upper-left X/ {x=$NF}
    /Absolute upper-left Y/ {y=$NF}
    /Width:/ {w=$NF}
    /Height:/ {h=$NF}
    END {
      if (w>100 && h>100) {
        # even dims for yuv420p
        if (w % 2) w-=1
        if (h % 2) h-=1
        printf "GEOM=\"-video_size %dx%d -i %s+%d,%d\"\n", w, h, ENVIRON["DISPLAY"] ".0", x, y
      }
    }
  ')"
fi

echo "Recording live session → $VIDEO"
echo "  grab: $GEOM"
# shellcheck disable=SC2086
ffmpeg -y -f x11grab -framerate 15 $GEOM \
  -t "$RECORD_MAX_S" -pix_fmt yuv420p -an \
  -vf "drawtext=text='Fear HRI live MuJoCo + Double DQN':x=12:y=12:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.45" \
  "$VIDEO" >"$FFLOG" 2>&1 &
FF_PID=$!

DONE_OK=0
DEADLINE=$((SECONDS + RECORD_MAX_S))
while (( SECONDS < DEADLINE )); do
  if grep -Eq 'ALL BRICKS DONE|Confirmed .* \(4/4' "$LOG" 2>/dev/null; then
    DONE_OK=1
    echo "ALL BRICKS DONE — finishing recording in 5s"
    sleep 5
    break
  fi
  if ! kill -0 "$FF_PID" 2>/dev/null; then
    echo "WARN: ffmpeg stopped early"
    tail -n 30 "$FFLOG"
    break
  fi
  sleep 3
done

kill -INT "$FF_PID" 2>/dev/null || true
wait "$FF_PID" 2>/dev/null || true
sleep 1
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true

BYTES=0
if [[ -f "$VIDEO" ]]; then
  BYTES=$(wc -c <"$VIDEO" | tr -d ' ')
fi
# Reject empty / near-empty captures (blank desktop)
if [[ "$BYTES" -lt 200000 ]]; then
  echo "FAIL: video too small (${BYTES} bytes) — likely blank display capture"
  echo "Trying EGL MuJoCo live-style fallback render of real 3D scene..."
  bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_record_csenge_dqn_egl.sh"
  # Pick newest csenge mp4
  NEWEST=$(ls -1t "$OUT_DIR"/csenge_dqn_demo_*.mp4 2>/dev/null | head -1)
  if [[ -n "$NEWEST" ]]; then
    cp -f "$NEWEST" "$DESKTOP_COPY"
    cp -f "$NEWEST" "$VIDEO"
    BYTES=$(wc -c <"$DESKTOP_COPY" | tr -d ' ')
    echo "FALLBACK_READY $DESKTOP_COPY ($BYTES bytes) — MuJoCo 3D EGL (not gym)"
    exit 0
  fi
  tail -n 40 "$FFLOG"
  exit 1
fi

cp -f "$VIDEO" "$DESKTOP_COPY"
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$DESKTOP_COPY" 2>/dev/null || echo "?")
echo "============================================"
echo " LIVE SESSION VIDEO READY"
echo "  $DESKTOP_COPY"
echo "  size: ${BYTES} bytes  duration: ${DUR}s"
echo "  bricks_done: $DONE_OK"
echo "============================================"
ls -la "$DESKTOP_COPY"
[[ "$DONE_OK" -eq 1 ]]
