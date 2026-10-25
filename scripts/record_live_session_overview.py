#!/usr/bin/env python3
"""Record live Fear HRI MuJoCo session with a clean overview camera (EGL).

Mirrors the running ROS/MuJoCo brick-carry poses into an offscreen renderer
with a fixed elevated camera — no zoomed-in free-camera mess.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from PIL import Image, ImageDraw
from rclpy.node import Node

LAB = Path("/mnt/c/Users/Fahrad/Desktop/AI Lab")
MODEL = LAB / "mecanumbot_remote/mecanumbot_sim/mujoco/mecanumbot.xml"
SCENARIO = LAB / "mecanumbot_remote/mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml"
OUT = Path("/mnt/c/Users/Fahrad/Desktop/FearHRI_live_session_for_Csenge.mp4")
TMP_DIR = LAB / "fear_mecanumbot/output/_live_overview_frames"
LOG = LAB / "fear_mecanumbot/output/live_session_win_record.log"

W, H = 640, 480
FPS = 12
MAX_S = 420.0


class PoseMirror(Node):
    def __init__(self):
        super().__init__("fear_live_overview_recorder")
        self.robot = None
        self.person = None
        self.create_subscription(PoseStamped, "/sim/robot_pose", self._robot, 10)
        self.create_subscription(
            PoseStamped, "/sim/subject_pose_ground_truth", self._person, 10
        )
        self.create_subscription(PoseStamped, "subject_pose", self._person, 10)

    def _robot(self, msg: PoseStamped):
        p = msg.pose.position
        self.robot = (float(p.x), float(p.y), float(p.z))

    def _person(self, msg: PoseStamped):
        p = msg.pose.position
        self.person = (float(p.x), float(p.y), float(p.z))


def set_freejoint_xy(model, data, x, y, z=0.06):
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "base_free")
    adr = int(model.jnt_qposadr[jid])
    dof = int(model.jnt_dofadr[jid])
    data.qpos[adr : adr + 3] = (x, y, z)
    data.qpos[adr + 3 : adr + 7] = (1, 0, 0, 0)
    data.qvel[dof : dof + 6] = 0.0


def set_mocap_xy(model, data, body, x, y, z=0.0):
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
    if bid < 0:
        return
    mid = int(model.body_mocapid[bid])
    if mid < 0:
        return
    data.mocap_pos[mid] = (x, y, z)
    data.mocap_quat[mid] = (1, 0, 0, 0)


def place_static_props(model, data):
    import yaml

    data_sc = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for prop in data_sc["scenario"].get("props", []):
        name = prop["body_name"]
        pose = prop["pose"]
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        if bid < 0:
            continue
        mid = int(model.body_mocapid[bid])
        if mid >= 0:
            data.mocap_pos[mid] = (
                float(pose["x"]),
                float(pose["y"]),
                float(pose.get("z", 0.0)),
            )
            data.mocap_quat[mid] = (1, 0, 0, 0)
        elif name.startswith("sim_cube"):
            jname = f"{name}_free"
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                adr = model.jnt_qposadr[jid]
                data.qpos[adr : adr + 3] = (pose["x"], pose["y"], 0.035)
                data.qpos[adr + 3 : adr + 7] = (1, 0, 0, 0)


def bricks_done(log_path: Path) -> bool:
    if not log_path.is_file():
        return False
    txt = log_path.read_text(encoding="utf-8", errors="ignore")
    return "ALL BRICKS DONE" in txt


def main() -> int:
    if not MODEL.is_file():
        print("FAIL: missing model", MODEL)
        return 1

    rclpy.init()
    node = PoseMirror()
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    place_static_props(model, data)
    mujoco.mj_forward(model, data)

    renderer = mujoco.Renderer(model, height=H, width=W)
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    # Elevated overview of the whole arena
    cam.lookat[:] = (0.0, -0.15, 0.05)
    cam.distance = 6.8
    cam.azimuth = 135.0
    cam.elevation = -48.0

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    for old in TMP_DIR.glob("*.png"):
        old.unlink()

    print("Waiting for live poses...")
    t0 = time.time()
    while time.time() - t0 < 60.0:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.robot is not None and node.person is not None:
            break
    if node.robot is None or node.person is None:
        print("FAIL: no /sim/robot_pose or subject pose yet")
        node.destroy_node()
        rclpy.shutdown()
        return 1
    print("Poses OK — recording overview", OUT)

    frames = 0
    start = time.time()
    last_save = 0.0
    while time.time() - start < MAX_S:
        rclpy.spin_once(node, timeout_sec=0.0)
        if node.robot is not None:
            set_freejoint_xy(model, data, node.robot[0], node.robot[1], max(0.05, node.robot[2]))
        if node.person is not None:
            px, py = node.person[0], node.person[1]
            set_mocap_xy(model, data, "sim_human_0", px, py, 0.0)
            set_mocap_xy(model, data, "sim_human_0_torso_lower", px, py, 0.45)
            set_mocap_xy(model, data, "sim_human_0_torso_upper", px, py, 0.85)
        mujoco.mj_forward(model, data)

        now = time.time()
        if now - last_save >= 1.0 / FPS:
            renderer.update_scene(data, camera=cam)
            img = Image.fromarray(renderer.render())
            draw = ImageDraw.Draw(img)
            draw.rectangle((6, 6, 640, 54), fill=(0, 0, 0))
            rx, ry = node.robot[0], node.robot[1] if node.robot else (0, 0)
            px, py = node.person[0], node.person[1] if node.person else (0, 0)
            dist = math.hypot(px - rx, py - ry)
            draw.text(
                (12, 10),
                f"Live Fear HRI  t={now - start:5.1f}s  person={dist:.2f}m\n"
                f"Double DQN brick-carry  (overview camera)",
                fill=(255, 255, 255),
            )
            img.save(TMP_DIR / f"f{frames:05d}.png")
            frames += 1
            last_save = now

        if bricks_done(LOG):
            # a few extra seconds of overrun
            if time.time() - start > 8.0:
                # wait ~3s more frames
                end_extra = time.time() + 3.0
                while time.time() < end_extra:
                    rclpy.spin_once(node, timeout_sec=0.05)
                    if node.robot is not None:
                        set_freejoint_xy(
                            model, data, node.robot[0], node.robot[1], max(0.05, node.robot[2])
                        )
                    if node.person is not None:
                        px, py = node.person[0], node.person[1]
                        set_mocap_xy(model, data, "sim_human_0", px, py, 0.0)
                    mujoco.mj_forward(model, data)
                    renderer.update_scene(data, camera=cam)
                    Image.fromarray(renderer.render()).save(TMP_DIR / f"f{frames:05d}.png")
                    frames += 1
                    time.sleep(1.0 / FPS)
                break
        time.sleep(0.01)

    node.destroy_node()
    rclpy.shutdown()

    if frames < 20:
        print("FAIL: too few frames", frames)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(TMP_DIR / "f%05d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-movflags", "+faststart",
        str(OUT),
    ]
    print("Encoding", OUT, "frames", frames)
    subprocess.check_call(cmd)
    print("READY", OUT, "bytes", OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
