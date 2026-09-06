"""One-step Fear HRI update: risk → fear → reward extras."""

from __future__ import annotations

from dataclasses import dataclass

from fear_mecanumbot.constants import ACTION_TASK
from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.reward import compute_reward
from fear_mecanumbot.risk import compute_risk, is_near_collision


@dataclass
class HriStepResult:
    risk: float
    near_collision: bool
    fear_level: float
    previous_fear_level: float
    reward: float


def hri_step(
    fear_state: FearState,
    *,
    min_range: float,
    closing_speed: float = 0.0,
    exploration_delta: float = 0.0,
    action_id: int = ACTION_TASK,
    wall_collision: bool = False,
    safe_distance: float | None = None,
    hit_distance: float | None = None,
) -> HriStepResult:
    """One step: LIDAR risk / near-collision → fear_level → reward."""
    from fear_mecanumbot.constants import HIT_DISTANCE_M, SAFE_DISTANCE_M

    safe = SAFE_DISTANCE_M if safe_distance is None else safe_distance
    hit = HIT_DISTANCE_M if hit_distance is None else hit_distance

    previous = fear_state.level
    risk = compute_risk(
        min_range=min_range,
        safe_distance=safe,
        hit_distance=hit,
        closing_speed=closing_speed,
    )
    near = is_near_collision(min_range, hit_distance=hit)
    update_fear_level(fear_state, risk=risk, spike_event=near)
    reward = compute_reward(
        exploration_delta=exploration_delta,
        fear_level=fear_state.level,
        previous_fear_level=previous,
        action_id=action_id,
        near_collision=near,
        wall_collision=wall_collision,
    )
    return HriStepResult(
        risk=risk,
        near_collision=near,
        fear_level=fear_state.level,
        previous_fear_level=previous,
        reward=reward,
    )
