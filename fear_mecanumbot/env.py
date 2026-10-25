"""2D Fear HRI environment: freeze / avoid / catch_attention / task.

Training layout matches MuJoCo fear_hri_brick_carry (corridor person + furniture).
Contract taught to Q:
  - task: complete pick/deliver (main objective)
  - avoid: pause delivery, increase distance to person (not when far)
  - freeze: only when very close
  - catch_attention: light social cue (IRL); weak in this 2D trainer
"""

from __future__ import annotations

from typing import Any

import numpy as np

from fear_mecanumbot.constants import (
    ACTION_AVOID,
    ACTION_CATCH_ATTENTION,
    ACTION_FREEZE,
    ACTION_TASK,
    ACTION_TASK_MIDDLE,
    ACTION_TASK_NORTH,
    ACTION_TASK_SOUTH,
    FEAR_MAX,
    HIT_DISTANCE_M,
    N_ACTIONS,
    REWARD_AVOID_CLEARED,
    REWARD_AVOID_FAR,
    REWARD_AVOID_NEAR,
    REWARD_CATCH_FAR,
    REWARD_CATCH_NEAR,
    REWARD_DELIVER,
    REWARD_FREEZE_FAR,
    REWARD_FREEZE_NEAR,
    REWARD_NEAR_COLLISION_PENALTY,
    REWARD_OBSTACLE_HIT,
    REWARD_PICK,
    REWARD_STEP,
    REWARD_STUCK,
    SAFE_DISTANCE_M,
    TASK_ACTIONS,
)
from fear_mecanumbot.fear_dynamics import FearState, update_fear_level
from fear_mecanumbot.route_cost import reward_from_completion_cost
from fear_mecanumbot.scenario import (
    BRICK_XY,
    GOAL_XY,
    START_XY,
    ScenarioState,
    apply_action,
    dist,
    person_blocks_middle,
    person_lateral_bin,
    person_path,
    sense,
)

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:  # pragma: no cover
    gym = None
    spaces = None


def _make_state(
    *,
    closest: float = 0.22,
    robot: tuple[float, float] = START_XY,
    brick: tuple[float, float] = BRICK_XY,
    goal: tuple[float, float] = GOAL_XY,
) -> ScenarioState:
    person0 = person_path(0, closest=closest)
    return ScenarioState(
        robot=robot,
        person=person0,
        brick=brick,
        goal=goal,
        fear=FearState(level=0.0),
        prev_person=person0,
        last_target_dist=dist(robot, brick),
    )


def _obs_from(state: ScenarioState, min_range: float, risk: float) -> np.ndarray:
    assert state.fear is not None
    # Normalise roughly to live arena extent (~±1.7)
    s = 3.5
    return np.array(
        [
            (state.robot[0] + 1.7) / s,
            (state.robot[1] + 1.4) / s,
            (state.person[0] + 1.7) / s,
            (state.person[1] + 1.4) / s,
            (state.brick[0] + 1.7) / s,
            (state.brick[1] + 1.4) / s,
            (state.goal[0] + 1.7) / s,
            (state.goal[1] + 1.4) / s,
            1.0 if state.has_brick else 0.0,
            1.0 if state.delivered else 0.0,
            state.fear.level / FEAR_MAX,
            min(min_range / 4.0, 1.0),
            risk,
        ],
        dtype=np.float32,
    )


def _action_shaping(action: int, min_range: float, fear_level: float) -> float:
    near = min_range < SAFE_DISTANCE_M
    if action == ACTION_FREEZE:
        if min_range <= HIT_DISTANCE_M + 0.15:
            return REWARD_FREEZE_NEAR
        return REWARD_FREEZE_FAR
    if action == ACTION_AVOID:
        return REWARD_AVOID_NEAR if near else REWARD_AVOID_FAR
    if action == ACTION_CATCH_ATTENTION:
        if 0.4 <= min_range <= 2.0 and 15.0 <= fear_level < 45.0:
            return REWARD_CATCH_NEAR
        return REWARD_CATCH_FAR
    return 0.0


class HriFearEnv:
    """Discrete-action env: freeze / avoid / catch_attention / task."""

    metadata = {"render_modes": []}

    def __init__(self, max_steps: int = 160, closest: float = 0.22) -> None:
        self.max_steps = max_steps
        self.closest = closest
        self.state: ScenarioState | None = None
        self._last_min_range = 4.0
        self._last_risk = 0.0
        if spaces is not None:
            self.action_space = spaces.Discrete(N_ACTIONS)
            self.observation_space = spaces.Box(
                low=0.0, high=1.0, shape=(13,), dtype=np.float32
            )
        else:
            self.action_space = None
            self.observation_space = None

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if seed is not None:
            rng = np.random.default_rng(seed)
            closest = float(rng.uniform(0.18, 0.32))
            # Small start jitter so policy is not brittle
            robot = (
                START_XY[0] + float(rng.uniform(-0.08, 0.08)),
                START_XY[1] + float(rng.uniform(-0.15, 0.15)),
            )
        else:
            closest = self.closest
            robot = START_XY
        options = options or {}
        closest = float(options.get("closest", closest))
        self.state = _make_state(closest=closest, robot=robot)
        self.closest = closest
        min_range, risk, _near = sense(self.state)
        self._last_min_range = min_range
        self._last_risk = risk
        return _obs_from(self.state, min_range, risk), self._info(False, False)

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.state is None:
            raise RuntimeError("call reset() before step()")
        action = int(action)
        if action not in (
            ACTION_FREEZE,
            ACTION_AVOID,
            ACTION_CATCH_ATTENTION,
            ACTION_TASK_MIDDLE,
            ACTION_TASK_NORTH,
            ACTION_TASK_SOUTH,
        ):
            raise ValueError(f"invalid action {action}")

        state = self.state
        assert state.fear is not None
        min_range, risk, near = sense(state)
        previous_fear = state.fear.level
        prev_range = min_range
        hits_before = state.obstacle_hits
        update_fear_level(state.fear, risk=risk, spike_event=near)

        target = state.goal if state.has_brick else state.brick
        dist_before = dist(state.robot, target)
        just_picked, just_delivered = apply_action(state, action)
        dist_after = dist(state.robot, target)
        min_after, _risk_after, near_after = sense(state)
        near = near or near_after
        if near:
            state.near_collisions += 1

        reward = REWARD_STEP + _action_shaping(action, min_range, state.fear.level)
        # Task progress toward current target
        if action in TASK_ACTIONS:
            reward += 2.0 * (dist_before - dist_after)
        # Csenge completion-time cost: travel + wait (long clear cheap, short blocked expensive)
        cost_r, cost_info = reward_from_completion_cost(
            action, state.robot, target, state.person
        )
        reward += cost_r
        if action == ACTION_AVOID and min_after > prev_range + 0.02:
            reward += REWARD_AVOID_CLEARED
        if just_picked:
            reward += REWARD_PICK
        if just_delivered:
            reward += REWARD_DELIVER
        if near:
            reward += REWARD_NEAR_COLLISION_PENALTY
        if state.obstacle_hits > hits_before:
            reward += REWARD_OBSTACLE_HIT
        if state.no_progress_steps > 12 and action in TASK_ACTIONS:
            reward += REWARD_STUCK
        if action != ACTION_FREEZE and min_range < SAFE_DISTANCE_M and state.fear.level > 0.0:
            reward -= 0.020 * state.fear.level
        # Driving into human on any corridor is expensive
        if action in TASK_ACTIONS and min_range < SAFE_DISTANCE_M:
            reward -= 0.45 * ((SAFE_DISTANCE_M - min_range) / SAFE_DISTANCE_M)
        if action == ACTION_AVOID and min_range < SAFE_DISTANCE_M:
            reward += 0.22
        if state.fear.level < previous_fear:
            reward += 0.05
        if action in TASK_ACTIONS and min_range > SAFE_DISTANCE_M:
            reward += 0.08

        state.prev_person = state.person
        state.step += 1
        state.person = person_path(state.step, closest=self.closest)

        terminated = bool(just_delivered or near)
        truncated = bool(state.step >= self.max_steps and not terminated)
        min_range, risk, _ = sense(state)
        self._last_min_range = min_range
        self._last_risk = risk
        obs = _obs_from(state, min_range, risk)
        info = self._info(just_picked, just_delivered)
        info.update(cost_info)
        return obs, float(reward), terminated, truncated, info

    def _info(self, just_picked: bool, just_delivered: bool) -> dict[str, Any]:
        state = self.state
        assert state is not None and state.fear is not None
        return {
            "fear_level": float(state.fear.level),
            "min_range": float(self._last_min_range),
            "risk": float(self._last_risk),
            "has_brick": bool(state.has_brick),
            "delivered": bool(state.delivered),
            "near_collisions": int(state.near_collisions),
            "obstacle_hits": int(state.obstacle_hits),
            "just_picked": just_picked,
            "just_delivered": just_delivered,
            "step": int(state.step),
            "target_dist_m": float(
                dist(state.robot, state.goal if state.has_brick else state.brick)
            ),
            "person_lat": int(person_lateral_bin(state)),
            "middle_blocked": bool(person_blocks_middle(state)),
        }


if gym is not None:

    class HriFearGymEnv(HriFearEnv, gym.Env):
        pass
else:  # pragma: no cover
    HriFearGymEnv = HriFearEnv
