"""Reward terms for Fear HRI V1."""

from __future__ import annotations

from fear_mecanumbot.constants import (
    ACTION_FREEZE,
    REWARD_FEAR_PENALTY_ALPHA,
    REWARD_FEAR_REDUCTION_BONUS,
    REWARD_NEAR_COLLISION_PENALTY,
    REWARD_WALL_COLLISION,
)


def compute_reward(
    *,
    exploration_delta: float,
    fear_level: float,
    previous_fear_level: float,
    action_id: int,
    near_collision: bool = False,
    wall_collision: bool = False,
    alpha: float = REWARD_FEAR_PENALTY_ALPHA,
) -> float:
    """Task progress, fear costs, near-collision penalty, recovery bonus."""
    reward = exploration_delta

    moving_while_scared = action_id != ACTION_FREEZE and fear_level > 0.0
    if moving_while_scared:
        reward -= alpha * fear_level

    if near_collision:
        reward += REWARD_NEAR_COLLISION_PENALTY

    if fear_level < previous_fear_level:
        reward += REWARD_FEAR_REDUCTION_BONUS

    if wall_collision:
        reward += REWARD_WALL_COLLISION

    return reward
