"""
Proximity-only speed vs fear-modulated speed.

  python scripts/residual_fear_demo.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.risk import compute_risk


def proximity_speed(min_range: float, safe: float = 1.0, max_speed: float = 1.0) -> float:
    if min_range >= safe:
        return max_speed
    if min_range <= 0.25:
        return 0.0
    return max_speed * (min_range - 0.25) / (safe - 0.25)


def fear_modulated_speed(
    min_range: float,
    fear_level: float,
    *,
    safe: float = 1.0,
    max_speed: float = 1.0,
    fear_max: float = 100.0,
) -> float:
    base = proximity_speed(min_range, safe=safe, max_speed=max_speed)
    caution = 1.0 - 0.8 * (fear_level / fear_max)
    return max(0.0, base * caution)


def make_range_schedule(n: int = 80) -> list[float]:
    ranges: list[float] = []
    for t in range(n):
        if t < 20:
            ranges.append(2.0 - 1.5 * (t / 20.0))
        elif t < 35:
            ranges.append(0.5)
        else:
            ranges.append(0.5 + 1.5 * min(1.0, (t - 35) / 15.0))
    return ranges


def main() -> None:
    ranges = make_range_schedule()
    fear = FearState(level=0.0)
    rows: list[dict[str, float]] = []

    print("step  range  risk  fear   speed_prox  speed_fear")
    for step, min_range in enumerate(ranges):
        prev = ranges[step - 1] if step > 0 else min_range
        closing = max(0.0, prev - min_range) / 0.1
        risk = compute_risk(min_range=min_range, closing_speed=closing * 0.05)
        update_fear_level(fear, risk=risk, spike_event=min_range <= 0.25)

        sp = proximity_speed(min_range)
        sf = fear_modulated_speed(min_range, fear.level)
        row = {
            "step": step,
            "min_range": round(min_range, 3),
            "risk": round(risk, 3),
            "fear": round(fear.level, 2),
            "speed_proximity": round(sp, 3),
            "speed_fear": round(sf, 3),
        }
        rows.append(row)
        if step % 5 == 0 or step in (19, 34, 50, 79):
            print(
                f"{step:4d}  {min_range:5.2f}  {risk:4.2f}  {fear.level:5.1f}  "
                f"{sp:10.3f}  {sf:10.3f}"
            )

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "residual_fear_demo.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    late = [r for r in rows if r["step"] >= 55 and r["min_range"] >= 1.5]
    avg_prox = sum(r["speed_proximity"] for r in late) / len(late)
    avg_fear = sum(r["speed_fear"] for r in late) / len(late)
    print()
    print("After person steps away (steps >= 55, range >= 1.5):")
    print(f"  avg proximity speed = {avg_prox:.3f}")
    print(f"  avg fear speed      = {avg_fear:.3f}")
    print(f"  residual gap        = {avg_prox - avg_fear:.3f}  (should be > 0)")
    print(f"CSV written to {out}")


if __name__ == "__main__":
    main()
