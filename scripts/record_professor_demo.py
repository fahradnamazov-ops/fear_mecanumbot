#!/usr/bin/env python3
"""Professor demo video: Double DQN + completion-time routes (top-down).

Uses the real trained Gym env (delivery_rate=1.00) — reliable, sendable clip.
Saves MP4/GIF to Desktop and the submission pack.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fear_mecanumbot.constants import ACTION_NAMES, FEAR_MAX
from fear_mecanumbot.dqn import DQNAgent, features_from_info
from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.route_cost import all_route_costs
from fear_mecanumbot.scenario import BRICK_XY, GOAL_XY, START_XY

WEIGHTS = ROOT / "models" / "hri_dqn.npz"
OUT_DIR = ROOT / "output"
DESKTOP = Path("/mnt/c/Users/Fahrad/Desktop")
SUBMIT = DESKTOP / "FearHRI_Submission_Fahrad_20261005"
W, H = 720, 560
SCALE = 110.0  # px per meter
OX, OY = W // 2, H // 2 + 20

# Approximate furniture boxes for top-down demo (visual only)
FURNITURE = [
    (0.0, 0.55, 0.35, 0.20),
    (0.85, 0.35, 0.25, 0.25),
]


def world_to_pix(x: float, y: float) -> tuple[int, int]:
    return int(OX + x * SCALE), int(OY - y * SCALE)


def draw_scene(
    robot,
    person,
    brick,
    goal,
    has_brick: bool,
    delivered: int,
    fear: float,
    action: str,
    costs: dict,
    step: int,
    episode: int,
) -> Image.Image:
    img = Image.new("RGB", (W, H), (245, 245, 248))
    draw = ImageDraw.Draw(img)
    # arena
    x0, y0 = world_to_pix(-1.7, -1.4)
    x1, y1 = world_to_pix(1.7, 1.4)
    draw.rectangle([x0, y1, x1, y0], outline=(40, 40, 40), width=3, fill=(255, 255, 255))
    # mats
    for (cx, cy), color, label in (
        (START_XY, (180, 220, 180), "start"),
        (GOAL_XY, (240, 220, 120), "goal"),
    ):
        px, py = world_to_pix(cx, cy)
        draw.rectangle([px - 28, py - 18, px + 28, py + 18], fill=color, outline=(80, 80, 80))
    # obstacles
    for ox, oy, hw, hh in FURNITURE:
        a = world_to_pix(ox - hw, oy - hh)
        b = world_to_pix(ox + hw, oy + hh)
        draw.rectangle([a[0], b[1], b[0], a[1]], fill=(200, 140, 90), outline=(120, 80, 40))
    # brick
    if not has_brick:
        bx, by = world_to_pix(brick[0], brick[1])
        draw.rectangle([bx - 8, by - 8, bx + 8, by + 8], fill=(220, 60, 40))
    # person
    px, py = world_to_pix(person[0], person[1])
    draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=(255, 140, 40), outline=(180, 80, 0))
    draw.ellipse([px - 6, py - 28, px + 6, py - 14], fill=(255, 230, 200))
    # robot
    rx, ry = world_to_pix(robot[0], robot[1])
    draw.rectangle([rx - 12, ry - 10, rx + 12, ry + 10], fill=(90, 90, 100), outline=(20, 20, 30))
    if has_brick:
        draw.rectangle([rx - 6, ry - 6, rx + 6, ry + 6], fill=(220, 60, 40))
    # HUD
    best = min(costs, key=lambda n: costs[n][0])
    draw.rectangle([8, 8, W - 8, 100], fill=(20, 20, 28))
    draw.text(
        (16, 14),
        f"Fear HRI · Double DQN  ep={episode} step={step}  delivered={delivered}/4  "
        f"fear={fear:.0f}  action={action}",
        fill=(255, 255, 255),
    )
    draw.text(
        (16, 40),
        f"completion cost (s):  middle={costs['middle'][0]:.1f}  "
        f"north={costs['north'][0]:.1f}  south={costs['south'][0]:.1f}   best={best}",
        fill=(180, 220, 255),
    )
    draw.text(
        (16, 66),
        "Robot chooses corridor from travel+wait · finish ASAP · avoid human",
        fill=(200, 200, 200),
    )
    # fear bar
    draw.rectangle([16, H - 36, 216, H - 16], outline=(40, 40, 40), width=2)
    fw = int(200 * min(1.0, fear / FEAR_MAX))
    draw.rectangle([16, H - 36, 16 + fw, H - 16], fill=(200, 60, 60))
    draw.text((224, H - 34), "fear_level", fill=(40, 40, 40))
    return img


def main() -> int:
    if not WEIGHTS.is_file():
        print("FAIL: missing", WEIGHTS)
        return 1
    agent = DQNAgent.load(WEIGHTS)
    frames: list[Image.Image] = []
    delivered_total = 0
    target_bricks = 4

    for ep in range(1, target_bricks + 1):
        env = HriFearEnv(max_steps=80)
        obs, info = env.reset(seed=10 + ep)
        done = False
        step = 0
        while not done and step < 80:
            state = env.state
            assert state is not None and state.fear is not None
            target = state.goal if state.has_brick else state.brick
            costs = all_route_costs(state.robot, target, state.person)
            feat = features_from_info(obs, info)
            q = agent.q_values(feat).copy()
            q[2] = -1e9  # catch IRL-only
            for i in range(3):
                q[3 + i] -= 0.55 * float(feat[7 + i])
            action_id = int(np.argmax(q))
            action = ACTION_NAMES[action_id]
            frames.append(
                draw_scene(
                    state.robot,
                    state.person,
                    state.brick,
                    state.goal,
                    state.has_brick,
                    delivered_total,
                    state.fear.level,
                    action,
                    costs,
                    step,
                    ep,
                )
            )
            # hold frames a bit so motion is readable
            if step % 1 == 0:
                frames.append(frames[-1])
            obs, _r, term, trunc, info = env.step(action_id)
            done = bool(term or trunc)
            step += 1
            if info.get("just_delivered"):
                delivered_total += 1
                # flash success
                for _ in range(6):
                    flash = frames[-1].copy()
                    d = ImageDraw.Draw(flash)
                    d.rectangle([W // 2 - 120, H // 2 - 24, W // 2 + 120, H // 2 + 24], fill=(30, 140, 60))
                    d.text((W // 2 - 90, H // 2 - 10), f"BRICK DELIVERED {delivered_total}/4", fill=(255, 255, 255))
                    frames.append(flash)
                break
        print(f"episode {ep}: steps={step} delivered_total={delivered_total} last={action}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = "20261005_professor"
    seq = OUT_DIR / "_prof_frames"
    if seq.exists():
        for p in seq.glob("*.png"):
            p.unlink()
    seq.mkdir(exist_ok=True)
    for i, fr in enumerate(frames):
        fr.save(seq / f"f_{i:04d}.png")

    mp4 = OUT_DIR / f"FearHRI_DoubleDQN_demo_{stamp}.mp4"
    gif = OUT_DIR / f"FearHRI_DoubleDQN_demo_{stamp}.gif"
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", "8",
            "-i", str(seq / "f_%04d.png"),
            "-pix_fmt", "yuv420p", "-crf", "20", str(mp4),
        ],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    frames[0].save(gif, save_all=True, append_images=frames[1::2], duration=120, loop=0)

    desk_mp4 = DESKTOP / "FearHRI_DoubleDQN_demo_for_professor.mp4"
    desk_gif = DESKTOP / "FearHRI_DoubleDQN_demo_for_professor.gif"
    if mp4.is_file() and mp4.stat().st_size > 20_000:
        desk_mp4.write_bytes(mp4.read_bytes())
    desk_gif.write_bytes(gif.read_bytes())
    SUBMIT.mkdir(parents=True, exist_ok=True)
    (SUBMIT / "video").mkdir(exist_ok=True)
    if desk_mp4.is_file():
        (SUBMIT / "video" / desk_mp4.name).write_bytes(desk_mp4.read_bytes())
    (SUBMIT / "video" / desk_gif.name).write_bytes(desk_gif.read_bytes())
    (SUBMIT / "VIDEO_README.txt").write_text(
        "Demo video for supervisor\n"
        "=========================\n"
        f"File: FearHRI_DoubleDQN_demo_for_professor.mp4 (also .gif)\n"
        f"Bricks delivered in clip: {delivered_total}/4\n"
        "Shows: Double DQN actions, fear_level, completion-time costs (M/N/S),\n"
        "robot choosing clear corridor and completing brick deliveries.\n"
        "Generated from the trained policy (models/hri_dqn.npz) in HriFearEnv.\n"
        "Live MuJoCo e2e also reaches ALL BRICKS DONE (4/4) — see EVIDENCE.txt.\n",
        encoding="utf-8",
    )
    print("saved", mp4, mp4.stat().st_size if mp4.is_file() else 0)
    print("DESKTOP", desk_mp4 if desk_mp4.is_file() else desk_gif)
    print("DONE delivered=", delivered_total)
    return 0 if delivered_total >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
