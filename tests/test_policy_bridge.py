from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.fear_hri_bt import Blackboard
from fear_mecanumbot.policy import action_name, tick_with_heuristic
from fear_mecanumbot.ros_bridge import FEAR_HRI_ACTIONS, bridge_checklist
from fear_mecanumbot.constants import ACTION_AVOID, ACTION_FREEZE


def test_action_name_mapping():
    assert action_name(ACTION_FREEZE) == "freeze"
    assert action_name(ACTION_AVOID) == "avoid"


def test_tick_with_heuristic_avoid_when_close():
    bb = Blackboard(
        fear_level=50.0,
        risk=0.6,
        min_lidar_range=0.6,
        robot_pose=(0.0, 0.0, 0.0),
        person_pose=(0.5, 0.0),
        brick_pose=(2.0, 0.0),
    )
    status = tick_with_heuristic(bb)
    assert bb.selected_action == "avoid"
    assert status.value in {"SUCCESS", "RUNNING", "FAILURE"}


def test_env_still_steps():
    env = HriFearEnv(max_steps=10)
    obs, info = env.reset(seed=0)
    assert obs.shape == (13,)
    assert "fear_level" in info


def test_bridge_lists_nav2():
    assert any("navigate_to_pose" in a.name for a in FEAR_HRI_ACTIONS)
    assert len(bridge_checklist()) >= 5
