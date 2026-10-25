#!/usr/bin/env bash
set -eo pipefail
export DISPLAY="${DISPLAY:-:0}"
OUT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output/live_mujoco_viewer.mp4"
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
echo "Recording live MuJoCo viewer for 18s..."
ffmpeg -y -video_size 1280x720 -framerate 12 -f x11grab -i :0.0 -t 18 -pix_fmt yuv420p "$OUT"
ls -la "$OUT"
echo "DONE"
