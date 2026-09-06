"""Fear HRI behaviour-tree leaf stubs (no ROS dependency)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fear_mecanumbot.constants import ACTION_NAMES
from fear_mecanumbot.scenario import unit_toward
from fear_mecanumbot.sensing import avoid_retreat_distance_m


class Status(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


@dataclass
class Blackboard:
    fear_level: float = 0.0
    risk: float = 0.0
    min_lidar_range: float = 10.0
    has_brick: bool = False
    brick_pose: tuple[float, float] | None = None
    goal_pose: tuple[float, float] | None = None
    robot_pose: tuple[float, float, float] | None = None
    person_pose: tuple[float, float] | None = None
    selected_action: str = "task"
    cmd_vel: tuple[float, float, float] = (0.0, 0.0, 0.0)
    catch_attention_active: bool = False
    nav_goal: tuple[float, float] | None = None
    nav_cancel: bool = False
    avoid_distance_m: float = 1.2
    notes: dict[str, Any] = field(default_factory=dict)


class Leaf:
    name: str = "leaf"

    def tick(self, bb: Blackboard) -> Status:
        raise NotImplementedError


class FreezeLeaf(Leaf):
    """Cancel Nav2 and stop wheels (SmoothTurner / zero Twist)."""

    name = "freeze"

    def tick(self, bb: Blackboard) -> Status:
        bb.cmd_vel = (0.0, 0.0, 0.0)
        bb.nav_cancel = True
        bb.nav_goal = None
        bb.selected_action = self.name
        bb.notes["ros_port"] = "cancel NavigateToPose; zero Twist"
        return Status.SUCCESS


class AvoidLeaf(Leaf):
    """Retreat pose for Nav2 Approach."""

    name = "avoid"

    def tick(self, bb: Blackboard) -> Status:
        if bb.robot_pose is None or bb.person_pose is None:
            bb.selected_action = self.name
            bb.notes["ros_port"] = "Approach retreat (need robot + person pose)"
            return Status.FAILURE
        robot_xy = (bb.robot_pose[0], bb.robot_pose[1])
        ux, uy = unit_toward(bb.person_pose, robot_xy)
        if ux == 0.0 and uy == 0.0:
            ux, uy = 1.0, 0.0
        d = avoid_retreat_distance_m(bb.fear_level, base=bb.avoid_distance_m * 0.6)
        bb.avoid_distance_m = d
        bb.nav_goal = (robot_xy[0] + d * ux, robot_xy[1] + d * uy)
        bb.nav_cancel = False
        bb.selected_action = self.name
        bb.notes["ros_port"] = "Approach / navigate_to_pose (retreat away from person)"
        return Status.RUNNING


class CatchAttentionLeaf(Leaf):
    """Make the human look at the robot."""

    name = "catch_attention"

    def tick(self, bb: Blackboard) -> Status:
        bb.catch_attention_active = True
        bb.nav_cancel = True
        bb.selected_action = self.name
        bb.notes["ros_port"] = "DogBehaviourSequence(catch_attention) + RelativeTurnPattern"
        return Status.SUCCESS


class TaskGoToBrickLeaf(Leaf):
    name = "go_to_brick"

    def tick(self, bb: Blackboard) -> Status:
        if bb.brick_pose is None:
            return Status.FAILURE
        bb.selected_action = self.name
        bb.nav_goal = bb.brick_pose
        bb.nav_cancel = False
        bb.notes["ros_port"] = "Approach / navigate_to_pose"
        return Status.RUNNING


class TaskGrabBrickLeaf(Leaf):
    name = "grab_brick"

    def tick(self, bb: Blackboard) -> Status:
        bb.has_brick = True
        bb.selected_action = self.name
        return Status.SUCCESS


class TaskGoToGoalLeaf(Leaf):
    name = "go_to_goal"

    def tick(self, bb: Blackboard) -> Status:
        if bb.goal_pose is None:
            return Status.FAILURE
        bb.selected_action = self.name
        bb.nav_goal = bb.goal_pose
        bb.nav_cancel = False
        bb.notes["ros_port"] = "Approach / navigate_to_pose"
        return Status.RUNNING


class TaskReleaseBrickLeaf(Leaf):
    name = "release_brick"

    def tick(self, bb: Blackboard) -> Status:
        bb.has_brick = False
        bb.selected_action = self.name
        return Status.SUCCESS


def select_action_from_fear(bb: Blackboard) -> str:
    if bb.fear_level >= 70.0 or bb.min_lidar_range <= 0.35:
        return ACTION_NAMES[0]
    if bb.fear_level >= 40.0 or bb.risk >= 0.5:
        return ACTION_NAMES[1]
    if 25.0 <= bb.fear_level < 40.0:
        return ACTION_NAMES[2]
    return ACTION_NAMES[3]


def tick_fear_hri_policy(bb: Blackboard, action: str | None = None) -> Status:
    chosen = action if action is not None else select_action_from_fear(bb)
    leaves: dict[str, Leaf] = {
        "freeze": FreezeLeaf(),
        "avoid": AvoidLeaf(),
        "catch_attention": CatchAttentionLeaf(),
        "task": TaskGoToBrickLeaf() if not bb.has_brick else TaskGoToGoalLeaf(),
        "go_to_brick": TaskGoToBrickLeaf(),
        "go_to_goal": TaskGoToGoalLeaf(),
    }
    leaf = leaves.get(chosen, leaves["task"])
    return leaf.tick(bb)


def retreat_pose(
    robot: tuple[float, float],
    person: tuple[float, float],
    distance_m: float = 1.2,
) -> tuple[float, float]:
    """Nav2 retreat target used by AvoidLeaf."""
    ux, uy = unit_toward(person, robot)
    if ux == 0.0 and uy == 0.0:
        ux, uy = 1.0, 0.0
    return (robot[0] + distance_m * ux, robot[1] + distance_m * uy)