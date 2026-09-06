"""Tabular Q-learning for HriFearEnv."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fear_mecanumbot.constants import FEAR_MAX, N_ACTIONS, SAFE_DISTANCE_M
from fear_mecanumbot.env import HriFearEnv


def discretize(obs: np.ndarray, info: dict) -> int:
    """fear(4) x range(4) x brick(2) x goal_near(2) = 64 states."""
    fear = float(info.get("fear_level", obs[10] * FEAR_MAX))
    min_range = float(info.get("min_range", obs[11] * 4.0))
    has_brick = 1 if info.get("has_brick", obs[8] > 0.5) else 0
    robot = (float(obs[0]) * 5.0, float(obs[1]) * 5.0)
    brick = (float(obs[4]) * 5.0, float(obs[5]) * 5.0)
    goal = (float(obs[6]) * 5.0, float(obs[7]) * 5.0)
    target = goal if has_brick else brick
    d_tgt = float(np.hypot(robot[0] - target[0], robot[1] - target[1]))
    near_goal = 1 if d_tgt < 1.2 else 0

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

    return ((fi * 4 + ri) * 2 + has_brick) * 2 + near_goal


N_STATES = 64


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
        return agent


def train(
    episodes: int = 6000,
    max_steps: int = 120,
    seed: int = 0,
    epsilon_start: float = 1.0,
    epsilon_end: float = 0.08,
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


def evaluate(agent: QAgent, episodes: int = 50, max_steps: int = 120, seed: int = 10_000) -> dict:
    env = HriFearEnv(max_steps=max_steps)
    delivered = 0
    collisions = 0
    returns = []
    freeze = avoid = catch = task = 0
    steps_sum = 0
    for ep in range(episodes):
        obs, info = env.reset(seed=seed + ep)
        state = discretize(obs, info)
        total = 0.0
        for t in range(max_steps):
            action = agent.act(state, epsilon=0.0)
            if action == 0:
                freeze += 1
            elif action == 1:
                avoid += 1
            elif action == 2:
                catch += 1
            else:
                task += 1
            obs, reward, terminated, truncated, info = env.step(action)
            total += reward
            state = discretize(obs, info)
            if terminated or truncated:
                steps_sum += t + 1
                if info["delivered"]:
                    delivered += 1
                collisions += info["near_collisions"]
                break
        returns.append(total)
    n = max(1, episodes)
    return {
        "episodes": episodes,
        "delivery_rate": delivered / n,
        "avg_return": float(np.mean(returns)),
        "avg_collisions": collisions / n,
        "avg_steps": steps_sum / n,
        "freeze": freeze,
        "avoid": avoid,
        "catch_attention": catch,
        "task": task,
    }
