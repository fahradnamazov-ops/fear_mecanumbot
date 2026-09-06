# Fear HRI V1 — report

Fahrad Namazov · MicroLab Mecanumbot · 30 August 2026

## Question

Can a continuous internal `fear_level` produce defensive behaviour that outlasts proximity-only safety — residual caution after the person steps away?

## Method

- Trigger: LIDAR min range + closing speed → risk; spike when range ≤ 0.25 m. Not IMU pickup.
- Fear: continuous 0–100, spike +50 on near-collision, rise with risk, decay 0.2/step.
- Actions: freeze · avoid (Nav2 retreat) · catch_attention · task (brick → goal).
- Policy: tabular Q-learning on local 2D `HriFearEnv`; compare with fixed heuristic.
- Repo: https://github.com/fahradnamazov-ops/fear_mecanumbot

## Results (local)

Run: `python scripts/v1_final_demo.py` → `output/v1_summary.json`

| Metric | Value |
|--------|-------|
| Unit tests | 50 passed |
| Residual gap (person far) | ~0.47 |
| Q-learning delivery rate (eval) | 1.00 |
| Q episode steps | ~34 |
| Heuristic episode steps | ~85 |
| Near-collisions (Q policy) | 0 |

After the person leaves, proximity-only speed returns to maximum immediately; fear-modulated speed stays lower while `fear_level` decays.

## Software (local)

| Component | Status |
|-----------|--------|
| risk / fear / reward | done |
| Q-learning env + train | done |
| Residual demo | done |
| BT stubs + Nav2 avoid retreat | done |
| ROS bridge notes | done |
| `ros_draft/mecanumbot_fear_hri_behaviour/` | behaviours package |
| `sim_draft/fear_hri_brick_carry.yaml` | sim scenario |

## Limits

- Not run on Jetson / MuJoCo with full stack
- No merged PR into `fear_RL` or `mecanumbot_behaviours`
- Ethologist review pending
- freeze / catch_attention rare when policy avoids hit distance

## Next steps

1. Branch `mecanumbot_fear_hri_behaviour` in `mecanumbot_behaviours`
2. PR to Reha: LIDAR risk + discrete actions in `fear_RL`
3. Sim scenario + policy on `/scan`
4. Robot brick HRI on lab network

## References

Tovote et al. 2015; LeDoux 2014; Maroto-Gómez et al. 2024; Fear HRI protocol (MicroLab).
