# Fear HRI — presentation (12 slides)

Fahrad Namazov · MicroLab Mecanumbot · September 2026  
GitHub: https://github.com/fahradnamazov-ops/fear_mecanumbot

---

## Slide 1 — Title

Fear HRI on Mecanumbot — progress update

- Fahrad Namazov
- MicroLab / Mecanumbot
- https://github.com/fahradnamazov-ops/fear_mecanumbot

---

## Slide 2 — Research question

Can internal fear outlast proximity-only safety?

- Continuous `fear_level` (0–100)
- Slow decay after the person steps away → residual caution (gap ~0.47)
- Policy learns defensive actions; no hardcoded freeze rules

---

## Slide 3 — Scenario

Brick carry with a person nearby

- Robot carries bricks to a fixed goal
- Person exercises nearby (Fear HRI protocol)
- LIDAR min range + closing speed → fear (not IMU pickup in V1)
- Actions: freeze · avoid · catch_attention · task

---

## Slide 4 — Biology → robot

| Concept | Robot |
|---------|--------|
| Fear | LIDAR risk / near-collision → `fear_level` |
| Residual caution | Slow decay |
| Freezing | `freeze` |
| Social signal | `catch_attention` |
| Learning | Q-learning vs heuristic |

Refs: Tovote 2015; LeDoux 2014; Maroto-Gómez 2024.

---

## Slide 5 — Fear model

- Risk from LIDAR range + closing speed
- Near-collision spike +50 at 0.25 m
- Fear 0–100, decay 0.2/step
- On robot: `/mecanumbot/scan` + optional subject pose fusion

---

## Slide 6 — Actions

| Action | Implementation |
|--------|----------------|
| freeze | Stop + cancel Nav2 |
| avoid | Nav2 Approach retreat (distance scales with fear) |
| catch_attention | Dog gestures + RelativeTurnPattern |
| task | Brick pipeline |

---

## Slide 7 — Architecture

```text
/scan → risk → fear_level → policy → action
                              ↓
              mecanumbot_fear_hri_behaviour (BT)
                              ↓
           Nav2 · freeze · catch_attention · task
```

- Local training: `fear_mecanumbot`
- Sim: `mecanumbot_sim` + `mecanumbot_RL`
- PR branches: `fahrad/fear_hri_behaviour`, `fahrad/fear_hri_scenario`

---

## Slide 8 — Results (local)

| Metric | Value |
|--------|-------|
| Tests | 50 passed |
| Residual gap | ~0.47 |
| Q delivery rate | 100% |
| Q steps / heuristic steps | ~34 / ~85 |
| Near-collisions (Q) | 0 |

---

## Slide 9 — Done

- Fear model + Q-learning + tests
- Scan fusion plan (`sensing.py`)
- Sim scenario + behaviours package with `/scan` subscriber
- Report + integration docs

---

## Slide 10 — In progress

- PR: scenario → `mecanumbot_sim`
- PR: `mecanumbot_fear_hri_behaviour` → behaviours repo
- Sim demo: truth twin + fear tree logging
- Robot run after sim

---

## Slide 11 — Next

1. Merge scenario + behaviours PRs
2. Run `sim.launch.py mode:=truth_twin scenario:=fear_hri_brick_carry`
3. Launch `fear_hri_bt_node` — verify fear logs
4. Record demo for report + Trello HRI

---

## Slide 12 — Discussion

- Sim integration review
- Avoid / task subtrees in BT (Approach wiring)
- Robot trial timing
