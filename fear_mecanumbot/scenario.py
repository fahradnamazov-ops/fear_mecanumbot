"""2D Fear HRI world: brick, goal, moving person."""

from __future__ import annotations

from dataclasses import dataclass
import math

from fear_mecanumbot.constants import (
    ACTION_AVOID,
    ACTION_CATCH_ATTENTION,
    ACTION_FREEZE,
    ACTION_TASK,
    HIT_DISTANCE_M,
    SAFE_DISTANCE_M,
)
from fear_mecanumbot.fear_dynamics import FearState
from fear_mecanumbot.risk import compute_risk, is_near_collision


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit_toward(src: tuple[float, float], dst: tuple[float, float]) -> tuple[float, float]:
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return (0.0, 0.0)
    return (dx / n, dy / n)


@dataclass
class ScenarioState:
    robot: tuple[float, float]
    person: tuple[float, float]
    brick: tuple[float, float]
    goal: tuple[float, float]
    has_brick: bool = False
    delivered: bool = False
    fear: FearState | None = None
    prev_person: tuple[float, float] | None = None
    freeze_ticks: int = 0
    avoid_ticks: int = 0
    catch_attention_ticks: int = 0
    task_ticks: int = 0
    near_collisions: int = 0
    picked: bool = False
    step: int = 0


def person_path(step: int, closest: float = 0.22) -> tuple[float, float]:
    """Cut across the brick/goal corridor, linger, then leave."""
    start = (3.2, 2.6)
    linger = (1.15, 1.25)
    end = (3.5, 3.1)
    if step < 16:
        t = step / 16.0
        return (
            start[0] + (linger[0] - start[0]) * t,
            start[1] + (linger[1] - start[1]) * t,
        )
    if step < 48:
        # exercise near linger; briefly closer, then back out
        radius = 0.18 if 28 <= step < 36 else max(closest, 0.42)
        ang = step * 0.4
        return (
            linger[0] + radius * math.cos(ang),
            linger[1] + radius * math.sin(ang),
        )
    t = min(1.0, (step - 48) / 22.0)
    return (
        linger[0] + (end[0] - linger[0]) * t,
        linger[1] + (end[1] - linger[1]) * t,
    )


def heuristic_action(fear_level: float, min_range: float, risk: float) -> int:
    """Fixed rule baseline for comparison with Q-learning."""
    if min_range <= HIT_DISTANCE_M + 0.05 or (fear_level >= 70.0 and min_range < SAFE_DISTANCE_M):
        return ACTION_FREEZE
    if risk >= 0.5 or (fear_level >= 40.0 and min_range < SAFE_DISTANCE_M):
        return ACTION_AVOID
    if 20.0 <= fear_level < 40.0 and min_range < 2.0:
        return ACTION_CATCH_ATTENTION
    return ACTION_TASK


def apply_action(state: ScenarioState, action: int, *, speed: float = 0.22) -> tuple[bool, bool]:
    """Move robot. Returns (just_picked, just_delivered)."""
    if state.fear is None:
        state.fear = FearState()
    just_picked = False
    just_delivered = False

    if action == ACTION_FREEZE:
        state.freeze_ticks += 1
        return False, False

    if action == ACTION_CATCH_ATTENTION:
        state.catch_attention_ticks += 1
        return False, False

    if action == ACTION_AVOID:
        state.avoid_ticks += 1
        ux, uy = unit_toward(state.person, state.robot)
        state.robot = (state.robot[0] + speed * ux, state.robot[1] + speed * uy)
        return False, False

    state.task_ticks += 1
    if state.delivered:
        return False, False

    target = state.goal if state.has_brick else state.brick
    caution = 1.0 - 0.45 * (state.fear.level / 100.0)
    step_speed = speed * max(0.4, caution)
    ux, uy = unit_toward(state.robot, target)
    state.robot = (state.robot[0] + step_speed * ux, state.robot[1] + step_speed * uy)

    if not state.has_brick and not state.delivered and dist(state.robot, state.brick) < 0.28:
        state.has_brick = True
        state.picked = True
        just_picked = True
    if state.has_brick and dist(state.robot, state.goal) < 0.32:
        state.delivered = True
        state.has_brick = False
        just_delivered = True
    return just_picked, just_delivered


def sense(state: ScenarioState, dt: float = 1.0) -> tuple[float, float, bool]:
    min_range = dist(state.robot, state.person)
    closing = 0.0
    if state.prev_person is not None:
        closing = max(0.0, dist(state.prev_person, state.robot) - min_range) / dt
    risk = compute_risk(min_range=min_range, closing_speed=closing)
    near = is_near_collision(min_range)
    return min_range, risk, near
