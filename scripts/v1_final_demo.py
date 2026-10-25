r"""
V1 summary demo (Double DQN).

  python scripts/v1_final_demo.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.constants import ACTION_NAMES, TASK_ACTIONS
from fear_mecanumbot.dqn import DQNAgent, evaluate, features_from_info, train
from fear_mecanumbot.env import HriFearEnv
from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.risk import compute_risk
from fear_mecanumbot.scenario import heuristic_action


def run_pytest() -> tuple[bool, str, str | None]:
    try:
        import pytest  # noqa: F401
    except ImportError:
        return (
            False,
            "pytest not installed",
            "Run: pip install -r requirements.txt",
        )

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    summary = out.splitlines()[-1] if out else err.splitlines()[-1] if err else f"exit code {proc.returncode}"
    hint = None
    if proc.returncode != 0:
        hint = err.splitlines()[0] if err else "Run: python -m pytest -v"
    return proc.returncode == 0, summary, hint


def residual_gap() -> float:
    fear = FearState(level=0.0)
    prox_speeds: list[float] = []
    fear_speeds: list[float] = []
    for step in range(80):
        if step < 20:
            r = 2.0 - 1.5 * (step / 20.0)
        elif step < 35:
            r = 0.5
        else:
            r = 0.5 + 1.5 * min(1.0, (step - 35) / 15.0)
        risk = compute_risk(min_range=r, closing_speed=0.0)
        update_fear_level(fear, risk=risk, spike_event=r <= 0.25)
        if r >= 1.5 and step >= 55:
            base = 1.0 if r >= 1.0 else max(0.0, (r - 0.25) / 0.75)
            caution = 1.0 - 0.8 * (fear.level / 100.0)
            prox_speeds.append(base)
            fear_speeds.append(max(0.0, base * caution))
    if not prox_speeds:
        return 0.0
    return sum(prox_speeds) / len(prox_speeds) - sum(fear_speeds) / len(fear_speeds)


def run_episode(choose_action, seed: int = 7) -> dict:
    env = HriFearEnv(max_steps=120)
    obs, info = env.reset(seed=seed)
    steps = 0
    actions: dict[str, int] = {
        "freeze": 0,
        "avoid": 0,
        "catch_attention": 0,
        "task_middle": 0,
        "task_north": 0,
        "task_south": 0,
    }

    while True:
        aid = choose_action(obs, info)
        name = ACTION_NAMES.get(aid, "task_middle")
        actions[name] = actions.get(name, 0) + 1
        obs, _r, terminated, truncated, info = env.step(aid)
        steps += 1
        if terminated or truncated:
            break
    return {
        "steps": steps,
        "delivered": bool(info["delivered"]),
        "final_fear": round(info["fear_level"], 1),
        "near_collisions": info["near_collisions"],
        "actions": actions,
        "task_total": sum(actions.get(ACTION_NAMES[a], 0) for a in TASK_ACTIONS),
    }


def main() -> None:
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)

    ok, pytest_line, pytest_hint = run_pytest()
    gap = round(residual_gap(), 3)

    model_path = ROOT / "models" / "hri_dqn.npz"
    if not model_path.exists():
        agent, _ = train(episodes=3000, max_steps=120, seed=0)
        agent.save(model_path)
    agent = DQNAgent.load(model_path)
    eval_stats = evaluate(agent, episodes=40, max_steps=120, seed=99_000, mask_catch=True)

    heuristic = run_episode(
        lambda _o, info: heuristic_action(info["fear_level"], info["min_range"], info["risk"])
    )

    def greedy(obs, info):
        return agent.act(features_from_info(obs, info), epsilon=0.0, mask_catch=True)

    rl = run_episode(greedy)

    summary = {
        "policy": "double_dqn",
        "pytest_ok": ok,
        "pytest_line": pytest_line,
        "pytest_hint": pytest_hint,
        "residual_gap": gap,
        "dqn_eval": eval_stats,
        "heuristic_episode": heuristic,
        "dqn_episode": rl,
        "done": [
            "fear_level + LIDAR risk + near-collision spike + slow decay",
            "residual caution vs proximity-only (gap > 0)",
            "discrete actions + Double DQN policy (routes included)",
            "Nav2 avoid retreat (Approach)",
            "BT + ROS bridge notes",
            "sim scenario YAML",
        ],
        "open": [
            "MuJoCo sim run with Fear HRI tree",
            "Robot brick run",
        ],
    }

    out_path = out_dir / "v1_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("=== Fear HRI summary (Double DQN) ===")
    if ok:
        print(f"pytest: PASS — {pytest_line}")
    else:
        print(f"pytest: FAIL — {pytest_line}")
        if pytest_hint:
            print(f"  hint: {pytest_hint}")
    print(f"residual_gap: {gap}")
    print(
        f"dqn_eval delivery={eval_stats['delivery_rate']:.2f} "
        f"collisions={eval_stats['avg_collisions']:.2f}"
    )
    print(f"heuristic episode delivered={heuristic['delivered']} steps={heuristic['steps']}")
    print(f"dqn episode delivered={rl['delivered']} steps={rl['steps']}")
    print(f"wrote {out_path}")
    if not ok or eval_stats["delivery_rate"] < 0.95 or not rl["delivered"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
