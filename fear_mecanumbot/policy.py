"""Map learned or heuristic actions onto Fear HRI leaves."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fear_mecanumbot.constants import ACTION_NAMES, ACTION_TASK
from fear_mecanumbot.fear_hri_bt import Blackboard, Status, tick_fear_hri_policy
from fear_mecanumbot.qlearn import QAgent, discretize
from fear_mecanumbot.scenario import heuristic_action


def action_name(action_id: int) -> str:
    return ACTION_NAMES.get(int(action_id), ACTION_NAMES[ACTION_TASK])


def tick_with_heuristic(bb: Blackboard) -> Status:
    aid = heuristic_action(bb.fear_level, bb.min_lidar_range, bb.risk)
    return tick_fear_hri_policy(bb, action=action_name(aid))


def tick_with_q(
    bb: Blackboard,
    agent: QAgent,
    obs: np.ndarray,
    info: dict,
) -> Status:
    state = discretize(obs, info)
    aid = agent.act(state, epsilon=0.0)
    return tick_fear_hri_policy(bb, action=action_name(aid))


def load_default_agent(root: Path | None = None) -> QAgent | None:
    root = root or Path(__file__).resolve().parents[1]
    path = root / "models" / "hri_q.npy"
    if not path.exists():
        return None
    return QAgent.load(path)
