"""Tests for vendored fear_logic in ros_draft (import without ROS build)."""

import importlib.util
from pathlib import Path

LOGIC = (
    Path(__file__).resolve().parents[1]
    / "ros_draft"
    / "mecanumbot_fear_hri_behaviour"
    / "mecanumbot_fear_hri_behaviour"
    / "behaviours"
    / "fear_logic.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("fear_logic_draft", LOGIC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_select_action_freeze_when_hit():
    fl = _load()
    assert fl.select_action(
        fear_level=10.0,
        min_range=0.24,
        risk=1.0,
        hit_distance=0.25,
        safe_distance=1.0,
        freeze_threshold=70.0,
        avoid_threshold=40.0,
        catch_low=25.0,
        catch_high=40.0,
    ) == "freeze"


def test_fear_spike_and_decay():
    fl = _load()
    fear = fl.update_fear_level(0.0, risk=0.0, spike_event=True, spike_on_event=50.0)
    assert fear == 50.0
    fear = fl.update_fear_level(fear, risk=0.0, spike_event=False, decay_per_step=0.2)
    assert fear == 49.8


def test_retreat_distance_scales():
    fl = _load()
    assert fl.avoid_retreat_distance_m(0.0) < fl.avoid_retreat_distance_m(80.0)
