#!/usr/bin/env python3
"""Activate Fear HRI on the fear_hri_brick_carry scenario geometry (no ROS).

Replays the person patrol waypoints from the shipped scenario YAML, computes
range to a fixed robot pose on the brick-carry line, updates fear_level, and
prints the selected action each step. Use this to verify activation before
(or without) a full MuJoCo / Gazebo bring-up.

  python scripts/sim_fear_activate_demo.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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

# Prefer team-synced scenario; fall back to draft path.
SCENARIO_CANDIDATES = [
    ROOT.parent / "mecanumbot_remote" / "mecanumbot_sim" / "config" / "sim_scenarios" / "fear_hri_brick_carry.yaml",
    ROOT / "sim_draft" / "fear_hri_brick_carry.yaml",
]

# Robot on the carry line just west of the mat centre so person approach
# enters hit / avoid ranges (matches the "person blocks corridor" layout).
ROBOT_XY = (-0.20, -0.20)
DT = 0.2  # seconds per demo step
SPEED = 0.30  # matches scenario patrol speed (m/s)


def load_scenario() -> dict:
    for path in SCENARIO_CANDIDATES:
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["_path"] = str(path)
            return data
    raise FileNotFoundError("fear_hri_brick_carry.yaml not found")


def waypoints_from_scenario(data: dict) -> list[tuple[float, float, float]]:
    """Return (x, y, pause_s) list from the subject human actor."""
    actors = data.get("scenario", data).get("actors", [])
    human = next(a for a in actors if a.get("kind") == "human")
    out: list[tuple[float, float, float]] = []
    for wp in human["motion"]["waypoints"]:
        out.append((float(wp["x"]), float(wp["y"]), float(wp.get("pause", 0.0))))
    return out


def interpolate_patrol(
    waypoints: list[tuple[float, float, float]],
    t: float,
) -> tuple[float, float]:
    """Dead-reckon position along waypoints with pauses (looping)."""
    if not waypoints:
        return 0.0, 0.0
    # Build segment timeline: move then pause at each waypoint.
    segments: list[tuple[float, float, float, float, float, float]] = []
    # each: (t0, t1, x0, y0, x1, y1) for moves; pauses as zero-length moves
    times: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    clock = 0.0
    n = len(waypoints)
    for i in range(n):
        x0, y0, pause = waypoints[i]
        x1, y1, _ = waypoints[(i + 1) % n]
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


def main() -> int:
    data = load_scenario()
    wps = waypoints_from_scenario(data)
    fear = FearState(level=0.0)
    prev_range = 10.0

    print("Fear HRI activation demo (scenario geometry)")
    print(f"scenario: {data['_path']}")
    print(f"robot at ({ROBOT_XY[0]:.2f}, {ROBOT_XY[1]:.2f})")
    print(f"{'t':>6} {'range':>7} {'risk':>6} {'fear':>6} {'action':>16}")
    print("-" * 50)

    duration = 90.0
    t = 0.0
    while t <= duration:
        px, py = interpolate_patrol(wps, t)
        min_range = math.hypot(px - ROBOT_XY[0], py - ROBOT_XY[1])
        closing = max(0.0, (prev_range - min_range) / DT)
        risk = compute_risk(
            min_range=min_range,
            safe_distance=SAFE_DISTANCE_M,
            hit_distance=HIT_DISTANCE_M,
            closing_speed=closing,
        )
        spike = is_near_collision(min_range, HIT_DISTANCE_M)
        update_fear_level(
            fear,
            risk=risk,
            spike_event=spike,
            spike=FEAR_SPIKE_ON_EVENT,
            rise_per_risk=FEAR_RISE_PER_RISK,
            decay=FEAR_DECAY_PER_STEP,
            dt=DT,
        )
        action = select_action(fear.level, min_range, risk)
        if int(t / DT) % 5 == 0:
            print(
                f"{t:6.1f} {min_range:7.2f} {risk:6.2f} {fear.level:6.1f} {action:>16}"
            )
        prev_range = min_range
        t += DT

    print("-" * 50)
    print("Done. Fear activated on fear_hri_brick_carry geometry.")
    print("Next (lab Linux / ROS 2 Humble workspace):")
    print(
        "  ros2 launch mecanumbot_bringup sim.launch.py "
        "mode:=behaviour condition:=none scenario:=fear_hri_brick_carry"
    )
    print("  ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
