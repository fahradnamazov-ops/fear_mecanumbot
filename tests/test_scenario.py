"""Tests for scenario helpers and heuristic baseline."""

from fear_mecanumbot.constants import ACTION_CATCH_ATTENTION, ACTION_FREEZE
from fear_mecanumbot.scenario import heuristic_action, person_path


def test_person_approaches_then_leaves():
    assert person_path(0)[0] > person_path(20)[0]
    assert person_path(80)[0] > person_path(50)[0]


def test_high_fear_near_person_selects_freeze():
    assert heuristic_action(fear_level=80.0, min_range=0.8, risk=0.2) == ACTION_FREEZE


def test_mid_fear_selects_catch_attention():
    assert heuristic_action(fear_level=30.0, min_range=1.5, risk=0.1) == ACTION_CATCH_ATTENTION
