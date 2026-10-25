#!/usr/bin/env python3
"""Render an overhead still of the Mecanumbot MuJoCo arena."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
from PIL import Image

MODEL = Path(
    "/mnt/c/Users/Fahrad/Desktop/AI Lab/mecanumbot_remote/mecanumbot_sim/mujoco/mecanumbot.xml"
)
OUT = Path("/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output/mujoco_scene.png")

model = mujoco.MjModel.from_xml_path(str(MODEL))
data = mujoco.MjData(model)

# Place human on mat centre if freejoint exists.
bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "sim_human_0")
if bid >= 0:
    for j in range(model.njnt):
        if model.jnt_bodyid[j] == bid and model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
            adr = model.jnt_qposadr[j]
            data.qpos[adr : adr + 3] = (0.0, -0.20, 0.0)
            data.qpos[adr + 3 : adr + 7] = (1, 0, 0, 0)
            break

mujoco.mj_forward(model, data)

w = int(getattr(model.vis.global_, "offwidth", 640) or 640)
h = int(getattr(model.vis.global_, "offheight", 480) or 480)
renderer = mujoco.Renderer(model, height=min(720, h) if h >= 480 else h, width=min(960, w) if w >= 640 else w)

cam = mujoco.MjvCamera()
mujoco.mjv_defaultFreeCamera(model, cam)
cam.lookat[:] = (0.0, 0.0, 0.2)
cam.distance = 6.0
cam.azimuth = 90.0
cam.elevation = -55.0

renderer.update_scene(data, camera=cam)
rgb = renderer.render()
OUT.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(rgb).save(OUT)
print(f"saved {OUT} shape={rgb.shape}")
