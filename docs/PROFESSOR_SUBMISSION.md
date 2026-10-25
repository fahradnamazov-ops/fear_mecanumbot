# Fear HRI — Professor Submission Summary

**Student:** Fahrad Namazov  
**Supervisor:** Csenge Hubay (MicroLab · Mecanumbot)  
**Date:** 5 October 2026  
**Repository:** https://github.com/fahradnamazov-ops/fear_mecanumbot  

---

## 1. What was delivered

A complete **Fear HRI V1** stack for the Mecanumbot brick-carry scenario:

| Layer | Deliverable |
|-------|-------------|
| Fear model | Continuous `fear_level` from proximity risk + near-collision spike; slow decay → residual caution |
| Learning | **Double DQN** (numpy MLP) selecting `freeze` / `avoid` / `catch_attention` / `task_middle|north|south` |
| Route cost (Csenge) | Completion time = **travel + wait**; long clear corridor can beat short blocked middle |
| Live ROS 2 | Fear BT in `mecanumbot_fear_hri_behaviour` on MuJoCo `fear_hri_brick_carry` |
| Sim alignment | `catch_attention` **IRL-only** (masked in sim); person GT in sim |

The robot decides the corridor itself from travel+wait features and rewards — **no hardcoded route lock**.

---

## 2. Key results (reproducible)

### Offline (this machine, 5 Oct 2026)

| Check | Result |
|-------|--------|
| Unit tests | **58 passed** |
| Double DQN eval | delivery **1.00**, collisions **0.00**, ~12.2 steps/episode |
| Route cost ordering | blocked middle expensive; clear middle cheapest; person on north → not north |
| Policy mix (eval) | task_middle ≈ 708, task_north ≈ 514 (adapts to person) |

### Live MuJoCo end-to-end

| Check | Result |
|-------|--------|
| Fear BT + Double DQN | `policy=rl_dqn` |
| Brick task | **ALL BRICKS DONE — delivered 4/4** |

Reproduce offline:

```bash
cd fear_mecanumbot
pip install -r requirements.txt
pytest -q
python scripts/validate_dqn.py
python scripts/validate_route_cost.py
python scripts/v1_final_demo.py
```

Live (WSL + ROS 2 Humble lab setup):

```bash
bash scripts/wsl_e2e_dqn.sh
# or interactive:
bash scripts/wsl_clean_brick_sim.sh
```

---

## 3. Design decisions (team-aligned)

1. **Fear trigger:** LIDAR-style range + closing speed (not IMU pickup).
2. **Avoid:** Nav2 Approach retreat (fear-scaled), via `mecanumbot_sim_nav_shim` in sim.
3. **Routes:** fixed arena lanes middle / north (+0.9 m) / south (−0.9 m); wait if person occupies that lane.
4. **Finish ASAP + avoid human:** RL reward uses completion-time cost; near-person task actions are penalised; clear cheap lane preferred.
5. **catch_attention:** enabled for IRL only (`FEAR_CATCH_ATTENTION`); off in sim.

---

## 4. Documents in this pack

| File | Purpose |
|------|---------|
| `TECHNICAL_REPORT.md` | Full method, biology mapping, limitations |
| `INTEGRATION.md` | How to activate fear in Mecanumbot sim / BT |
| `hri_dqn_eval.json` | Latest Double DQN evaluation metrics |
| `EMAIL_DRAFT.txt` | Suggested email to professor |
| `HOW_TO_RUN.txt` | Short reproduce checklist |

Weights: `fear_mecanumbot/models/hri_dqn.npz` (also referenced by `FEAR_DQN_MODEL` in live scripts).

---

## 5. Known limitations (honest)

- Ethologist review not yet requested by the team.
- Physical Jetson / IRL `catch_attention` not demonstrated in this submission (sim-masked by design).
- Early demo videos showed poor route behaviour (person-relative vias); **fixed** to arena lanes + cost commit; please use live e2e / current weights for review, not older clips.
- Deep RL is Double DQN on a local 2D env; live MuJoCo uses the same policy weights with live cost features.

---

## 6. Status

**V1 software deliverable complete** for supervisor review: fear dynamics, Double DQN policy, completion-time route choice, MuJoCo brick-carry integration, tests, and documentation.
