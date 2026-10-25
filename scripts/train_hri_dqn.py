r"""
Train Double DQN (numpy MLP) for Fear HRI + routes.

  python scripts/train_hri_dqn.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.dqn import evaluate, train


def main() -> None:
    agent, returns = train(episodes=5000, max_steps=160, seed=0, mask_catch=True)
    model_dir = ROOT / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / "hri_dqn.npz"
    agent.save(path)

    stats = evaluate(agent, episodes=100, max_steps=160, seed=50_000, mask_catch=True)
    stats_path = model_dir / "hri_dqn_eval.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"saved {path}")
    print(f"last-100 mean return: {sum(returns[-100:]) / 100:.2f}")
    print(f"eval delivery_rate: {stats['delivery_rate']:.2f}")
    print(f"eval avg_return: {stats['avg_return']:.2f}")
    print(f"eval avg_collisions: {stats['avg_collisions']:.2f}")
    print(f"eval avg_steps: {stats['avg_steps']:.1f}")
    print(
        "eval actions: "
        f"freeze={stats.get('freeze', 0)} avoid={stats.get('avoid', 0)} "
        f"catch={stats.get('catch_attention', 0)} "
        f"task_m={stats.get('task_middle', 0)} "
        f"task_n={stats.get('task_north', 0)} "
        f"task_s={stats.get('task_south', 0)}"
    )
    print(f"eval json: {stats_path}")


if __name__ == "__main__":
    main()
