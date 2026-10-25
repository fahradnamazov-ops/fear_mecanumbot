#!/usr/bin/env bash
# Real live MuJoCo ROS session → Windows desktop capture → Desktop mp4 only.
set +e
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
export FEAR_USE_SIM=1
export FEAR_CATCH_ATTENTION=0
export FEAR_TEST_THAW=0
export FEAR_DQN_MODEL="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/models/hri_dqn.npz"

FFMPEG_WIN="/mnt/c/Users/Fahrad/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe"
OUT_DIR="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output"
DESKTOP="/mnt/c/Users/Fahrad/Desktop"
VIDEO="${DESKTOP}/FearHRI_live_session_for_Csenge.mp4"
LOG="/tmp/fear_live_session.log"
FFLOG="${OUT_DIR}/live_session_win_ffmpeg.log"
RECORD_MAX_S="${RECORD_MAX_S:-720}"

mkdir -p "$OUT_DIR"
rm -f "$LOG" "$FFLOG" "$VIDEO"

if [[ ! -f "$FFMPEG_WIN" ]]; then
  echo "FAIL: Windows ffmpeg missing at $FFMPEG_WIN"
  exit 1
fi

bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true
sleep 2

echo "Launching live MuJoCo Fear HRI (viewer ON)..."
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_clean_brick_sim.sh" >"$LOG" 2>&1 &
LAUNCH_PID=$!

READY=0
for i in $(seq 1 150); do
  if grep -Eiq 'Fear action policy: dqn|policy=rl_dqn' "$LOG" 2>/dev/null; then
    READY=1
    break
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "FAIL: launcher exited early"
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
echo "DQN ready — starting Windows desktop capture in 6s"
sleep 6

echo "Recording Windows desktop → $VIDEO"
# Must launch Windows ffmpeg via cmd.exe (PE binary cannot run under Linux)
WIN_FF='C:\Users\Fahrad\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'
WIN_OUT='C:\Users\Fahrad\Desktop\FearHRI_live_session_for_Csenge.mp4'
cmd.exe /c "\"$WIN_FF\" -y -f gdigrab -framerate 12 -i desktop -t $RECORD_MAX_S -pix_fmt yuv420p -an -c:v libx264 -preset veryfast -crf 23 \"$WIN_OUT\"" >"$FFLOG" 2>&1 &
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
    echo "WARN: ffmpeg exited early"
    tail -n 40 "$FFLOG"
    break
  fi
  sleep 3
done

kill -INT "$FF_PID" 2>/dev/null || true
# Windows process may need taskkill
taskkill.exe /IM ffmpeg.exe /F >/dev/null 2>&1 || true
wait "$FF_PID" 2>/dev/null || true
sleep 1

bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_kill_fear.sh" >/dev/null 2>&1 || true

if [[ ! -f "$VIDEO" ]]; then
  echo "FAIL: video missing"
  tail -n 50 "$FFLOG"
  exit 1
fi
BYTES=$(wc -c <"$VIDEO" | tr -d ' ')
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$VIDEO" 2>/dev/null || echo "?")
echo "============================================"
echo " LIVE SESSION VIDEO READY (Windows capture)"
echo "  $VIDEO"
echo "  size=${BYTES} duration=${DUR}s bricks_done=${DONE_OK}"
echo "============================================"
ls -la "$VIDEO"

# Quick blank check: sample a frame mean luminance
PRE="${OUT_DIR}/_preview_live_win.png"
ffmpeg -y -ss 20 -i "$VIDEO" -frames:v 1 "$PRE" >/dev/null 2>&1 || true
python3 - <<PY
from pathlib import Path
from PIL import Image
import statistics
p = Path("${PRE}")
if p.is_file():
    im = Image.open(p).convert("RGB")
    lum = [(r+g+b)/3 for r,g,b in list(im.getdata())[::80]]
    mean = sum(lum)/len(lum)
    sd = statistics.pstdev(lum)
    print(f"frame_check mean={mean:.1f} stdev={sd:.1f}")
    if mean < 5 and sd < 15:
        raise SystemExit("FAIL: captured video looks blank")
print("FRAME_OK")
PY
EC=$?
[[ "$DONE_OK" -eq 1 && "$EC" -eq 0 ]]
