r"""
Train tabular Q-learning on the local Fear HRI env.

  python scripts\train_hri_rl.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.qlearn import evaluate, train


def main() -> None:
    agent, returns = train(episodes=6000, max_steps=120, seed=0)
    model_dir = ROOT / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    q_path = model_dir / "hri_q.npy"
    agent.save(q_path)

    stats = evaluate(agent, episodes=80, max_steps=120, seed=50_000)
    stats_path = model_dir / "hri_q_eval.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"saved {q_path}")
    print(f"last-100 mean return: {sum(returns[-100:]) / 100:.2f}")
    print(f"eval delivery_rate: {stats['delivery_rate']:.2f}")
    print(f"eval avg_return: {stats['avg_return']:.2f}")
    print(f"eval avg_collisions: {stats['avg_collisions']:.2f}")
    print(f"eval avg_steps: {stats['avg_steps']:.1f}")
    print(
        "eval actions: "
        f"freeze={stats['freeze']} avoid={stats['avoid']} "
        f"catch_attention={stats['catch_attention']} task={stats['task']}"
    )
    print(f"eval json: {stats_path}")


if __name__ == "__main__":
    main()
