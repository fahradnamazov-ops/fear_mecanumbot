r"""
Validate Double DQN policy — fail hard if metrics are below bar.

  python scripts/validate_dqn.py
Exit code 0 only if delivery_rate >= 0.95 and model loads.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.dqn import DQNAgent, evaluate

MIN_DELIVERY = 0.95
MAX_COLLISIONS = 0.15


def main() -> int:
    path = ROOT / "models" / "hri_dqn.npz"
    if not path.is_file():
        print(f"FAIL: missing {path}")
        return 1
    agent = DQNAgent.load(path)
    stats = evaluate(agent, episodes=100, max_steps=160, seed=50_000, mask_catch=True)
    out = ROOT / "models" / "hri_dqn_eval.json"
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    ok = True
    if stats["delivery_rate"] < MIN_DELIVERY:
        print(f"FAIL: delivery_rate {stats['delivery_rate']:.2f} < {MIN_DELIVERY}")
        ok = False
    if stats["avg_collisions"] > MAX_COLLISIONS:
        print(f"FAIL: avg_collisions {stats['avg_collisions']:.2f} > {MAX_COLLISIONS}")
        ok = False
    if stats.get("policy") != "dqn":
        print("FAIL: policy tag is not dqn")
        ok = False
    # Must actually use task routes (not freeze-only collapse)
    task_n = int(stats.get("task", 0))
    freeze_n = int(stats.get("freeze", 0))
    if task_n < 100:
        print(f"FAIL: too few task actions ({task_n}) — policy collapsed?")
        ok = False
    if freeze_n > task_n:
        print(f"FAIL: freeze ({freeze_n}) dominates task ({task_n})")
        ok = False
    if ok:
        print("PASS: Double DQN validation")
        return 0
    print("FAIL: Double DQN validation")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
