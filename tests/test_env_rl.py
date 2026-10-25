"""Tests for the HRI Gym env and Q-learning."""

import numpy as np

from fear_mecanumbot.constants import ACTION_TASK, N_ACTIONS
from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.qlearn import QAgent, discretize, evaluate, train


def test_reset_obs_shape():
    env = HriFearEnv(max_steps=30)
    obs, info = env.reset(seed=0)
    assert obs.shape == (13,)
    assert "fear_level" in info


def test_step_changes_state():
    env = HriFearEnv(max_steps=30)
    env.reset(seed=1)
    obs, reward, terminated, truncated, info = env.step(ACTION_TASK)
    assert obs.shape == (13,)
    assert isinstance(reward, float)
    assert terminated in (True, False)
    assert truncated in (True, False)
    assert info["step"] == 1


def test_episode_stops_on_delivery_or_limit():
    env = HriFearEnv(max_steps=120)
    env.reset(seed=2)
    done = False
    delivered = False
    for _ in range(120):
        _obs, _r, terminated, truncated, info = env.step(ACTION_TASK)
        if info["delivered"]:
            delivered = True
        if terminated or truncated:
            done = True
            if terminated and delivered:
                assert info["delivered"] is True
            break
    assert done is True


def test_q_update_changes_table():
    agent = QAgent(seed=0)
    before = agent.q.copy()
    agent.update(0, 3, 10.0, 1, False)
    assert not np.allclose(agent.q, before)


def test_short_train_runs():
    agent, returns = train(episodes=80, max_steps=50, seed=0)
    assert agent.q.shape == (192, N_ACTIONS)
    assert len(returns) == 80
    stats = evaluate(agent, episodes=8, max_steps=50, seed=100)
    assert 0.0 <= stats["delivery_rate"] <= 1.0
