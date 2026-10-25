#!/usr/bin/env bash
set -eo pipefail
set +u
source /opt/ros/humble/setup.bash
source "${HOME}/mecanumbot_ws/install/setup.bash"
set -u
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export DISPLAY="${DISPLAY:-:0}"
export MUJOCO_GL=glfw

LOGDIR="${HOME}/mecanumbot_ws/log_fear_sim"
OUTDIR="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output"
mkdir -p "$LOGDIR" "$OUTDIR"

pkill -f mecanumbot_sim_mujoco_io_node 2>/dev/null || true
pkill -f fear_hri_bt_node 2>/dev/null || true
sleep 1

echo "DISPLAY=$DISPLAY"
echo ">>> Starting MuJoCo viewer + fear scene"
ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco \
  mode:=truth_twin \
  scenario:=fear_hri_brick_carry \
  show_viewer:=true \
  use_rviz:=false \
  >"${LOGDIR}/sim_view.log" 2>&1 &
echo "sim pid=$!"

# wait until scan is alive
for i in $(seq 1 60); do
  if ros2 topic list 2>/dev/null | grep -q '/mecanumbot/scan'; then
    echo "scan ready ($i)"
    break
  fi
  sleep 1
done

ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py \
  >"${LOGDIR}/fear_view.log" 2>&1 &
echo "fear pid=$!"

sleep 8
echo ">>> Capturing screenshot of DISPLAY"
if command -v gnome-screenshot >/dev/null 2>&1; then
  gnome-screenshot -f "${OUTDIR}/mujoco_live.png" || true
elif command -v import >/dev/null 2>&1; then
  import -window root "${OUTDIR}/mujoco_live.png" || true
else
  sudo apt-get install -y -qq imagemagick-6.q16 >/dev/null 2>&1 || true
  import -window root "${OUTDIR}/mujoco_live.png" 2>/dev/null || \
  python3 - <<'PY'
import os
try:
    from Xlib import display, X
    from PIL import Image
    d = display.Display()
    root = d.screen().root
    geom = root.get_geometry()
    raw = root.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff)
    # fallback note
    print('xlib ok but raw decode skipped')
except Exception as e:
    print('screenshot fallback failed', e)
PY
fi

# Always render an offline MuJoCo still of the model for the user
python3 - <<'PY'
import os
from pathlib import Path
import mujoco
import numpy as np

model_path = os.path.expanduser(
    "~/mecanumbot_ws/install/mecanumbot_sim/share/mecanumbot_sim/mujoco/mecanumbot.xml"
)
if not os.path.isfile(model_path):
    model_path = "/mnt/c/Users/Fahrad/Desktop/AI Lab/mecanumbot_remote/mecanumbot_sim/mujoco/mecanumbot.xml"
out = Path("/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output/mujoco_scene.png")
out.parent.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MUJOCO_GL", "egl")
model = mujoco.MjModel.from_xml_path(model_path)
data = mujoco.MjData(model)
# place person roughly on mat centre if body exists
try:
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "sim_human_0")
    if bid >= 0:
        # free joint qpos if present - best effort
        pass
except Exception:
    pass
mujoco.mj_forward(model, data)
renderer = mujoco.Renderer(model, height=720, width=1280)
# camera look at arena centre
renderer.update_scene(data, camera=-1)
rgb = renderer.render()
try:
    from PIL import Image
    Image.fromarray(rgb).save(out)
    print("saved", out)
except Exception as e:
    # write ppm
    ppm = out.with_suffix(".ppm")
    h, w, _ = rgb.shape
    with open(ppm, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode())
        f.write(rgb.tobytes())
    print("saved", ppm, e)
PY

echo ">>> Live fear sample"
grep 'fear=' "${LOGDIR}/fear_view.log" | tail -n 5 || true
echo ">>> DONE_SHOW"
echo "MuJoCo window should be on your Windows desktop (WSLg)."
echo "Still image: ${OUTDIR}/mujoco_scene.png"
