"""Fear HRI V1 package for the Mecanumbot project.

Provides continuous fear dynamics, proximity risk, reward terms,
a Gymnasium brick-carry environment, and Double DQN (+ legacy Q) utilities.
"""

from fear_mecanumbot.constants import ACTION_NAMES
from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.hri_step import HriStepResult, hri_step
from fear_mecanumbot.reward import compute_reward
from fear_mecanumbot.risk import compute_risk, is_near_collision
from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.dqn import DQNAgent
from fear_mecanumbot.qlearn import QAgent
from fear_mecanumbot.policy import action_name, load_default_agent

__all__ = [
    "ACTION_NAMES",
    "FearState",
    "HriStepResult",
    "update_fear_level",
    "hri_step",
    "compute_reward",
    "compute_risk",
    "is_near_collision",
    "HriFearEnv",
    "DQNAgent",
    "QAgent",
    "action_name",
    "load_default_agent",
]

__version__ = "1.1.0"
