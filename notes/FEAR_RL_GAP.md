# Gap vs Reha `fear_RL`

Integrate via branch + PR. Do not edit `main` directly.

## Reha status

GitHub `rehawild/fear_RL` has one commit (`Initial commit`):

- Gymnasium `MecanumbotFearEnv` — continuous velocity actions (2D box)
- Fear spike is **manual / config**, not LIDAR-driven
- No brick HRI, no discrete freeze/avoid/catch_attention/task actions
- Reha offered repo access on Teams — **no new commits since initial env**

So Reha delivered the **base RL shell**; **HRI + LIDAR fear integration is still open** (your PR or joint branch).

## Needed in fear_RL

1. Person / obstacle min range each step (LIDAR or fused pose)
2. Near-collision spike from distance
3. Optional brick carry scenario
4. Discrete actions freeze / avoid / catch_attention / task

## Local until merged

`fear_mecanumbot` — `HriFearEnv`, Q-learning, same fear/risk/reward terms, residual demo.

Reference implementation to port: `fear_mecanumbot/fear_mecanumbot/` + `sensing.py`.
