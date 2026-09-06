# fear_mecanumbot

Fear HRI V1 helpers for Mecanumbot.

Author: Fahrad Namazov

Teammate repos: pull + personal branch + PR only.

## Setup

**Important:** install deps **inside this repo** (`pip install -r requirements.txt`).  
A separate `(fear_rl)` env is not enough — pytest lives here.

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python scripts\check_setup.py
pytest -v
```

### Linux

```bash
cd fear_mecanumbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_setup.py
python -m pytest -q
python scripts/residual_fear_demo.py
python scripts/v1_final_demo.py
```

## Local vs robot

Local scripts use a **2D simulated person path** (geometry → min_range).  
On robot/sim: `/scan` + optional `people_fusion` — see `notes/LOCAL_VS_ROS.md`.

## Layout

| Path | Role |
|------|------|
| `fear_mecanumbot/` | risk, fear, reward, env, Q-learning, BT stubs |
| `ros_draft/` | Fear HRI behaviours package (for team integration) |
| `sim_draft/` | MuJoCo scenario YAML (for team integration) |
| `models/` | Q-table after train |
| `tests/` | unit tests |
| `scripts/` | demos |
| `notes/` | report, scope, status |

## V1

- Bricks to goal, person nearby (LIDAR risk)
- Continuous `fear_level`, slow decay
- Actions: freeze, avoid (Nav2 retreat), catch_attention, task

Repo: https://github.com/fahradnamazov-ops/fear_mecanumbot
