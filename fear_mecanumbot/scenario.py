"""2D Fear HRI world aligned with MuJoCo fear_hri_brick_carry layout.

Layout (map frame, same idea as mecanumbot_sim):
  start/bricks west (-1.35, -0.20), goal east (1.35, -0.20),
  person on the centre corridor, furniture:
    box_obstacle_a (green)  ~ (0.9,  0.4)
    box_obstacle_b (orange) ~ (-0.7, -0.8)
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from fear_mecanumbot.constants import (
    ACTION_AVOID,
    ACTION_CATCH_ATTENTION,
    ACTION_FREEZE,
    ACTION_TASK,
    ACTION_TASK_MIDDLE,
    ACTION_TASK_NORTH,
    ACTION_TASK_SOUTH,
    HIT_DISTANCE_M,
    SAFE_DISTANCE_M,
    TASK_ACTIONS,
)
from fear_mecanumbot.fear_dynamics import FearState
from fear_mecanumbot.risk import compute_risk, is_near_collision

# Arena clamp (matches live reactive clamps)
ARENA_X = (-1.65, 1.65)
ARENA_Y = (-1.35, 1.35)

# Furniture centres + approximate half-diagonal clearance (live MuJoCo boxes)
OBSTACLES: tuple[tuple[float, float, float], ...] = (
    (0.9, 0.4, 0.32),  # green box_obstacle_a
    (-0.7, -0.8, 0.30),  # orange box_obstacle_b
)

START_XY = (-1.35, -0.20)
GOAL_XY = (1.35, -0.20)
BRICK_XY = (-1.35, -0.10)


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit_toward(src: tuple[float, float], dst: tuple[float, float]) -> tuple[float, float]:
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    n = math.hypot(dx, dy)
    if n < 1e-6:
        return (0.0, 0.0)
    return (dx / n, dy / n)


def clamp_arena(p: tuple[float, float]) -> tuple[float, float]:
    return (
        max(ARENA_X[0], min(ARENA_X[1], p[0])),
        max(ARENA_Y[0], min(ARENA_Y[1], p[1])),
    )


def obstacle_repulsion(p: tuple[float, float]) -> tuple[float, float]:
    """Soft push away from furniture so avoid/task do not train into pockets."""
    fx = fy = 0.0
    for ox, oy, r in OBSTACLES:
        d = dist(p, (ox, oy))
        if d < 1e-6:
            fx += 1.0
            continue
        if d < r + 0.25:
            push = (r + 0.25 - d) / (r + 0.25)
            ux, uy = unit_toward((ox, oy), p)
            fx += ux * push
            fy += uy * push
    return fx, fy


def hits_obstacle(p: tuple[float, float]) -> bool:
    for ox, oy, r in OBSTACLES:
        if dist(p, (ox, oy)) < r * 0.85:
            return True
    return False


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
    obstacle_hits: int = 0
    picked: bool = False
    step: int = 0
    no_progress_steps: int = 0
    last_target_dist: float = 99.0
    avoid_side: float = 1.0


def person_path(step: int, closest: float = 0.22) -> tuple[float, float]:
    """Patrol the centre corridor like fear_hri_brick_carry (block, linger, clear)."""
    # On mat blocking start→goal line
    block = (0.0, -0.20)
    north = (0.0, 0.15)
    south = (0.0, -0.55)
    # Clear corridor: north-east past green box (open window)
    clear = (1.05, 1.05)

    cycle = step % 75
    if cycle < 18:
        return block
    if cycle < 28:
        return north
    if cycle < 38:
        return south
    if cycle < 44:
        return block
    if cycle < 52:
        t = (cycle - 44) / 8.0
        return (
            block[0] + (clear[0] - block[0]) * t,
            block[1] + (clear[1] - block[1]) * t,
        )
    if cycle < 66:
        # Linger clear — fear should decay; robot should resume task
        return clear
    t = (cycle - 66) / 9.0
    return (
        clear[0] + (block[0] - clear[0]) * t,
        clear[1] + (block[1] - clear[1]) * t,
    )


def heuristic_action(fear_level: float, min_range: float, risk: float) -> int:
    """Fixed rule baseline for comparison with Double DQN."""
    if min_range <= HIT_DISTANCE_M + 0.05 or (
        fear_level >= 70.0 and min_range < SAFE_DISTANCE_M
    ):
        return ACTION_FREEZE
    if risk >= 0.5 or (fear_level >= 40.0 and min_range < SAFE_DISTANCE_M):
        return ACTION_AVOID
    if 20.0 <= fear_level < 40.0 and min_range < 2.0:
        return ACTION_CATCH_ATTENTION
    return ACTION_TASK


def apply_action(state: ScenarioState, action: int, *, speed: float = 0.22) -> tuple[bool, bool]:
    """Move robot. Avoid = pause delivery and retreat from person (free space)."""
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
        # Pure retreat from person + tangential free-space + obstacle push
        ax, ay = unit_toward(state.person, state.robot)
        left = (-ay, ax)
        right = (ay, -ax)
        rx, ry = state.robot
        cand_l = (rx + left[0], ry + left[1])
        cand_r = (rx + right[0], ry + right[1])
        score_l = dist(cand_l, state.person) - (
            1.0 if hits_obstacle(cand_l) else 0.0
        )
        score_r = dist(cand_r, state.person) - (
            1.0 if hits_obstacle(cand_r) else 0.0
        )
        tx, ty = left if score_l >= score_r else right
        ox, oy = obstacle_repulsion(state.robot)
        wx = ax * speed * 0.80 + tx * speed * 0.50 + ox * speed * 0.70
        wy = ay * speed * 0.80 + ty * speed * 0.50 + oy * speed * 0.70
        state.robot = clamp_arena((rx + wx, ry + wy))
        if hits_obstacle(state.robot):
            state.obstacle_hits += 1
            # Bounce toward centre
            state.robot = clamp_arena((rx * 0.7, ry * 0.7))
        return False, False

    state.task_ticks += 1
    if state.delivered:
        return False, False

    target = state.goal if state.has_brick else state.brick
    # Fear does not throttle speed — RL picks freeze/avoid/task instead.
    step_speed = speed
    ux, uy = unit_toward(state.robot, target)
    # Fixed arena corridors (same as live completion_cost / brick_carry)
    route_y = 0.0
    if action == ACTION_TASK_NORTH:
        route_y = 0.90
    elif action == ACTION_TASK_SOUTH:
        route_y = -0.90
    if action in TASK_ACTIONS and abs(route_y) > 1e-3:
        mid_x = 0.5 * (state.robot[0] + target[0])
        via = (mid_x, route_y)
        vx, vy = unit_toward(state.robot, via)
        if (target[0] - state.robot[0]) * (state.robot[0] - state.person[0]) > 0 and abs(
            state.robot[0] - state.person[0]
        ) > 0.7:
            ux, uy = unit_toward(state.robot, target)
        else:
            ux = 0.55 * vx + 0.45 * ux
            uy = 0.55 * vy + 0.45 * uy
            n = math.hypot(ux, uy) or 1.0
            ux, uy = ux / n, uy / n

    ox, oy = obstacle_repulsion(state.robot)
    wx = ux * step_speed + ox * step_speed * 0.55
    wy = uy * step_speed + oy * step_speed * 0.55
    pd = dist(state.robot, state.person)
    # Stay clear of human on EVERY task corridor (not only middle)
    if pd < SAFE_DISTANCE_M and action in TASK_ACTIONS:
        lx, ly = -(state.person[1] - state.robot[1]), (state.person[0] - state.robot[0])
        n = math.hypot(lx, ly) or 1.0
        push = (SAFE_DISTANCE_M - pd) / SAFE_DISTANCE_M
        wx += (lx / n) * step_speed * 0.75 * push
        wy += (ly / n) * step_speed * 0.75 * push
        # Also back off along person→robot
        away_x = state.robot[0] - state.person[0]
        away_y = state.robot[1] - state.person[1]
        an = math.hypot(away_x, away_y) or 1.0
        wx += (away_x / an) * step_speed * 0.55 * push
        wy += (away_y / an) * step_speed * 0.55 * push

    nxt = clamp_arena((state.robot[0] + wx, state.robot[1] + wy))
    if hits_obstacle(nxt):
        state.obstacle_hits += 1
        nxt = clamp_arena(
            (
                state.robot[0] + ox * step_speed + ux * step_speed * 0.2,
                state.robot[1] + oy * step_speed + uy * step_speed * 0.2,
            )
        )
    state.robot = nxt

    d_tgt = dist(state.robot, target)
    if d_tgt < state.last_target_dist - 0.02:
        state.no_progress_steps = 0
        state.last_target_dist = d_tgt
    else:
        state.no_progress_steps += 1

    if not state.has_brick and not state.delivered and dist(state.robot, state.brick) < 0.28:
        state.has_brick = True
        state.picked = True
        just_picked = True
        state.last_target_dist = dist(state.robot, state.goal)
        state.no_progress_steps = 0
    if state.has_brick and dist(state.robot, state.goal) < 0.32:
        state.delivered = True
        state.has_brick = False
        just_delivered = True
    return just_picked, just_delivered


def person_blocks_middle(state: ScenarioState, band: float = 0.55) -> bool:
    """True if person sits on the start↔goal corridor (for RL route reward)."""
    target = state.goal if state.has_brick else state.brick
    rx, ry = state.robot
    tx, ty = target
    px, py = state.person
    mid_y = 0.5 * (ry + ty)
    lo, hi = (rx, tx) if rx <= tx else (tx, rx)
    return lo - 0.1 <= px <= hi + 0.1 and abs(py - mid_y) < band


def person_lateral_bin(state: ScenarioState) -> int:
    """0=person south of path, 1=on middle, 2=person north — RL state feature."""
    target = state.goal if state.has_brick else state.brick
    mid_y = 0.5 * (state.robot[1] + target[1])
    dy = state.person[1] - mid_y
    if abs(dy) < 0.45:
        return 1
    return 2 if dy > 0 else 0


def sense(state: ScenarioState, dt: float = 1.0) -> tuple[float, float, bool]:
    min_range = dist(state.robot, state.person)
    closing = 0.0
    if state.prev_person is not None:
        closing = max(0.0, dist(state.prev_person, state.robot) - min_range) / dt
    risk = compute_risk(min_range=min_range, closing_speed=closing)
    near = is_near_collision(min_range)
    return min_range, risk, near
