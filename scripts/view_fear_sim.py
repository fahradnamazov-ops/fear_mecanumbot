#!/usr/bin/env python3
"""Top-down visual Fear HRI simulation (no ROS).

Shows robot, person patrol from fear_hri_brick_carry, bricks/mats, and a live
fear meter. Saves output/fear_sim_preview.gif and shows a window if a display
is available.

  python scripts/view_fear_sim.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, PillowWriter
import yaml

from fear_mecanumbot.constants import (
    FEAR_DECAY_PER_STEP,
    FEAR_RISE_PER_RISK,
    FEAR_SPIKE_ON_EVENT,
    HIT_DISTANCE_M,
    SAFE_DISTANCE_M,
)
from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.risk import compute_risk, is_near_collision

SCENARIO_CANDIDATES = [
    ROOT.parent / "mecanumbot_remote" / "mecanumbot_sim" / "config" / "sim_scenarios" / "fear_hri_brick_carry.yaml",
    ROOT / "sim_draft" / "fear_hri_brick_carry.yaml",
]
ROBOT_XY = (-0.20, -0.20)
DT = 0.2
SPEED = 0.30
DURATION = 76.0


def load_scenario() -> dict:
    for path in SCENARIO_CANDIDATES:
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["_path"] = str(path)
            return data
    raise FileNotFoundError("fear_hri_brick_carry.yaml not found")


def waypoints(data: dict) -> list[tuple[float, float, float]]:
    actors = data.get("scenario", data).get("actors", [])
    human = next(a for a in actors if a.get("kind") == "human")
    return [
        (float(w["x"]), float(w["y"]), float(w.get("pause", 0.0)))
        for w in human["motion"]["waypoints"]
    ]


def interpolate_patrol(wps, t: float) -> tuple[float, float]:
    times: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    clock = 0.0
    n = len(wps)
    for i in range(n):
        x0, y0, pause = wps[i]
        x1, y1, _ = wps[(i + 1) % n]
        dist = math.hypot(x1 - x0, y1 - y0)
        move_t = dist / SPEED if SPEED > 0 else 0.0
        times.append(clock)
        xs.append(x0)
        ys.append(y0)
        clock += move_t
        times.append(clock)
        xs.append(x1)
        ys.append(y1)
        if pause > 0:
            clock += pause
            times.append(clock)
            xs.append(x1)
            ys.append(y1)
    period = clock if clock > 0 else 1.0
    tau = t % period
    for i in range(len(times) - 1):
        if times[i] <= tau <= times[i + 1]:
            span = times[i + 1] - times[i]
            if span <= 1e-9:
                return xs[i + 1], ys[i + 1]
            u = (tau - times[i]) / span
            return xs[i] + u * (xs[i + 1] - xs[i]), ys[i] + u * (ys[i + 1] - ys[i])
    return xs[-1], ys[-1]


def select_action(fear: float, min_range: float, risk: float) -> str:
    if min_range <= HIT_DISTANCE_M + 0.05 or (fear >= 70.0 and min_range < SAFE_DISTANCE_M):
        return "freeze"
    if fear >= 40.0 or risk >= 0.5:
        return "avoid"
    if 25.0 <= fear < 40.0:
        return "catch_attention"
    return "task"


def props_from_scenario(data: dict) -> list[dict]:
    return list(data.get("scenario", data).get("props", []))


def main() -> int:
    data = load_scenario()
    wps = waypoints(data)
    props = props_from_scenario(data)
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    gif_path = out_dir / "fear_sim_preview.gif"

    times = []
    person_xy = []
    ranges = []
    fears = []
    actions = []
    fear = FearState()
    prev_r = 10.0
    t = 0.0
    while t <= DURATION:
        px, py = interpolate_patrol(wps, t)
        r = math.hypot(px - ROBOT_XY[0], py - ROBOT_XY[1])
        closing = max(0.0, (prev_r - r) / DT)
        risk = compute_risk(min_range=r, closing_speed=closing)
        update_fear_level(
            fear,
            risk=risk,
            spike_event=is_near_collision(r),
            spike=FEAR_SPIKE_ON_EVENT,
            rise_per_risk=FEAR_RISE_PER_RISK,
            decay=FEAR_DECAY_PER_STEP,
            dt=DT,
        )
        action = select_action(fear.level, r, risk)
        times.append(t)
        person_xy.append((px, py))
        ranges.append(r)
        fears.append(fear.level)
        actions.append(action)
        prev_r = r
        t += DT

    fig, (ax_map, ax_fear) = plt.subplots(
        1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1.35, 1.0]}
    )
    fig.suptitle("Fear HRI — fear_hri_brick_carry (preview)", fontsize=12)

    ax_map.set_xlim(-2.2, 2.2)
    ax_map.set_ylim(-2.2, 2.2)
    ax_map.set_aspect("equal")
    ax_map.set_xlabel("x (m)")
    ax_map.set_ylabel("y (m)")
    ax_map.grid(True, alpha=0.3)
    ax_map.set_title("Top-down scene")

    # Arena walls (from MJCF approx)
    ax_map.add_patch(patches.Rectangle((-2.05, -2.05), 4.1, 4.1, fill=False, lw=2, color="#333"))
    for name, color in (("box_obstacle_a", "#2ca02c"), ("box_obstacle_b", "#ff7f0e")):
        # approximate positions from MJCF
        pass
    ax_map.add_patch(patches.Rectangle((0.72, 0.22), 0.36, 0.36, color="#2ca02c", alpha=0.5))
    ax_map.add_patch(patches.Rectangle((-0.82, -1.05), 0.24, 0.5, color="#ff7f0e", alpha=0.5))

    for prop in props:
        pose = prop["pose"]
        kind = prop.get("kind", "")
        size = prop.get("size", 0.2)
        if isinstance(size, list):
            w, h = float(size[0]), float(size[1])
        else:
            w = h = float(size)
        color = {"mat": "#2a9d8f", "cube": "#b35c3a"}.get(kind, "#888")
        if kind == "mat":
            # size is full width/height in scenario
            ax_map.add_patch(
                patches.Rectangle(
                    (pose["x"] - w / 2, pose["y"] - h / 2),
                    w,
                    h,
                    color=color,
                    alpha=0.35,
                    label=prop.get("name"),
                )
            )
        else:
            ax_map.add_patch(
                patches.Rectangle(
                    (pose["x"] - w / 2, pose["y"] - h / 2),
                    w,
                    h,
                    color=color,
                    alpha=0.9,
                )
            )

    robot_dot, = ax_map.plot([ROBOT_XY[0]], [ROBOT_XY[1]], "s", color="#1f77b4", ms=12, label="robot")
    person_dot, = ax_map.plot([0], [0], "o", color="#d62728", ms=12, label="person")
    link_line, = ax_map.plot([], [], "--", color="#555", lw=1)
    safe_circle = patches.Circle(ROBOT_XY, SAFE_DISTANCE_M, fill=False, ls=":", color="#2ca02c", label="safe 1.0 m")
    hit_circle = patches.Circle(ROBOT_XY, HIT_DISTANCE_M, fill=False, ls="--", color="#d62728", label="hit 0.25 m")
    ax_map.add_patch(safe_circle)
    ax_map.add_patch(hit_circle)
    status_text = ax_map.text(
        0.02, 0.98, "", transform=ax_map.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    ax_map.legend(loc="lower right", fontsize=8)

    ax_fear.set_xlim(0, DURATION)
    ax_fear.set_ylim(0, 105)
    ax_fear.set_xlabel("time (s)")
    ax_fear.set_ylabel("fear_level")
    ax_fear.set_title("Fear over time")
    ax_fear.axhline(70, color="#d62728", ls=":", alpha=0.6, label="freeze thr")
    ax_fear.axhline(40, color="#ff7f0e", ls=":", alpha=0.6, label="avoid thr")
    fear_line, = ax_fear.plot([], [], color="#9467bd", lw=2, label="fear")
    ax_fear.legend(loc="upper right", fontsize=8)
    fear_fill = None

    def update(frame: int):
        px, py = person_xy[frame]
        person_dot.set_data([px], [py])
        link_line.set_data([ROBOT_XY[0], px], [ROBOT_XY[1], py])
        status_text.set_text(
            f"t={times[frame]:5.1f}s\n"
            f"range={ranges[frame]:.2f} m\n"
            f"fear={fears[frame]:.1f}\n"
            f"action={actions[frame]}"
        )
        fear_line.set_data(times[: frame + 1], fears[: frame + 1])
        return person_dot, link_line, status_text, fear_line

    # Subsample frames for a smaller GIF
    step = 2
    frames = list(range(0, len(times), step))
    anim = FuncAnimation(fig, update, frames=frames, interval=80, blit=False)

    print(f"Saving {gif_path} ...")
    anim.save(str(gif_path), writer=PillowWriter(fps=12))
    print(f"Saved: {gif_path}")
    print("Opening window (close it when done)...")
    plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
