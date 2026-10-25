#!/usr/bin/env bash
# Live MuJoCo Fear sim with on-screen viewer + screen recording of real behaviour.
set -eo pipefail
set +u
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
export PATH="${HOME}/.local/bin:/usr/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw
set -u

OUT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output"
LOG="${HOME}/mecanumbot_ws/log_fear_sim"
mkdir -p "$OUT" "$LOG"

pkill -f mecanumbot_sim_mujoco_io_node 2>/dev/null || true
pkill -f fear_hri_bt_node 2>/dev/null || true
pkill -f ffmpeg 2>/dev/null || true
sleep 1

echo "DISPLAY=$DISPLAY"
echo ">>> Launch MuJoCo (viewer ON) + Fear HRI"

ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco \
  mode:=truth_twin \
  scenario:=fear_hri_brick_carry \
  show_viewer:=true \
  use_rviz:=false \
  >"${LOG}/live_sim.log" 2>&1 &
SIM_PID=$!

for i in $(seq 1 60); do
  if ros2 topic list 2>/dev/null | grep -q '/mecanumbot/scan'; then
    echo "scan ready ($i)"
    break
  fi
  sleep 1
done

ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py \
  >"${LOG}/live_fear.log" 2>&1 &
FEAR_PID=$!

# Give viewer time to appear
sleep 5

# Install recorder if needed
if ! command -v ffmpeg >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq ffmpeg
fi

echo ">>> Recording 25s of the live MuJoCo window (real robot behaviour)"
# Record whole WSLg display
ffmpeg -y -f x11grab -framerate 15 -video_size 1280x720 -i "${DISPLAY}.0" \
  -t 25 -pix_fmt yuv420p "${OUT}/live_fear_sim.mp4" \
  >"${LOG}/ffmpeg.log" 2>&1 || \
ffmpeg -y -f x11grab -framerate 15 -i "${DISPLAY}.0" \
  -t 25 -pix_fmt yuv420p "${OUT}/live_fear_sim.mp4" \
  >"${LOG}/ffmpeg.log" 2>&1

# Also make a short GIF from the mp4 for easy preview
ffmpeg -y -i "${OUT}/live_fear_sim.mp4" -vf "fps=8,scale=640:-1" -t 20 \
  "${OUT}/live_fear_sim.gif" >>"${LOG}/ffmpeg.log" 2>&1 || true

echo ">>> Sample fear / cmd_vel behaviour"
grep 'fear=' "${LOG}/live_fear.log" | tail -n 8 || true
timeout 3 ros2 topic echo /cmd_vel --once 2>/dev/null | head -20 || true

echo ">>> Files:"
ls -la "${OUT}/live_fear_sim.mp4" "${OUT}/live_fear_sim.gif" 2>/dev/null || true
echo "SIM_PID=$SIM_PID FEAR_PID=$FEAR_PID"
echo ">>> DONE_LIVE_RECORD"
echo "MuJoCo viewer should still be open. Video: ${OUT}/live_fear_sim.mp4"
