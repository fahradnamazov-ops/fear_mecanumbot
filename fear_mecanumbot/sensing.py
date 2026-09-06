"""Range sensing helpers: local geometry now, ROS scan + people fusion on robot."""

from __future__ import annotations

import math
from typing import Sequence


def min_range_from_lidar_sectors(
    ranges: Sequence[float],
    *,
    angle_min: float,
    angle_increment: float,
    fov_rad: float | None = None,
    min_valid: float = 0.05,
    max_valid: float = 30.0,
) -> float:
    """Minimum valid LaserScan range inside the forward field of view."""
    if not ranges:
        return max_valid
    half = (fov_rad or math.pi) / 2.0
    best = max_valid
    for i, raw in enumerate(ranges):
        r = float(raw)
        if not min_valid <= r <= max_valid:
            continue
        angle = angle_min + i * angle_increment
        if abs(angle) <= half:
            best = min(best, r)
    return best


def closing_speed_from_ranges(prev_range: float, curr_range: float, dt: float) -> float:
    """Positive when the obstacle got closer (approaching)."""
    if dt <= 0.0:
        return 0.0
    return max(0.0, (float(prev_range) - float(curr_range)) / dt)


def person_distance(robot_xy: tuple[float, float], person_xy: tuple[float, float]) -> float:
    return math.hypot(robot_xy[0] - person_xy[0], robot_xy[1] - person_xy[1])


def fused_min_range(
    *,
    lidar_min: float,
    person_range: float | None,
    person_visible_to_lidar: bool = True,
) -> tuple[float, str]:
    """
    Combine LIDAR and people_fusion.

    When the robot turns away, LIDAR may miss the person; fusion keeps awareness.
    Returns (min_range, source) with source in {'lidar', 'fusion', 'both'}.
    """
    if person_range is None or not math.isfinite(person_range):
        return lidar_min, "lidar"
    if not person_visible_to_lidar and person_range < lidar_min:
        return person_range, "fusion"
    fused = min(lidar_min, person_range)
    if fused == lidar_min == person_range:
        return fused, "both"
    if fused == lidar_min:
        return fused, "lidar"
    return fused, "fusion"


def avoid_retreat_distance_m(fear_level: float, *, base: float = 0.8, scale: float = 0.01) -> float:
    """Nav2 Approach retreat distance grows with fear (dynamic avoidance, not fixed inflation)."""
    return base + scale * max(0.0, min(100.0, float(fear_level)))
