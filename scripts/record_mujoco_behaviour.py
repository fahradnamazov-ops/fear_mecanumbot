#!/usr/bin/env python3
"""Record MuJoCo robot behaviour under Fear HRI policy (person patrol + robot reacts)."""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

LAB = Path("/mnt/c/Users/Fahrad/Desktop/AI Lab")
MODEL = LAB / "mecanumbot_remote/mecanumbot_sim/mujoco/mecanumbot.xml"
SCENARIO = LAB / "mecanumbot_remote/mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml"
OUT_DIR = LAB / "fear_mecanumbot/output"
OUT_GIF = OUT_DIR / "robot_behaviour_live.gif"
OUT_MP4 = OUT_DIR / "robot_behaviour_live.mp4"

SAFE, HIT = 1.2, 0.35
DECAY, SPIKE, RISE = 0.15, 55.0, 12.0
DT = 0.05
DURATION = 40.0
PATROL_SPEED = 0.45
# Stronger wheel cmds so task/avoid motion is obvious on camera
WHEEL_GAIN = 80.0


def waypoints():
    data = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    human = next(a for a in data["scenario"]["actors"] if a["kind"] == "human")
    return [(float(w["x"]), float(w["y"]), float(w.get("pause", 0.0))) for w in human["motion"]["waypoints"]]


def person_xy(wps, t):
    times, xs, ys = [], [], []
    clock = 0.0
    n = len(wps)
    for i in range(n):
        x0, y0, pause = wps[i]
        x1, y1, _ = wps[(i + 1) % n]
        dist = math.hypot(x1 - x0, y1 - y0)
        move_t = dist / PATROL_SPEED if PATROL_SPEED else 0.0
        times += [clock, clock + move_t]
        xs += [x0, x1]
        ys += [y0, y1]
        clock += move_t
        if pause > 0:
            clock += pause
            times.append(clock)
            xs.append(x1)
            ys.append(y1)
    period = clock or 1.0
    tau = t % period
    for i in range(len(times) - 1):
        if times[i] <= tau <= times[i + 1]:
            span = max(1e-9, times[i + 1] - times[i])
            u = (tau - times[i]) / span
            return xs[i] + u * (xs[i + 1] - xs[i]), ys[i] + u * (ys[i + 1] - ys[i])
    return xs[-1], ys[-1]


def mocap_id_for_body(model, body_name: str) -> int:
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if bid < 0:
        return -1
    return int(model.body_mocapid[bid])


def set_mocap_xy(model, data, body_name: str, x: float, y: float, z: float = 0.0) -> None:
    mid = mocap_id_for_body(model, body_name)
    if mid < 0:
        return
    data.mocap_pos[mid] = (x, y, z)
    data.mocap_quat[mid] = (1, 0, 0, 0)


def set_robot_xy(model, data, x: float, y: float) -> None:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "base_free")
    adr = model.jnt_qposadr[jid]
    data.qpos[adr : adr + 3] = (x, y, 0.06)
    data.qpos[adr + 3 : adr + 7] = (1, 0, 0, 0)
    data.qvel[model.jnt_dofadr[jid] : model.jnt_dofadr[jid] + 6] = 0.0


def robot_xy(model, data):
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base_link")
    return float(data.xpos[bid][0]), float(data.xpos[bid][1])


def risk_of(r, closing):
    if r <= HIT:
        prox = 1.0
    elif r >= SAFE:
        prox = 0.0
    else:
        prox = (SAFE - r) / (SAFE - HIT)
    return float(max(0.0, min(1.0, prox + max(0.0, closing) * 0.5)))


def choose(fear, r, risk):
    if r <= HIT + 0.05 or (fear >= 70 and r < SAFE):
        return "freeze"
    if fear >= 40 or risk >= 0.5:
        return "avoid"
    if 25 <= fear < 40:
        return "catch_attention"
    return "task"


def apply_cmd(model, data, vx: float, wz: float = 0.0) -> None:
    """Integrate planar motion on freejoint (keeps wheels-down, no tip-over)."""
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "base_free")
    adr = int(model.jnt_qposadr[jid])
    dof = int(model.jnt_dofadr[jid])
    # yaw from current quat (w,x,y,z)
    w, x, y, z = [float(v) for v in data.qpos[adr + 3 : adr + 7]]
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    yaw += wz * DT
    data.qpos[adr + 0] += vx * math.cos(yaw) * DT
    data.qpos[adr + 1] += vx * math.sin(yaw) * DT
    data.qpos[adr + 2] = 0.06
    data.qpos[adr + 3 : adr + 7] = (math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0))
    data.qvel[dof : dof + 6] = 0.0
    # Spin wheels for visual feedback
    yaw_w = wz * 0.35
    raw = {"bl": vx - yaw_w, "br": vx + yaw_w, "fl": vx - yaw_w, "fr": vx + yaw_w}
    for name, val in raw.items():
        aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
        if aid >= 0:
            data.ctrl[aid] = float(np.clip(val * WHEEL_GAIN, -40, 40))


def place_props(model, data):
    data_sc = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for prop in data_sc["scenario"].get("props", []):
        name = prop["body_name"]
        pose = prop["pose"]
        mid = mocap_id_for_body(model, name)
        if mid >= 0:
            data.mocap_pos[mid] = (pose["x"], pose["y"], pose.get("z", 0.0))
            data.mocap_quat[mid] = (1, 0, 0, 0)
        elif name.startswith("sim_cube"):
            jname = f"{name}_free"
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid >= 0:
                adr = model.jnt_qposadr[jid]
                data.qpos[adr : adr + 3] = (pose["x"], pose["y"], 0.035)
                data.qpos[adr + 3 : adr + 7] = (1, 0, 0, 0)


def main() -> int:
    wps = waypoints()
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    place_props(model, data)
    # Start on Csenge's start mat, upright, drive toward person
    set_robot_xy(model, data, -1.35, -0.20)
    set_mocap_xy(model, data, "sim_human_0", 0.0, -0.20, 0.0)
    # park unused limb segments near root for visibility of torso only is ok
    mujoco.mj_forward(model, data)

    w = min(640, int(getattr(model.vis.global_, "offwidth", 640) or 640))
    h = min(480, int(getattr(model.vis.global_, "offheight", 480) or 480))
    renderer = mujoco.Renderer(model, height=h, width=w)
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.lookat[:] = (0.0, -0.2, 0.15)
    cam.distance = 5.0
    cam.azimuth = 90.0
    cam.elevation = -55.0

    fear = 0.0
    prev_r = 10.0
    frames = []
    t = 0.0
    step = 0
    print("Recording Fear HRI robot behaviour in MuJoCo...")

    while t <= DURATION:
        px, py = person_xy(wps, t)
        set_mocap_xy(model, data, "sim_human_0", px, py, 0.0)
        # keep limbs roughly with root (simple)
        for seg, dz in (
            ("sim_human_0_torso_lower", 0.45),
            ("sim_human_0_torso_upper", 0.85),
        ):
            set_mocap_xy(model, data, seg, px, py, dz)

        rx, ry = robot_xy(model, data)
        r = math.hypot(px - rx, py - ry)
        closing = max(0.0, (prev_r - r) / DT)
        risk = risk_of(r, closing)
        if r <= HIT:
            fear = min(100.0, fear + SPIKE)
        else:
            fear = max(0.0, fear - DECAY * DT)
        fear = min(100.0, fear + RISE * risk * DT)
        action = choose(fear, r, risk)

        if action == "freeze":
            apply_cmd(model, data, 0.0, 0.0)
        elif action == "avoid":
            # Back away from person + yaw clear
            apply_cmd(model, data, -min(0.55, 0.25 + 0.004 * fear), 0.9)
        elif action == "catch_attention":
            apply_cmd(model, data, 0.0, 1.6)
        else:
            apply_cmd(model, data, 0.45, 0.0)  # task: drive toward person / goal (+x)

        nsub = max(1, int(DT / model.opt.timestep))
        for _ in range(nsub):
            mujoco.mj_step(model, data)

        if step % 2 == 0:
            renderer.update_scene(data, camera=cam)
            img = Image.fromarray(renderer.render())
            draw = ImageDraw.Draw(img)
            draw.rectangle((4, 4, 360, 70), fill=(0, 0, 0, 180))
            draw.text(
                (10, 10),
                f"t={t:5.1f}s  range={r:.2f}m  fear={fear:5.1f}\naction={action}",
                fill=(255, 255, 255),
            )
            frames.append(img)
            if step % 40 == 0:
                print(f"t={t:5.1f} range={r:.2f} fear={fear:5.1f} action={action:16s} robot=({rx:.2f},{ry:.2f})")

        prev_r = r
        t += DT
        step += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT_GIF, save_all=True, append_images=frames[1::2], duration=70, loop=0)
    print("saved", OUT_GIF)

    seq = OUT_DIR / "_beh_frames"
    seq.mkdir(exist_ok=True)
    for i, fr in enumerate(frames[::2]):
        fr.save(seq / f"f_{i:04d}.png")
    cmd = [
        "ffmpeg", "-y", "-framerate", "12",
        "-i", str(seq / "f_%04d.png"),
        "-pix_fmt", "yuv420p", str(OUT_MP4),
    ]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if OUT_MP4.is_file():
        print("saved", OUT_MP4, "bytes", OUT_MP4.stat().st_size)
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
