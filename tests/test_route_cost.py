"""Completion-time cost: long clear cheap, short blocked expensive."""

from fear_mecanumbot.constants import ACTION_TASK_MIDDLE, ACTION_TASK_NORTH
from fear_mecanumbot.route_cost import (
    all_route_costs,
    cheapest_route,
    completion_time_s,
    reward_from_completion_cost,
)


def test_blocked_middle_more_expensive_than_north():
    robot = (-1.3, -0.2)
    target = (1.3, -0.2)
    person = (0.0, -0.2)  # on middle
    mid = completion_time_s("middle", robot, target, person)
    north = completion_time_s("north", robot, target, person)
    assert mid[2] > north[2], (mid, north)  # wait dominates on middle
    assert mid[0] > north[0], (mid, north)  # total: short+wait > long+clear
    assert cheapest_route(robot, target, person) in ("north", "south")


def test_clear_middle_cheaper_than_side():
    robot = (-1.3, -0.2)
    target = (1.3, -0.2)
    person = (1.0, 1.0)  # off corridor
    mid = completion_time_s("middle", robot, target, person)
    north = completion_time_s("north", robot, target, person)
    assert mid[1] < north[1]  # shorter travel
    assert mid[2] <= 0.5
    assert cheapest_route(robot, target, person) == "middle"


def test_reward_prefers_cheapest():
    robot = (-1.3, -0.2)
    target = (1.3, -0.2)
    person = (0.0, -0.2)
    r_mid, _ = reward_from_completion_cost(ACTION_TASK_MIDDLE, robot, target, person)
    r_n, info = reward_from_completion_cost(ACTION_TASK_NORTH, robot, target, person)
    assert info["cost_best"] in ("north", "south")
    assert r_n > r_mid


def test_person_on_north_makes_north_expensive():
    robot = (-1.3, -0.2)
    target = (1.3, -0.2)
    person = (0.0, 0.90)  # on fixed north lane
    costs = all_route_costs(robot, target, person)
    assert costs["north"][2] > costs["south"][2]
    assert costs["north"][0] > costs["south"][0]
    assert cheapest_route(robot, target, person) != "north"


def test_all_routes_keys():
    costs = all_route_costs((-1.0, 0.0), (1.0, 0.0), (0.0, 0.0))
    assert set(costs) == {"middle", "north", "south"}
