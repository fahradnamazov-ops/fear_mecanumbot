"""Tests for Fear HRI behaviour-tree leaf stubs."""

from fear_mecanumbot.fear_hri_bt import (
    AvoidLeaf,
    Blackboard,
    CatchAttentionLeaf,
    FreezeLeaf,
    Status,
    retreat_pose,
    select_action_from_fear,
    tick_fear_hri_policy,
)


def test_freeze_zeros_cmd_vel():
    bb = Blackboard()
    status = FreezeLeaf().tick(bb)
    assert status == Status.SUCCESS
    assert bb.cmd_vel == (0.0, 0.0, 0.0)
    assert bb.nav_cancel is True


def test_catch_attention_sets_flag():
    bb = Blackboard()
    status = CatchAttentionLeaf().tick(bb)
    assert status == Status.SUCCESS
    assert bb.catch_attention_active is True


def test_avoid_sets_nav2_retreat_goal():
    bb = Blackboard(
        robot_pose=(0.0, 0.0, 0.0),
        person_pose=(1.0, 0.0),
        avoid_distance_m=1.0,
    )
    status = AvoidLeaf().tick(bb)
    assert status == Status.RUNNING
    assert bb.nav_goal is not None
    assert bb.nav_goal[0] < 0.0
    assert "navigate_to_pose" in bb.notes["ros_port"]


def test_retreat_pose_moves_away_from_person():
    goal = retreat_pose((0.0, 0.0), (2.0, 0.0), distance_m=1.0)
    assert goal[0] < 0.0


def test_selector_freeze_when_fear_high():
    bb = Blackboard(fear_level=80.0)
    assert select_action_from_fear(bb) == "freeze"


def test_selector_task_when_calm():
    bb = Blackboard(fear_level=0.0, risk=0.0, min_lidar_range=3.0)
    assert select_action_from_fear(bb) == "task_middle"


def test_policy_tick_runs():
    bb = Blackboard(fear_level=50.0, risk=0.6, brick_pose=(1.0, 1.0), robot_pose=(0.0, 0.0, 0.0), person_pose=(0.5, 0.0))
    status = tick_fear_hri_policy(bb)
    assert status in {Status.SUCCESS, Status.RUNNING, Status.FAILURE}
    assert bb.selected_action in {
        "freeze",
        "avoid",
        "catch_attention",
        "task",
        "task_middle",
        "task_north",
        "task_south",
        "go_to_brick",
        "go_to_goal",
    }
