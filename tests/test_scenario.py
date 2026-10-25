"""Tests for scenario helpers and heuristic baseline."""

from fear_mecanumbot.constants import ACTION_CATCH_ATTENTION, ACTION_FREEZE
from fear_mecanumbot.scenario import person_path, heuristic_action


def test_person_blocks_then_clears_corridor():
    # On-mat block phase stays near corridor centre
    assert abs(person_path(5)[0]) < 0.25
    # Clear window moves north-east past the green box
    assert person_path(60)[0] > 0.8
    assert person_path(60)[1] > 0.5
    # Loop returns toward the mat
    assert abs(person_path(74)[0]) < 0.6


def test_high_fear_near_person_selects_freeze():
    assert heuristic_action(fear_level=80.0, min_range=0.8, risk=0.2) == ACTION_FREEZE


def test_mid_fear_selects_catch_attention():
    assert heuristic_action(fear_level=30.0, min_range=1.5, risk=0.1) == ACTION_CATCH_ATTENTION
