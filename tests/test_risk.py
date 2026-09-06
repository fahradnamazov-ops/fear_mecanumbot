"""Tests for HRI risk signal."""

from fear_mecanumbot.risk import compute_risk, is_near_collision


def test_far_away_is_zero_risk():
    assert compute_risk(min_range=3.0, safe_distance=1.0) == 0.0


def test_at_hit_distance_is_full_risk():
    assert compute_risk(min_range=0.25, hit_distance=0.25) == 1.0


def test_mid_range_is_partial_risk():
    risk = compute_risk(min_range=0.625, safe_distance=1.0, hit_distance=0.25)
    assert abs(risk - 0.5) < 1e-6


def test_closing_speed_increases_risk():
    base = compute_risk(min_range=0.8, safe_distance=1.0, hit_distance=0.25, closing_speed=0.0)
    faster = compute_risk(min_range=0.8, safe_distance=1.0, hit_distance=0.25, closing_speed=1.0)
    assert faster > base


def test_near_collision_flag():
    assert is_near_collision(0.2, hit_distance=0.25) is True
    assert is_near_collision(0.5, hit_distance=0.25) is False
