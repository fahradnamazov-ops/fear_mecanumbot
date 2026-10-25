"""Tests for Double DQN Fear HRI policy."""

import numpy as np

from fear_mecanumbot.constants import N_ACTIONS
from fear_mecanumbot.dqn import DQNAgent, N_FEATURES, evaluate, features_from_info, train
from fear_mecanumbot.env import HriFearEnv


def test_features_shape():
    env = HriFearEnv(max_steps=20)
    obs, info = env.reset(seed=0)
    feat = features_from_info(obs, info)
    assert feat.shape == (N_FEATURES,)


def test_short_dqn_train(tmp_path):
    agent, returns = train(episodes=40, max_steps=40, seed=1, mask_catch=True)
    assert len(returns) == 40
    path = tmp_path / "hri_dqn.npz"
    agent.save(path)
    loaded = DQNAgent.load(path)
    q = loaded.q_values(np.zeros(N_FEATURES, dtype=np.float32))
    assert q.shape == (N_ACTIONS,)
    stats = evaluate(loaded, episodes=4, max_steps=40, seed=200)
    assert 0.0 <= stats["delivery_rate"] <= 1.0


def test_act_masks_catch():
    agent = DQNAgent(seed=0)
    # Bias catch head high
    agent.online.b3[2] = 50.0
    feat = np.zeros(N_FEATURES, dtype=np.float32)
    a_on = agent.act(feat, epsilon=0.0, mask_catch=False)
    a_off = agent.act(feat, epsilon=0.0, mask_catch=True)
    assert a_on == 2
    assert a_off != 2
