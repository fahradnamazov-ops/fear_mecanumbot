"""Double DQN (numpy MLP) for Fear HRI — continuous state, 6 discrete actions.

Better than tabular Q: no hand-binned states; learns freeze/avoid/catch/routes
from continuous fear, range, person offset, and target distance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fear_mecanumbot.constants import (
    ACTION_CATCH_ATTENTION,
    ACTION_NAMES,
    FEAR_MAX,
    N_ACTIONS,
    TASK_ACTIONS,
)
from fear_mecanumbot.env import HriFearEnv

N_FEATURES = 10
HIDDEN = 64


def features_from_info(obs: np.ndarray, info: dict) -> np.ndarray:
    """Continuous features + relative completion-time costs (middle/north/south)."""
    from fear_mecanumbot.route_cost import normalized_cost_features

    fear = float(info.get("fear_level", float(obs[10]) * FEAR_MAX))
    min_range = float(info.get("min_range", float(obs[11]) * 4.0))
    has_brick = 1.0 if info.get("has_brick", float(obs[8]) > 0.5) else 0.0
    target_dist = float(info.get("target_dist_m", 2.0))
    risk = float(info.get("risk", float(obs[12])))
    c_m = c_n = c_s = 0.5
    if obs is not None and len(obs) >= 8:
        rx = float(obs[0]) * 3.5 - 1.7
        ry = float(obs[1]) * 3.5 - 1.4
        px = float(obs[2]) * 3.5 - 1.7
        py = float(obs[3]) * 3.5 - 1.4
        bx = float(obs[4]) * 3.5 - 1.7
        by = float(obs[5]) * 3.5 - 1.4
        gx = float(obs[6]) * 3.5 - 1.7
        gy = float(obs[7]) * 3.5 - 1.4
        tx, ty = (gx, gy) if has_brick > 0.5 else (bx, by)
        person_dx = float(np.clip((px - rx) / 3.0, -1.0, 1.0))
        person_dy = float(np.clip((py - ry) / 2.0, -1.0, 1.0))
        c_m, c_n, c_s = normalized_cost_features((rx, ry), (tx, ty), (px, py))
    else:
        person_dx = 0.0
        person_dy = 0.0

    return np.array(
        [
            fear / FEAR_MAX,
            min(min_range / 4.0, 1.0),
            has_brick,
            min(target_dist / 4.0, 1.0),
            person_dy,
            person_dx,
            min(max(risk, 0.0), 1.0),
            float(c_m),
            float(c_n),
            float(c_s),
        ],
        dtype=np.float32,
    )


def features_live(
    *,
    fear_level: float,
    min_range: float,
    has_brick: bool,
    target_dist_m: float,
    person_dx: float,
    person_dy: float,
    risk: float = 0.0,
    cost_middle: float = 0.5,
    cost_north: float = 0.5,
    cost_south: float = 0.5,
) -> np.ndarray:
    return np.array(
        [
            float(fear_level) / FEAR_MAX,
            min(float(min_range) / 4.0, 1.0),
            1.0 if has_brick else 0.0,
            min(float(target_dist_m) / 4.0, 1.0),
            float(np.clip(person_dy / 2.0, -1.0, 1.0)),
            float(np.clip(person_dx / 3.0, -1.0, 1.0)),
            min(max(float(risk), 0.0), 1.0),
            float(np.clip(cost_middle, 0.0, 1.0)),
            float(np.clip(cost_north, 0.0, 1.0)),
            float(np.clip(cost_south, 0.0, 1.0)),
        ],
        dtype=np.float32,
    )


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


@dataclass
class MLPWeights:
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray
    w3: np.ndarray
    b3: np.ndarray

    def copy(self) -> "MLPWeights":
        return MLPWeights(
            self.w1.copy(),
            self.b1.copy(),
            self.w2.copy(),
            self.b2.copy(),
            self.w3.copy(),
            self.b3.copy(),
        )


def _init_mlp(rng: np.random.Generator, n_in: int = N_FEATURES, n_out: int = N_ACTIONS) -> MLPWeights:
    def he(fan_in: int, fan_out: int) -> np.ndarray:
        return rng.normal(0.0, np.sqrt(2.0 / fan_in), size=(fan_in, fan_out)).astype(np.float32)

    return MLPWeights(
        w1=he(n_in, HIDDEN),
        b1=np.zeros(HIDDEN, dtype=np.float32),
        w2=he(HIDDEN, HIDDEN),
        b2=np.zeros(HIDDEN, dtype=np.float32),
        w3=rng.normal(0.0, 0.01, size=(HIDDEN, n_out)).astype(np.float32),
        b3=np.zeros(n_out, dtype=np.float32),
    )


def mlp_forward(w: MLPWeights, x: np.ndarray) -> tuple[np.ndarray, dict]:
    """x: (B, F) → q: (B, A). Cache activations for backprop."""
    z1 = x @ w.w1 + w.b1
    h1 = _relu(z1)
    z2 = h1 @ w.w2 + w.b2
    h2 = _relu(z2)
    q = h2 @ w.w3 + w.b3
    return q, {"x": x, "h1": h1, "h2": h2}


def mlp_backward(
    w: MLPWeights,
    cache: dict,
    d_q: np.ndarray,
) -> dict[str, np.ndarray]:
    """Gradients for MSE on Q heads. d_q: (B, A)."""
    h2 = cache["h2"]
    h1 = cache["h1"]
    x = cache["x"]
    dw3 = h2.T @ d_q
    db3 = d_q.sum(axis=0)
    dh2 = d_q @ w.w3.T
    dz2 = dh2 * (h2 > 0)
    dw2 = h1.T @ dz2
    db2 = dz2.sum(axis=0)
    dh1 = dz2 @ w.w2.T
    dz1 = dh1 * (h1 > 0)
    dw1 = x.T @ dz1
    db1 = dz1.sum(axis=0)
    return {
        "w1": dw1,
        "b1": db1,
        "w2": dw2,
        "b2": db2,
        "w3": dw3,
        "b3": db3,
    }


class ReplayBuffer:
    def __init__(self, capacity: int, n_feat: int = N_FEATURES) -> None:
        self.capacity = capacity
        self.s = np.zeros((capacity, n_feat), dtype=np.float32)
        self.a = np.zeros(capacity, dtype=np.int32)
        self.r = np.zeros(capacity, dtype=np.float32)
        self.ns = np.zeros((capacity, n_feat), dtype=np.float32)
        self.d = np.zeros(capacity, dtype=np.float32)
        self.i = 0
        self.n = 0

    def add(self, s: np.ndarray, a: int, r: float, ns: np.ndarray, done: bool) -> None:
        i = self.i % self.capacity
        self.s[i] = s
        self.a[i] = a
        self.r[i] = r
        self.ns[i] = ns
        self.d[i] = 1.0 if done else 0.0
        self.i += 1
        self.n = min(self.n + 1, self.capacity)

    def sample(self, batch: int, rng: np.random.Generator):
        idx = rng.integers(0, self.n, size=batch)
        return self.s[idx], self.a[idx], self.r[idx], self.ns[idx], self.d[idx]


class DQNAgent:
    def __init__(
        self,
        seed: int = 0,
        *,
        lr: float = 1e-3,
        gamma: float = 0.97,
        buffer_size: int = 50_000,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.lr = lr
        self.gamma = gamma
        self.online = _init_mlp(self.rng)
        self.target = self.online.copy()
        self.buffer = ReplayBuffer(buffer_size)
        self.train_steps = 0

    def q_values(self, feat: np.ndarray, *, net: MLPWeights | None = None) -> np.ndarray:
        w = self.online if net is None else net
        x = np.atleast_2d(feat.astype(np.float32))
        q, _ = mlp_forward(w, x)
        return q[0]

    def act(
        self,
        feat: np.ndarray,
        epsilon: float,
        *,
        mask_catch: bool = False,
    ) -> int:
        if self.rng.random() < epsilon:
            choices = list(range(N_ACTIONS))
            if mask_catch:
                choices.remove(ACTION_CATCH_ATTENTION)
            return int(self.rng.choice(choices))
        q = self.q_values(feat)
        if mask_catch:
            q = q.copy()
            q[ACTION_CATCH_ATTENTION] = -1e9
        return int(np.argmax(q))

    def learn(self, batch_size: int = 64) -> None:
        if self.buffer.n < batch_size:
            return
        s, a, r, ns, done = self.buffer.sample(batch_size, self.rng)
        q_online_ns, _ = mlp_forward(self.online, ns)
        best = np.argmax(q_online_ns, axis=1)
        q_tgt_ns, _ = mlp_forward(self.target, ns)
        target_q = r + (1.0 - done) * self.gamma * q_tgt_ns[np.arange(batch_size), best]

        q_pred, cache = mlp_forward(self.online, s)
        d_q = np.zeros_like(q_pred)
        idx = np.arange(batch_size)
        d_q[idx, a] = (2.0 / batch_size) * (q_pred[idx, a] - target_q)
        grads = mlp_backward(self.online, cache, d_q)

        for name, g in grads.items():
            arr = getattr(self.online, name)
            np.clip(g, -1.0, 1.0, out=g)
            arr -= self.lr * g

        self.train_steps += 1
        if self.train_steps % 25 == 0:
            self.target = self.online.copy()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            w1=self.online.w1,
            b1=self.online.b1,
            w2=self.online.w2,
            b2=self.online.b2,
            w3=self.online.w3,
            b3=self.online.b3,
            n_features=np.array([N_FEATURES]),
            n_actions=np.array([N_ACTIONS]),
        )

    @classmethod
    def load(cls, path: str | Path, seed: int = 0) -> "DQNAgent":
        data = np.load(path)
        agent = cls(seed=seed)
        agent.online = MLPWeights(
            w1=data["w1"].astype(np.float32),
            b1=data["b1"].astype(np.float32),
            w2=data["w2"].astype(np.float32),
            b2=data["b2"].astype(np.float32),
            w3=data["w3"].astype(np.float32),
            b3=data["b3"].astype(np.float32),
        )
        agent.target = agent.online.copy()
        if int(data["n_features"][0]) != N_FEATURES or int(data["n_actions"][0]) != N_ACTIONS:
            raise ValueError("DQN checkpoint feature/action mismatch")
        return agent


def distill_from_q(
    agent: DQNAgent,
    q_path: str | Path,
    *,
    steps: int = 8000,
) -> None:
    """Warm-start DQN by imitating a strong tabular Q policy on visited states."""
    from fear_mecanumbot.qlearn import QAgent, discretize

    q_agent = QAgent.load(q_path)
    env = HriFearEnv(max_steps=120)
    # Collect teacher rollouts, then fit MLP to teacher actions
    feats: list[np.ndarray] = []
    acts: list[int] = []
    for i in range(steps):
        obs, info = env.reset(seed=10_000 + i)
        for _ in range(40):
            feat = features_from_info(obs, info)
            state = discretize(obs, info)
            target_a = int(np.argmax(q_agent.q[state]))
            feats.append(feat.copy())
            acts.append(target_a)
            obs, _r, terminated, truncated, info = env.step(target_a)
            if terminated or truncated:
                break
        if len(feats) >= 20_000:
            break

    x_all = np.stack(feats).astype(np.float32)
    a_all = np.asarray(acts, dtype=np.int32)
    n = len(a_all)
    for epoch in range(12):
        order = agent.rng.permutation(n)
        for start in range(0, n, 64):
            idx = order[start : start + 64]
            if len(idx) < 8:
                continue
            x = x_all[idx]
            a = a_all[idx]
            q_pred, cache = mlp_forward(agent.online, x)
            # Softmax CE gradient: softmax(q) - one_hot
            q_shift = q_pred - q_pred.max(axis=1, keepdims=True)
            exp = np.exp(q_shift)
            prob = exp / exp.sum(axis=1, keepdims=True)
            d_q = prob
            d_q[np.arange(len(a)), a] -= 1.0
            d_q /= float(len(a))
            grads = mlp_backward(agent.online, cache, d_q)
            for name, g in grads.items():
                arr = getattr(agent.online, name)
                np.clip(g, -1.0, 1.0, out=g)
                arr -= 2e-3 * g
        agent.target = agent.online.copy()
    agent.target = agent.online.copy()


def train(
    episodes: int = 5000,
    max_steps: int = 160,
    seed: int = 0,
    epsilon_start: float = 0.25,
    epsilon_end: float = 0.03,
    mask_catch: bool = True,
    q_bootstrap: str | Path | None = None,
) -> tuple[DQNAgent, list[float]]:
    """Double DQN fine-tune after Q distillation (keeps delivery high)."""
    env = HriFearEnv(max_steps=max_steps)
    agent = DQNAgent(seed=seed, lr=5e-4)
    if q_bootstrap is None:
        default_q = Path(__file__).resolve().parents[1] / "models" / "hri_q.npy"
        if default_q.is_file():
            q_bootstrap = default_q
    if q_bootstrap is not None and Path(q_bootstrap).is_file():
        distill_from_q(agent, q_bootstrap)
    returns: list[float] = []
    for ep in range(episodes):
        frac = ep / max(1, episodes - 1)
        epsilon = epsilon_start + (epsilon_end - epsilon_start) * frac
        obs, info = env.reset(seed=seed + ep)
        feat = features_from_info(obs, info)
        total = 0.0
        for _ in range(max_steps):
            action = agent.act(feat, epsilon, mask_catch=mask_catch)
            obs, reward, terminated, truncated, info = env.step(action)
            next_feat = features_from_info(obs, info)
            done = terminated or truncated
            agent.buffer.add(feat, action, float(reward), next_feat, done)
            agent.learn(batch_size=64)
            total += reward
            feat = next_feat
            if done:
                break
        returns.append(total)
    return agent, returns


def evaluate(
    agent: DQNAgent,
    episodes: int = 100,
    max_steps: int = 160,
    seed: int = 50_000,
    mask_catch: bool = True,
) -> dict:
    env = HriFearEnv(max_steps=max_steps)
    delivered = 0
    collisions = 0.0
    steps_sum = 0.0
    rets = 0.0
    counts = {name: 0 for name in ACTION_NAMES.values()}
    for ep in range(episodes):
        obs, info = env.reset(seed=seed + ep)
        feat = features_from_info(obs, info)
        total = 0.0
        for _ in range(max_steps):
            action = agent.act(feat, epsilon=0.0, mask_catch=mask_catch)
            counts[ACTION_NAMES[action]] = counts.get(ACTION_NAMES[action], 0) + 1
            obs, reward, terminated, truncated, info = env.step(action)
            total += reward
            feat = features_from_info(obs, info)
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
        "task": sum(counts.get(ACTION_NAMES[a], 0) for a in TASK_ACTIONS),
        "policy": "dqn",
    }
