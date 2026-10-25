"""Completion-time route cost (Csenge) — training + eval.

Cost = travel_time + wait_time. Prefer long clear over short blocked.
Implementation shared with live ROS package when available; local copy otherwise.
"""

from __future__ import annotations

try:
    # Prefer live package copy so train/sim stay identical
    from mecanumbot_fear_hri_behaviour.behaviours.completion_cost import (  # type: ignore
        CRUISE_MPS,
        PERSON_CLEAR_M,
        WAIT_FULL_S,
        all_route_costs,
        cheapest_route,
        completion_time_s,
        normalized_cost_features,
        path_length_m,
        person_on_middle_corridor,
        wait_time_s,
    )
except ImportError:  # pragma: no cover - offline train without ROS package
    from fear_mecanumbot._completion_cost_local import (  # type: ignore
        CRUISE_MPS,
        PERSON_CLEAR_M,
        WAIT_FULL_S,
        all_route_costs,
        cheapest_route,
        completion_time_s,
        normalized_cost_features,
        path_length_m,
        person_on_middle_corridor,
        wait_time_s,
    )

from fear_mecanumbot.constants import (
    ACTION_AVOID,
    ACTION_CATCH_ATTENTION,
    ACTION_FREEZE,
    ACTION_TASK_MIDDLE,
    ACTION_TASK_NORTH,
    ACTION_TASK_SOUTH,
    TASK_ACTIONS,
)


def action_to_route_name(action: int) -> str | None:
    if action == ACTION_TASK_MIDDLE:
        return "middle"
    if action == ACTION_TASK_NORTH:
        return "north"
    if action == ACTION_TASK_SOUTH:
        return "south"
    return None


def reward_from_completion_cost(
    action: int,
    robot: tuple[float, float],
    target: tuple[float, float],
    person: tuple[float, float],
    *,
    scale: float = 0.12,
) -> tuple[float, dict]:
    """Shaped reward so RL finishes ASAP while avoiding the person.

    - Lower completion time (travel+wait) → higher reward
    - Bonus for picking the cheapest corridor
    - Penalty for freeze/avoid when a clear cheap middle exists
    """
    costs = all_route_costs(robot, target, person)
    best = min(costs, key=lambda n: costs[n][0])
    best_total = costs[best][0]
    route = action_to_route_name(action)
    info = {
        "cost_middle": costs["middle"][0],
        "cost_north": costs["north"][0],
        "cost_south": costs["south"][0],
        "cost_best": best,
        "travel_middle": costs["middle"][1],
        "wait_middle": costs["middle"][2],
        "travel_north": costs["north"][1],
        "wait_north": costs["north"][2],
        "travel_south": costs["south"][1],
        "wait_south": costs["south"][2],
    }

    if route is not None:
        total, travel, wait = costs[route]
        r = -scale * total
        if route == best:
            r += 0.28
        else:
            r -= scale * 0.55 * (total - best_total)
        # Extra penalty for choosing a human-blocked lane
        if wait >= 8.0:
            r -= 0.35
        info.update(
            {"chosen_route": route, "chosen_travel": travel, "chosen_wait": wait}
        )
        return r, info

    if action in (ACTION_FREEZE, ACTION_AVOID, ACTION_CATCH_ATTENTION):
        if best == "middle" and costs["middle"][2] < 1.0:
            r = -0.55  # stalling while clear middle is free
        else:
            r = -0.08
        info["chosen_route"] = "wait"
        return r, info

    return 0.0, info


__all__ = [
    "CRUISE_MPS",
    "PERSON_CLEAR_M",
    "WAIT_FULL_S",
    "all_route_costs",
    "cheapest_route",
    "completion_time_s",
    "normalized_cost_features",
    "path_length_m",
    "person_on_middle_corridor",
    "reward_from_completion_cost",
    "wait_time_s",
    "action_to_route_name",
]
