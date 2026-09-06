r"""
Preview fear updates from simulated LaserScan ranges (no ROS).

  python scripts/scan_fear_preview.py

Uses the same math as the local env; on robot the Fear HRI node reads /mecanumbot/scan.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.risk import compute_risk, is_near_collision
from fear_mecanumbot.sensing import closing_speed_from_ranges, min_range_from_lidar_sectors


def main() -> None:
    # Simulated forward scan: person approaches then leaves (ranges in metres)
    profile = [3.0] * 5 + [2.0, 1.5, 1.0, 0.7, 0.5, 0.5, 0.5, 0.8, 1.5, 2.0, 2.5] + [3.0] * 8
    fear = FearState(level=0.0)
    prev_range = profile[0]
    dt = 0.125  # ~8 Hz scan

    print("step  scan_min  risk   fear   event")
    for step, ranges_val in enumerate(profile):
        # Fake 5-beam scan with closest at centre
        ranges = [ranges_val + 0.5, ranges_val, ranges_val + 0.3, ranges_val + 1.0, ranges_val + 1.2]
        lidar_min = min_range_from_lidar_sectors(
            ranges, angle_min=-0.5, angle_increment=0.25, fov_rad=1.0
        )
        closing = closing_speed_from_ranges(prev_range, lidar_min, dt)
        risk = compute_risk(min_range=lidar_min, closing_speed=closing)
        near = is_near_collision(lidar_min)
        update_fear_level(fear, risk=risk, spike_event=near)
        event = "SPIKE" if near else ""
        print(f"{step:4d}  {lidar_min:7.2f}  {risk:4.2f}  {fear.level:5.1f}  {event}")
        prev_range = lidar_min

    print("\nNext: run this logic in sim via fear_hri_bt_node on /mecanumbot/scan")


if __name__ == "__main__":
    main()
