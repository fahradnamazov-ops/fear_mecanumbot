#!/usr/bin/env python3
"""Validate Csenge completion-time cost: travel + wait.

Long clear way must be cheaper than short blocked way when wait dominates.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.route_cost import all_route_costs, cheapest_route, completion_time_s


def main() -> int:
    robot = (-1.35, -0.20)
    target = (1.35, -0.20)

    print("=== Person ON middle corridor ===")
    person_block = (0.0, -0.20)
    costs = all_route_costs(robot, target, person_block)
    for name in ("middle", "north", "south"):
        tot, travel, wait = costs[name]
        print(f"  {name:7s} total={tot:6.2f}s  travel={travel:5.2f}s  wait={wait:5.2f}s")
    best = cheapest_route(robot, target, person_block)
    print(f"  cheapest → {best}")
    if best == "middle":
        print("FAIL: middle should not win while person blocks it")
        return 1
    if costs["middle"][0] <= costs[best][0]:
        print("FAIL: middle total not higher than cheapest side")
        return 1

    print("=== Person CLEAR (north-east) ===")
    person_clear = (1.05, 1.05)
    costs2 = all_route_costs(robot, target, person_clear)
    for name in ("middle", "north", "south"):
        tot, travel, wait = costs2[name]
        print(f"  {name:7s} total={tot:6.2f}s  travel={travel:5.2f}s  wait={wait:5.2f}s")
    best2 = cheapest_route(robot, target, person_clear)
    print(f"  cheapest → {best2}")
    if best2 != "middle":
        print("FAIL: middle should win when clear")
        return 1

    print("=== Person ON north lane ===")
    person_north = (0.0, 0.90)
    costs3 = all_route_costs(robot, target, person_north)
    for name in ("middle", "north", "south"):
        tot, travel, wait = costs3[name]
        print(f"  {name:7s} total={tot:6.2f}s  travel={travel:5.2f}s  wait={wait:5.2f}s")
    best3 = cheapest_route(robot, target, person_north)
    print(f"  cheapest → {best3}")
    if best3 == "north":
        print("FAIL: north must not win while person stands on north lane")
        return 1

    print("PASS: completion-time cost ordering (long clear cheap / short blocked expensive)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
