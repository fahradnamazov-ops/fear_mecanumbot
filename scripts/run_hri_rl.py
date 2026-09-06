r"""
Run a trained Q policy (or heuristic if no model).

  python scripts\train_hri_rl.py
  python scripts\run_hri_rl.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.constants import ACTION_NAMES
from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.qlearn import QAgent, discretize
from fear_mecanumbot.scenario import heuristic_action


def run_policy(name: str, choose_action, max_steps: int = 120, seed: int = 7) -> list[dict]:
    env = HriFearEnv(max_steps=max_steps)
    obs, info = env.reset(seed=seed)
    log: list[dict] = []
    for _ in range(max_steps):
        action = choose_action(obs, info)
        obs, reward, terminated, truncated, info = env.step(action)
        log.append(
            {
                "step": info["step"],
                "min_range": round(info["min_range"], 3),
                "risk": round(info["risk"], 3),
                "fear": round(info["fear_level"], 2),
                "action": action,
                "has_brick": info["has_brick"],
                "delivered": info["delivered"],
                "near_collision": info["near_collisions"] > 0,
                "reward": round(reward, 3),
            }
        )
        if terminated or truncated:
            break
    return log


def print_log(title: str, log: list[dict]) -> None:
    print(f"\n=== {title} ===")
    print("step  range  fear   action              brick  delivered  r")
    for row in log:
        if row["step"] % 5 == 0 or row["step"] in (1, 20, 50) or row["delivered"]:
            name = ACTION_NAMES.get(row["action"], str(row["action"]))
            print(
                f"{row['step']:4d}  {row['min_range']:5.2f}  {row['fear']:5.1f}  "
                f"{name:18s}  {int(row['has_brick'])}      {int(row['delivered'])}   "
                f"{row['reward']:6.2f}"
            )
    last = log[-1]
    print(
        f"end: steps={len(log)} delivered={last['delivered']} "
        f"fear={last['fear']:.1f} min_range={last['min_range']:.2f} "
        f"near_collision_seen={any(r['near_collision'] for r in log)}"
    )


def main() -> None:
    q_path = ROOT / "models" / "hri_q.npy"
    heuristic_log = run_policy(
        "heuristic",
        lambda obs, info: heuristic_action(info["fear_level"], info["min_range"], info["risk"]),
    )
    print_log("heuristic", heuristic_log)

    if not q_path.exists():
        print(f"\nNo model at {q_path}. Train first: python scripts\\train_hri_rl.py")
        return

    agent = QAgent.load(q_path)

    def greedy(_obs, info):
        return agent.act(discretize(_obs, info), epsilon=0.0)

    rl_log = run_policy("q-learning", greedy)
    print_log("Q-learning (greedy)", rl_log)

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "hri_rl_demo.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rl_log[0].keys()))
        writer.writeheader()
        writer.writerows(rl_log)
    print(f"\nCSV: {out}")


if __name__ == "__main__":
    main()
