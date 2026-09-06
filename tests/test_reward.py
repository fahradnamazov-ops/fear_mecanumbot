"""Tests for Fear HRI reward function."""

from fear_mecanumbot.constants import ACTION_FREEZE, ACTION_TASK, REWARD_NEAR_COLLISION_PENALTY
from fear_mecanumbot.reward import compute_reward


def test_exploration_progress_gives_positive_reward():
    reward = compute_reward(
        exploration_delta=0.5,
        fear_level=0.0,
        previous_fear_level=0.0,
        action_id=ACTION_TASK,
    )
    assert reward == 0.5


def test_near_collision_applies_large_penalty():
    reward = compute_reward(
        exploration_delta=0.0,
        fear_level=50.0,
        previous_fear_level=0.0,
        near_collision=True,
        action_id=ACTION_FREEZE,
    )
    assert reward == REWARD_NEAR_COLLISION_PENALTY


def test_moving_while_scared_is_penalised():
    reward = compute_reward(
        exploration_delta=0.0,
        fear_level=50.0,
        previous_fear_level=50.0,
        action_id=ACTION_TASK,
    )
    assert reward == -0.5


def test_freeze_while_scared_avoids_movement_penalty():
    reward = compute_reward(
        exploration_delta=0.0,
        fear_level=50.0,
        previous_fear_level=50.0,
        action_id=ACTION_FREEZE,
    )
    assert reward == 0.0


def test_fear_reduction_gives_bonus():
    reward = compute_reward(
        exploration_delta=0.0,
        fear_level=40.0,
        previous_fear_level=50.0,
        action_id=ACTION_FREEZE,
    )
    assert abs(reward - 0.05) < 1e-9
