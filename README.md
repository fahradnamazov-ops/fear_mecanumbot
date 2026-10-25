# Fear HRI for Mecanumbot

Fahrad Namazov · MicroLab, Eötvös Loránd University  
https://github.com/fahradnamazov-ops/fear_mecanumbot

The robot carries bricks while a person moves nearby. A continuous `fear_level` (0–100) rises with LIDAR range and closing speed, spikes at 0.25 m or closer, and decays slowly. After the person is far again, fear-modulated speed stays about 0.47 below a proximity-only controller.

A Double DQN (numpy MLP) chooses `freeze`, `avoid`, `catch_attention`, or a lane: `task_middle`, `task_north`, `task_south`. Lane cost is travel time plus a blockage cost from the person’s current position. The robot does not predict when the person will leave, and it does not run a fixed wait timer. `catch_attention` is used on the real robot and masked in simulation.

The setup follows the internal-variable idea in Maroto-Gómez, Malfaz, Castro-González, Álvarez Arias, and Salichs, IEEE Access, 2024. This project uses one variable, fear, on the MicroLab Mecanumbot.

## Results (6 October 2026)

| Check | Result |
| --- | --- |
| Tests | 58 passed |
| Offline Double DQN | delivery 1.00, near collisions 0.00, about 12.2 steps |
| Live MuJoCo | 4/4 bricks, `policy=rl_dqn` |

Log: [evidence/EVIDENCE.txt](evidence/EVIDENCE.txt). Numbers: [models/hri_dqn_eval.json](models/hri_dqn_eval.json). Clip: `video/FearHRI_DoubleDQN_demo_for_professor.mp4`. Method: [docs/TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md).

## Run offline

Python 3.10+.

```bash
cd fear_mecanumbot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python scripts/validate_dqn.py
python scripts/validate_route_cost.py
python scripts/residual_fear_demo.py
```

`output/` is gitignored.

## Simulation

ROS 2 Humble on the lab machine. Steps: [docs/INTEGRATION.md](docs/INTEGRATION.md) and [docs/HOW_TO_RUN.txt](docs/HOW_TO_RUN.txt).

```bash
bash scripts/wsl_e2e_dqn.sh
```

## Where the pieces live

| Path | Contents |
| --- | --- |
| `fear_mecanumbot/` | Fear dynamics, environment, Double DQN |
| `ros_draft/` | ROS 2 behaviour package used in the October run |
| `sim_draft/` | `fear_hri_brick_carry` scenario and the MuJoCo files from that run |
| `models/` | `hri_dqn.npz` |

The behaviour package is also on branch `fahrad/fear_hri_behaviour` in [hubaycsenge/mecanumbot_behaviours](https://github.com/hubaycsenge/mecanumbot_behaviours). The scenario YAML matches [Fortuz/mecanumbot_remote](https://github.com/Fortuz/mecanumbot_remote). This repository does not commit to those `main` branches.

## Licence

MicroLab Mecanumbot project. Apache-2.0 on the ROS package (`ros_draft/`).
