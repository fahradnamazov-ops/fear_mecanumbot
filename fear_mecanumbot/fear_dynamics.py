"""Fear state dynamics for Fear HRI V1."""

from __future__ import annotations

from dataclasses import dataclass

from fear_mecanumbot.constants import (
    FEAR_DECAY_PER_STEP,
    FEAR_MAX,
    FEAR_MIN,
    FEAR_RISE_PER_RISK,
    FEAR_SPIKE_ON_EVENT,
)


@dataclass
class FearState:
    """Continuous internal fear variable (0–100 by default)."""

    level: float = 0.0
    time_since_event: float = 0.0

    def clamp(self) -> None:
        self.level = max(FEAR_MIN, min(FEAR_MAX, self.level))


def update_fear_level(
    state: FearState,
    *,
    risk: float = 0.0,
    spike_event: bool = False,
    spike: float = FEAR_SPIKE_ON_EVENT,
    rise_per_risk: float = FEAR_RISE_PER_RISK,
    decay: float = FEAR_DECAY_PER_STEP,
    dt: float = 1.0,
) -> FearState:
    """
    One environment step:
    - spike_event: near-collision
    - risk in [0, 1]: proximity / closing movement
    - slow decay when not spiking
    """
    risk_clipped = max(0.0, min(1.0, float(risk)))

    if spike_event:
        state.level = min(FEAR_MAX, state.level + spike)
        state.time_since_event = 0.0
    else:
        state.time_since_event += dt

    if risk_clipped > 0.0:
        state.level = min(FEAR_MAX, state.level + rise_per_risk * risk_clipped * dt)

    if not spike_event:
        state.level = max(FEAR_MIN, state.level - decay * dt)

    state.clamp()
    return state
