#!/usr/bin/env python3
"""Offscreen MuJoCo demo video for Csenge: Double DQN + completion-time routes.

Renders with EGL (no X11) so the clip is always visible. Overlay shows
policy action, chosen corridor, and travel+wait costs.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np
import yaml
from PIL import Image, ImageDraw

LAB = Path("/mnt/c/Users/Fahrad/Desktop/AI Lab")
sys.path.insert(0, str(LAB / "fear_mecanumbot"))

from fear_mecanumbot.constants import ACTION_NAMES, FEAR_MAX  # noqa: E402
from fear_mecanumbot.dqn import DQNAgent, features_live  # noqa: E402
from fear_mecanumbot.route_cost import all_route_costs  # noqa: E402

MODEL = LAB / "mecanumbot_remote/mecanumbot_sim/mujoco/mecanumbot.xml"
SCENARIO = LAB / "mecanumbot_remote/mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml"
WEIGHTS = LAB / "fear_mecanumbot/models/hri_dqn.npz"
OUT_DIR = LAB / "fear_mecanumbot/output"
DESKTOP = Path("/mnt/c/Users/Fahrad/Desktop")

SAFE, HIT = 1.2, 0.35
DECAY, SPIKE, RISE = 0.15, 55.0, 12.0
DT = 0.05
DURATION = 70.0
PATROL_SPEED = 0.35
WHEEL_GAIN = 80.0
CRUISE = 0.42
ROUTE_SWITCH_MARGIN_S = 2.5

# Simplified brick task waypoints (start mat → cube → goal mat)
BRICKS = [(-1.15, 0.55), (-1.15, -0.55), (-0.85, 0.25), (-0.85, -0.25)]
GOAL = (1.35, -0.20)
START = (-1.35, -0.20)


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


def apply_cmd(model, data, vx: float, wz: float = 0.0) -> None:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "base_free")
    adr = int(model.jnt_qposadr[jid])
    dof = int(model.jnt_dofadr[jid])
    w, x, y, z = [float(v) for v in data.qpos[adr + 3 : adr + 7]]
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    yaw += wz * DT
    data.qpos[adr + 0] += vx * math.cos(yaw) * DT
    data.qpos[adr + 1] += vx * math.sin(yaw) * DT
    data.qpos[adr + 2] = 0.06
    data.qpos[adr + 3 : adr + 7] = (math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0))
    data.qvel[dof : dof + 6] = 0.0
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


def route_via(route: str, rx, ry, tx, ty, px, py):
    del py
    if route == "middle":
        return tx, ty
    cy = 0.90 if route == "north" else -0.90
    sign = 1.0 if tx >= rx else -1.0
    if (px - rx) * sign > 0.15:
        return px - sign * 0.70, cy
    if (rx - px) * sign < 0.55:
        return px + sign * 1.10, cy
    return tx, ty


def drive_toward(model, data, gx, gy, speed=CRUISE):
    rx, ry = robot_xy(model, data)
    dx, dy = gx - rx, gy - ry
    dist = math.hypot(dx, dy)
    if dist < 0.08:
        apply_cmd(model, data, 0.0, 0.0)
        return dist
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "base_free")
    adr = int(model.jnt_qposadr[jid])
    w, x, y, z = [float(v) for v in data.qpos[adr + 3 : adr + 7]]
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    desired = math.atan2(dy, dx)
    err = (desired - yaw + math.pi) % (2 * math.pi) - math.pi
    apply_cmd(model, data, speed * max(0.25, 1.0 - abs(err)), 1.8 * err)
    return dist


def main() -> int:
    if not WEIGHTS.is_file():
        print("FAIL: missing", WEIGHTS)
        return 1

    agent = DQNAgent.load(WEIGHTS)
    wps = waypoints()
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    place_props(model, data)
    set_robot_xy(model, data, START[0], START[1])
    set_mocap_xy(model, data, "sim_human_0", 0.0, -0.20, 0.0)
    mujoco.mj_forward(model, data)

    w = min(720, int(getattr(model.vis.global_, "offwidth", 720) or 720))
    h = min(480, int(getattr(model.vis.global_, "offheight", 480) or 480))
    renderer = mujoco.Renderer(model, height=h, width=w)
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.lookat[:] = (0.0, -0.2, 0.15)
    cam.distance = 5.2
    cam.azimuth = 90.0
    cam.elevation = -55.0

    fear = 0.0
    prev_r = 10.0
    frames = []
    t = 0.0
    step = 0
    brick_i = 0
    has_brick = False
    delivered = 0
    route = "middle"
    committed: str | None = None
    commit_has_brick: bool | None = None

    print("Recording Double DQN + completion-time demo for Csenge...")

    while t <= DURATION and delivered < 4:
        px, py = person_xy(wps, t)
        set_mocap_xy(model, data, "sim_human_0", px, py, 0.0)
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

        target = GOAL if has_brick else BRICKS[min(brick_i, len(BRICKS) - 1)]
        tx, ty = target
        costs = all_route_costs((rx, ry), (tx, ty), (px, py))
        totals = [costs["middle"][0], costs["north"][0], costs["south"][0]]
        mx = max(totals) or 1.0
        c_m, c_n, c_s = [v / mx for v in totals]
        # relative 0=cheap like live normalized features
        lo, hi = min(totals), max(totals)
        span = max(1e-3, hi - lo)
        c_m, c_n, c_s = ((c - lo) / span for c in totals)
        feat = features_live(
            fear_level=fear,
            min_range=r,
            has_brick=has_brick,
            target_dist_m=math.hypot(tx - rx, ty - ry),
            person_dx=px - rx,
            person_dy=py - ry,
            risk=risk,
            cost_middle=c_m,
            cost_north=c_n,
            cost_south=c_s,
        )
        q = agent.q_values(feat).copy()
        q[2] = -1e9
        for i in range(3):
            q[3 + i] -= 0.45 * float(feat[7 + i])
        if r < 1.15 and fear > 15.0:
            q[1] += 0.55
            q[0] += 0.25
            q[3] -= 0.35
        aid = int(np.argmax(q))
        action = ACTION_NAMES[aid]
        if commit_has_brick is None or commit_has_brick != has_brick:
            commit_has_brick = has_brick
            committed = None
        if action.startswith("task_"):
            proposed = action.replace("task_", "")
            if committed in ("middle", "north", "south") and proposed != committed:
                if costs[proposed][0] + ROUTE_SWITCH_MARGIN_S >= costs[committed][0]:
                    proposed = committed
            committed = proposed
            route = proposed
            action = "task_%s" % route
        elif action == "freeze":
            pass
        elif action == "avoid":
            pass

        if action == "freeze":
            apply_cmd(model, data, 0.0, 0.0)
        elif action == "avoid":
            apply_cmd(model, data, -min(0.55, 0.25 + 0.004 * fear), 0.9)
        else:
            vx, vy = route_via(route, rx, ry, tx, ty, px, py)
            # Extra lateral clear if too close while tasked
            if r < 1.05:
                away = 1.0 if ry >= py else -1.0
                vy = vy + away * 0.35
            dist = drive_toward(model, data, vx, vy, speed=CRUISE)
            if dist < 0.18 and abs(rx - tx) < 0.25 and abs(ry - ty) < 0.25:
                if has_brick:
                    has_brick = False
                    delivered += 1
                    brick_i = min(brick_i + 1, len(BRICKS) - 1)
                else:
                    has_brick = True

        nsub = max(1, int(DT / model.opt.timestep))
        for _ in range(nsub):
            mujoco.mj_step(model, data)

        if step % 2 == 0:
            renderer.update_scene(data, camera=cam)
            img = Image.fromarray(renderer.render())
            draw = ImageDraw.Draw(img)
            draw.rectangle((4, 4, 510, 92), fill=(0, 0, 0))
            best = min(costs, key=lambda n: costs[n][0])
            draw.text(
                (10, 8),
                f"Double DQN  t={t:4.1f}s  fear={fear:4.1f}  person={r:.2f}m\n"
                f"action={action}  route={route}  bricks={delivered}/4  carrying={has_brick}\n"
                f"cost M={costs['middle'][0]:.1f}s N={costs['north'][0]:.1f}s "
                f"S={costs['south'][0]:.1f}s  best={best}",
                fill=(255, 255, 255),
            )
            frames.append(img)
            if step % 40 == 0:
                print(
                    f"t={t:5.1f} {action:12s} route={route:6s} "
                    f"costM={costs['middle'][0]:5.1f} bricks={delivered} carrying={has_brick}"
                )

        prev_r = r
        t += DT
        step += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M")
    out_mp4 = OUT_DIR / f"csenge_dqn_demo_{stamp}.mp4"
    out_gif = OUT_DIR / f"csenge_dqn_demo_{stamp}.gif"
    desk_mp4 = DESKTOP / f"Csenge_FearHRI_DoubleDQN_{stamp}.mp4"
    note = DESKTOP / f"Csenge_FearHRI_DoubleDQN_{stamp}_NOTE.txt"

    frames[0].save(out_gif, save_all=True, append_images=frames[1::3], duration=80, loop=0)
    seq = OUT_DIR / "_csenge_frames"
    if seq.exists():
        for old in seq.glob("*.png"):
            old.unlink()
    seq.mkdir(exist_ok=True)
    for i, fr in enumerate(frames[::2]):
        fr.save(seq / f"f_{i:04d}.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            "12",
            "-i",
            str(seq / "f_%04d.png"),
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "23",
            str(out_mp4),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not out_mp4.is_file() or out_mp4.stat().st_size < 50_000:
        print("FAIL: mp4 too small / missing")
        return 1

    desk_mp4.write_bytes(out_mp4.read_bytes())
    note.write_text(
        "Fear HRI demo for Csenge\n"
        "========================\n"
        "Policy: Double DQN (hri_dqn.npz)\n"
        "Cost: completion_time = travel + wait\n"
        "Robot chooses middle/north/south itself from costs; no hardcoded route lock.\n"
        "catch_attention masked in sim (IRL-only).\n"
        f"Delivered in clip: {delivered}/4 bricks\n"
        f"Video: {desk_mp4.name}\n"
        f"Also: {out_mp4}\n",
        encoding="utf-8",
    )
    print("saved", out_mp4, "bytes", out_mp4.stat().st_size)
    print("DESKTOP", desk_mp4)
    print("NOTE", note)
    print("DONE bricks=", delivered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
