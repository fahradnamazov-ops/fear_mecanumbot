# Technical Report: Fear HRI V1

**Project:** Mecanumbot Fear Human–Robot Interaction  
**Author:** Fahrad Namazov  
**Supervisor:** Csenge Hubay  
**Date:** September 2026  
**Code:** https://github.com/fahradnamazov-ops/fear_mecanumbot  

---

## 1. Abstract

This work implements a continuous internal fear state for a mobile robot engaged in a brick-carry task near a moving person. Proximity risk derived from minimum range and closing speed drives `fear_level`. Near collisions produce large fear spikes; fear then decays slowly when the person moves away. A tabular Q-learning agent selects among four discrete actions—freeze, avoid, catch attention, and task execution—on a local two-dimensional Gymnasium environment. Evaluation shows a residual caution gap of approximately 0.47 relative to proximity-only speed modulation, perfect delivery rate under the learned policy in evaluation episodes, fewer steps than a fixed heuristic, and zero near collisions for the Q-learning policy in the reported trial. Draft ROS 2 behaviour and simulation scenario artefacts are included for later integration with the Mecanumbot software stack.

---

## 2. Introduction

### 2.1 Motivation

Classical proximity safety reduces robot speed when a human is close and restores full speed when the human leaves the protective envelope. Biological fear and anxiety, by contrast, can leave a residual defensive state after an aversive event. This project asks whether an explicit continuous fear variable can induce that residual behaviour in a robot HRI setting, and whether reinforcement learning can select appropriate defensive and task actions under that state.

### 2.2 Scenario

- The robot transports bricks to a fixed goal.
- A person exercises or moves nearby (Fear HRI protocol; calf-level motion is relevant for LIDAR returns).
- The robot must complete the task while managing proximity risk.

### 2.3 Design decisions (team-aligned)

| Decision | Choice |
|----------|--------|
| Fear trigger | LIDAR-style range risk and near-collision events |
| Not used as primary trigger (V1) | IMU-based pickup detection |
| Fear representation | Continuous scalar in observation and reward |
| Decay | Slow (0.2 units per step by default) |
| Avoid execution (robot stack) | Nav2 `Approach` to a retreat pose; distance may scale with fear |
| Social signal | `catch_attention` (seek human visual attention) |
| Explicitly deferred | LED patterns; ethologist review; production merge into team repos |

---

## 3. Biological mapping

The following mapping links ethological / neuroscience concepts to robot mechanisms for V1. It is an engineering analogy, not a claim of biological fidelity.

| Concept | Biological idea | Robot realisation |
|---------|-----------------|-------------------|
| Fear | Response to present threat | Elevated `fear_level` under high proximity risk |
| Near-collision event | Acute aversive event | Spike when `min_range ≤ HIT_DISTANCE_M` (0.25 m) |
| Residual caution | Defensive state after threat removal | Slow decay of `fear_level` after the person steps away |
| Freezing | Immobility under threat | Action `freeze` (zero velocity) |
| Avoidance | Distance regulation | Action `avoid` (retreat via Nav2 Approach on robot) |
| Social signalling | Attract conspecific attention | Action `catch_attention` |
| Instrumental learning | When to defend versus continue | Reward shaping + Q-learning policy |

### Key references

- Tovote, P., Fadok, J. P., & Lüthi, A. (2015). Neuronal circuits for fear and anxiety. *Nature Reviews Neuroscience*.
- LeDoux, J. E. (2014). Coming to terms with fear. *Proceedings of the National Academy of Sciences*.
- Maroto-Gómez et al. (2024). Deep reinforcement learning with internal biological variables (IEEE).
- MicroLab Fear HRI experimental protocol (internal).

---

## 4. Method

### 4.1 Risk signal

Risk \(r \in [0, 1]\) is computed from minimum obstacle/person range \(d\) and closing speed \(v_c \geq 0\):

- If \(d \leq d_{\mathrm{hit}}\) (0.25 m): proximity component = 1.
- If \(d \geq d_{\mathrm{safe}}\) (1.0 m): proximity component = 0.
- Otherwise: linear interpolation between safe and hit distances.
- Closing speed adds a non-negative term scaled by `speed_scale` (default 0.5), clipped so total risk ≤ 1.

A discrete near-collision flag is true when \(d \leq d_{\mathrm{hit}}\).

### 4.2 Fear dynamics

State variables: `level` ∈ [0, 100], `time_since_event`.

Each step:

1. On near-collision spike: add `FEAR_SPIKE_ON_EVENT` (50), reset event timer.
2. Else: increment time since event.
3. If risk > 0: increase fear by `FEAR_RISE_PER_RISK × risk × dt` (default rise 5.0).
4. If not spiking: decrease fear by `FEAR_DECAY_PER_STEP × dt` (default 0.2).
5. Clamp to [0, 100].

Slow decay is essential for residual caution: after the person leaves the safe distance, proximity-only controllers return to full speed immediately, while fear-modulated speed remains reduced until `fear_level` falls.

### 4.3 Discrete actions

| ID | Name | Intended behaviour |
|----|------|--------------------|
| 0 | `freeze` | Stop motion |
| 1 | `avoid` | Increase distance from the person (Nav2 retreat on robot) |
| 2 | `catch_attention` | Ostensive / attention-seeking motion |
| 3 | `task` | Continue brick pipeline (approach brick / goal / manipulate) |

### 4.4 Reward

The local environment combines task progress with fear-related terms, including:

- Near-collision penalty (−20)
- Per-step cost for moving while fear > 0 (α × fear_level)
- Small bonus when fear decreases
- Wall collision penalty
- Task rewards for pick and deliver; action-specific shaping near/far from the person

Exact coefficients are defined in `fear_mecanumbot/constants.py`.

### 4.5 Learning environment

`HriFearEnv` (Gymnasium) provides a 2D brick-carry episode with a scripted person trajectory. Observations include geometry and fear-related features suitable for tabular discretisation. The agent is a tabular Q-learner (`QAgent`) trained with ε-greedy exploration.

Local episodes use **simulated geometry**, not live ROS topics. This isolates fear and policy logic from the full Mecanumbot bring-up.

### 4.6 Residual caution metric

After a close approach phase, when the person is again far (\(d \geq 1.5\) m), compare:

- Proximity-only normalised speed
- Fear-modulated speed: base × (1 − 0.8 × fear_level / 100)

The **residual gap** is the mean difference (proximity-only − fear-modulated) over late far samples. A positive gap indicates lingering caution.

### 4.7 Behaviour tree sketch (robot integration)

Intended tree structure for the team behaviours stack:

```text
ROOT
├── ParamsToBlackboard
├── UpdateFearFromRange          # /mecanumbot/scan (+ optional pose fusion)
└── PolicyGate
    ├── Freeze
    ├── Avoid                    # Nav2 Approach retreat
    ├── CatchAttention
    └── TaskSequence             # brick → goal pipeline
```

Local stubs: `fear_mecanumbot/fear_hri_bt.py`  
ROS draft package: `ros_draft/mecanumbot_fear_hri_behaviour/`

---

## 5. Software architecture

| Module | Responsibility |
|--------|----------------|
| `constants.py` | Distances, fear and reward coefficients, action IDs |
| `risk.py` | Risk and near-collision predicates |
| `fear_dynamics.py` | `FearState`, `update_fear_level` |
| `reward.py` | Core reward aggregation |
| `sensing.py` | LaserScan FOV min-range helpers; fusion with person pose |
| `env.py` | `HriFearEnv` |
| `qlearn.py` | Tabular Q-learning |
| `policy.py` | Load default agent / action names |
| `scenario.py` | Heuristic baseline |
| `fear_hri_bt.py` | Local BT leaf stubs |
| `ros_bridge.py` | Notes / helpers toward ROS wiring |

Supporting artefacts:

- `scripts/` — demos and training entry points  
- `tests/` — unit tests  
- `models/` — persisted Q-table  
- `ros_draft/` — ament package skeleton for `mecanumbot_behaviours`  
- `sim_draft/` — scenario YAML for `mecanumbot_sim`  

---

## 6. Results (local evaluation)

Command:

```bash
python scripts/v1_final_demo.py
```

Representative summary (`output/v1_summary.json`, 30 August 2026 run):

| Metric | Value |
|--------|-------|
| Unit tests | 50 passed |
| Residual gap (person far) | ≈ 0.47 |
| Q-learning delivery rate (40 eval episodes) | 1.00 |
| Mean Q episode length | ≈ 34 steps |
| Heuristic episode length (example) | 85 steps |
| Near collisions (Q policy, reported eval) | 0.0 mean |
| Dominant Q actions (eval counts) | task ≫ avoid; freeze / catch_attention rare |

Interpretation:

- Residual gap > 0 supports the claim that fear decays more slowly than pure proximity gating.
- The learned policy completes delivery faster than the fixed heuristic in the reported comparison and avoids near collisions in evaluation.
- Freeze and catch_attention appear infrequently when the policy successfully stays out of hit distance; that is consistent with shaping that rewards avoidance and task progress.

---

## 7. Limitations

1. **Not validated on the physical Jetson stack or full MuJoCo truth twin** with this fear tree in closed loop.
2. **No merged pull request** into `mecanumbot_behaviours`, `mecanumbot_remote`, or `fear_RL` at the time of writing (access and ownership constraints).
3. Local range is **geometric**, not a full LIDAR simulation.
4. Ethologist review is **pending** and scheduled only when the team requests it.
5. Tabular Q-learning is appropriate for V1 discreteness but is not a deep RL baseline.

---

## 8. Status relative to project track

The local fear model, reward design, biological mapping, environment, and Q-learning policy constitute the completed Fear V1 software deliverable in this repository. Simulation and behaviour-tree integration remain available as drafts for team maintainers to copy into:

- `Fortuz/mecanumbot_remote` → `mecanumbot_sim`
- `hubaycsenge/mecanumbot_behaviours`

---

## 9. How to reproduce

```bash
python -m venv .venv
# activate venv
pip install -r requirements.txt
pytest -v
python scripts/residual_fear_demo.py
python scripts/v1_final_demo.py
```

Optional retraining:

```bash
python scripts/train_hri_rl.py
python scripts/run_hri_rl.py
```

---

## 10. Document history

| Version | Date | Notes |
|---------|------|-------|
| V1 | Aug–Sep 2026 | Local model, Q-learning, drafts, report consolidation |
