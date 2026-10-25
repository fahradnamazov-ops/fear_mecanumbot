"""Tabular Q-learning for HriFearEnv — includes learned route actions."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fear_mecanumbot.constants import (
    ACTION_NAMES,
    FEAR_MAX,
    N_ACTIONS,
    SAFE_DISTANCE_M,
    TASK_ACTIONS,
)
from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.scenario import person_lateral_bin


def discretize(obs: np.ndarray, info: dict) -> int:
    """fear(4) x range(4) x brick(2) x goal_near(2) x person_lat(3) = 192 states."""
    fear = float(info.get("fear_level", obs[10] * FEAR_MAX))
    min_range = float(info.get("min_range", obs[11] * 4.0))
    has_brick = 1 if info.get("has_brick", obs[8] > 0.5) else 0
    if "target_dist_m" in info:
        d_tgt = float(info["target_dist_m"])
    else:
        robot = (float(obs[0]) * 3.5 - 1.7, float(obs[1]) * 3.5 - 1.4)
        brick = (float(obs[4]) * 3.5 - 1.7, float(obs[5]) * 3.5 - 1.4)
        goal = (float(obs[6]) * 3.5 - 1.7, float(obs[7]) * 3.5 - 1.4)
        target = goal if has_brick else brick
        d_tgt = float(np.hypot(robot[0] - target[0], robot[1] - target[1]))
    near_goal = 1 if d_tgt < 1.2 else 0
    lat = int(info.get("person_lat", 1))
    lat = max(0, min(2, lat))

    if fear < 15:
        fi = 0
    elif fear < 35:
        fi = 1
    elif fear < 60:
        fi = 2
    else:
        fi = 3

    if min_range < 0.35:
        ri = 0
    elif min_range < SAFE_DISTANCE_M:
        ri = 1
    elif min_range < 2.2:
        ri = 2
    else:
        ri = 3

    return (((fi * 4 + ri) * 2 + has_brick) * 2 + near_goal) * 3 + lat


N_STATES = 192


class QAgent:
    def __init__(self, n_states: int = N_STATES, n_actions: int = N_ACTIONS, seed: int = 0) -> None:
        self.n_states = n_states
        self.n_actions = n_actions
        self.rng = np.random.default_rng(seed)
        self.q = np.zeros((n_states, n_actions), dtype=np.float64)

    def act(self, state: int, epsilon: float) -> int:
        if self.rng.random() < epsilon:
            return int(self.rng.integers(0, self.n_actions))
        return int(np.argmax(self.q[state]))

    def update(
        self,
        state: int,
        action: int,
        reward: float,
        next_state: int,
        done: bool,
        *,
        alpha: float = 0.2,
        gamma: float = 0.97,
    ) -> None:
        target = reward if done else reward + gamma * float(np.max(self.q[next_state]))
        self.q[state, action] += alpha * (target - self.q[state, action])

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, self.q)

    @classmethod
    def load(cls, path: str | Path, seed: int = 0) -> QAgent:
        agent = cls(seed=seed)
        agent.q = np.load(path)
        if agent.q.shape != (N_STATES, N_ACTIONS):
            raise ValueError(
                "Q shape %s, expected (%d, %d)" % (agent.q.shape, N_STATES, N_ACTIONS)
            )
        return agent


def train(
    episodes: int = 12000,
    max_steps: int = 180,
    seed: int = 0,
    epsilon_start: float = 1.0,
    epsilon_end: float = 0.05,
) -> tuple[QAgent, list[float]]:
    env = HriFearEnv(max_steps=max_steps)
    agent = QAgent(seed=seed)
    returns: list[float] = []
    for ep in range(episodes):
        frac = ep / max(1, episodes - 1)
        epsilon = epsilon_start + (epsilon_end - epsilon_start) * frac
        obs, info = env.reset(seed=seed + ep)
        state = discretize(obs, info)
        total = 0.0
        for _ in range(max_steps):
            action = agent.act(state, epsilon)
            obs, reward, terminated, truncated, info = env.step(action)
            next_state = discretize(obs, info)
            done = terminated or truncated
            agent.update(state, action, reward, next_state, done)
            total += reward
            state = next_state
            if done:
                break
        returns.append(total)
    return agent, returns


def evaluate(
    agent: QAgent,
    episodes: int = 100,
    max_steps: int = 180,
    seed: int = 50_000,
) -> dict:
    env = HriFearEnv(max_steps=max_steps)
    delivered = 0
    collisions = 0.0
    steps_sum = 0.0
    rets = 0.0
    counts = {name: 0 for name in ACTION_NAMES.values()}
    for ep in range(episodes):
        obs, info = env.reset(seed=seed + ep)
        state = discretize(obs, info)
        total = 0.0
        for t in range(max_steps):
            action = int(np.argmax(agent.q[state]))
            counts[ACTION_NAMES[action]] = counts.get(ACTION_NAMES[action], 0) + 1
            obs, reward, terminated, truncated, info = env.step(action)
            total += reward
            state = discretize(obs, info)
            if terminated or truncated:
                break
        rets += total
        steps_sum += info["step"]
        collisions += info["near_collisions"]
        if info["delivered"]:
            delivered += 1
    return {
        "delivery_rate": delivered / episodes,
        "avg_return": rets / episodes,
        "avg_collisions": collisions / episodes,
        "avg_steps": steps_sum / episodes,
        **counts,
        # Aggregate task routes for legacy readers
        "task": sum(counts.get(ACTION_NAMES[a], 0) for a in TASK_ACTIONS),
    }
