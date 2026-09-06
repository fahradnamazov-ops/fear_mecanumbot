"""Risk signal from proximity / movement (Fear HRI protocol)."""

from __future__ import annotations


def compute_risk(
    *,
    min_range: float,
    safe_distance: float = 1.0,
    hit_distance: float = 0.25,
    closing_speed: float = 0.0,
    speed_scale: float = 0.5,
) -> float:
    """
    Map LIDAR proximity and closing speed to risk in [0, 1].

    - min_range <= hit_distance → risk 1.0
    - min_range >= safe_distance → base risk 0.0 (speed may still add a little)
    - between: linear from 0 → 1 as range shrinks
    - closing_speed > 0 (approaching) adds extra risk, clipped to 1
    """
    if min_range <= hit_distance:
        proximity = 1.0
    elif min_range >= safe_distance:
        proximity = 0.0
    else:
        proximity = (safe_distance - min_range) / (safe_distance - hit_distance)

    speed_term = max(0.0, float(closing_speed)) * speed_scale
    return float(max(0.0, min(1.0, proximity + speed_term)))


def is_near_collision(min_range: float, hit_distance: float = 0.25) -> bool:
    """Discrete aversive event for a fear spike."""
    return float(min_range) <= float(hit_distance)
