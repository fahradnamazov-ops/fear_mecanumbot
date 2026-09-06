"""Tests for fear level dynamics (HRI risk / near-collision spike)."""

from fear_mecanumbot.fear_dynamics import FearState, update_fear_level


def test_fear_spikes_on_near_collision():
    state = FearState(level=10.0)
    update_fear_level(state, spike_event=True)
    assert state.level == 60.0
    assert state.time_since_event == 0.0


def test_fear_caps_at_maximum():
    state = FearState(level=80.0)
    update_fear_level(state, spike_event=True)
    assert state.level == 100.0


def test_fear_decays_when_calm():
    state = FearState(level=50.0, time_since_event=0.0)
    update_fear_level(state)
    assert state.level == 49.8
    assert state.time_since_event == 1.0


def test_fear_reaches_zero_after_many_steps():
    state = FearState(level=10.0)
    for _ in range(100):
        update_fear_level(state)
    assert state.level == 0.0


def test_repeated_spikes_accumulate_fear():
    state = FearState(level=0.0)
    update_fear_level(state, spike_event=True)
    update_fear_level(state, spike_event=True)
    assert state.level == 100.0


def test_continuous_risk_raises_fear_without_spike():
    state = FearState(level=0.0)
    update_fear_level(state, risk=1.0)
    assert abs(state.level - 4.8) < 1e-6


def test_residual_fear_after_risk_ends():
    state = FearState(level=0.0)
    for _ in range(10):
        update_fear_level(state, risk=1.0)
    level_after_risk = state.level
    assert level_after_risk > 20.0

    for _ in range(5):
        update_fear_level(state, risk=0.0)

    assert state.level < level_after_risk
    assert state.level > level_after_risk - 2.0
