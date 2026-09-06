"""Tests for ROS-oriented range fusion helpers."""

import math

from fear_mecanumbot.sensing import (
    avoid_retreat_distance_m,
    closing_speed_from_ranges,
    fused_min_range,
    min_range_from_lidar_sectors,
)


def test_min_range_from_forward_sectors():
    # 3 beams: left, center, right — center is closest
    ranges = [2.0, 0.6, 2.0]
    assert min_range_from_lidar_sectors(ranges, angle_min=-0.2, angle_increment=0.2) == 0.6


def test_closing_speed_positive_when_approaching():
    assert closing_speed_from_ranges(2.0, 1.0, dt=1.0) == 1.0
    assert closing_speed_from_ranges(1.0, 2.0, dt=1.0) == 0.0


def test_fusion_uses_person_when_lidar_blind():
    r, src = fused_min_range(lidar_min=3.0, person_range=0.9, person_visible_to_lidar=False)
    assert r == 0.9
    assert src == "fusion"


def test_fusion_takes_minimum_when_both_see_person():
    r, src = fused_min_range(lidar_min=1.2, person_range=0.8, person_visible_to_lidar=True)
    assert math.isclose(r, 0.8)
    assert src in {"fusion", "both"}


def test_retreat_distance_grows_with_fear():
    assert avoid_retreat_distance_m(0.0) < avoid_retreat_distance_m(80.0)
