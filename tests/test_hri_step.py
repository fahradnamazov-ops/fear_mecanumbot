"""Tests for combined HRI step helper."""

from fear_mecanumbot.constants import ACTION_FREEZE, ACTION_TASK
from fear_mecanumbot.fear_dynamics import FearState
from fear_mecanumbot.hri_step import hri_step


def test_far_away_keeps_fear_low():
    state = FearState(level=0.0)
    result = hri_step(state, min_range=3.0, action_id=ACTION_TASK)
    assert result.risk == 0.0
    assert result.near_collision is False
    assert result.fear_level == 0.0


def test_close_range_raises_fear():
    state = FearState(level=0.0)
    result = hri_step(state, min_range=0.5, closing_speed=0.5, action_id=ACTION_FREEZE)
    assert result.risk > 0.0
    assert result.fear_level > 0.0


def test_hit_distance_is_near_collision():
    state = FearState(level=0.0)
    result = hri_step(state, min_range=0.2, action_id=ACTION_FREEZE)
    assert result.near_collision is True
    assert result.reward <= -10.0
