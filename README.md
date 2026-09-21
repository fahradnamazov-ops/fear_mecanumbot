# Fear HRI for Mecanumbot

**Author:** Fahrad Namazov  
**Affiliation:** MicroLab · Mecanumbot project  
**Repository:** https://github.com/fahradnamazov-ops/fear_mecanumbot  

Python package for a biologically motivated **fear** state in human–robot interaction (HRI). The robot maintains a continuous internal `fear_level` driven by proximity risk, learns discrete defensive and task actions with tabular Q-learning, and exposes draft ROS 2 / simulation artefacts for integration with the Mecanumbot stack.

---

## Research question

Can a continuous internal fear variable produce **residual caution** after a nearby person steps away—behaviour that persists longer than proximity-only safety rules?

## Scope (V1)

| Element | Specification |
|---------|----------------|
| Scenario | Brick-carry task with a person nearby |
| Trigger | Minimum range and closing speed (LIDAR-style risk); near-collision spike at ≤ 0.25 m. Not IMU pickup. |
| State | Continuous `fear_level` ∈ [0, 100] with slow decay |
| Actions | `freeze`, `avoid` (Nav2 Approach retreat), `catch_attention`, `task` |
| Policy | Tabular Q-learning on a local 2D Gymnasium environment |
| Out of scope (V1) | LED signalling; ethologist evaluation; merged PRs into team repositories |

## Features

- Risk mapping from range and closing speed (`risk.py`)
- Fear dynamics with spike, rise, and decay (`fear_dynamics.py`)
- Structured reward terms for near-collision, fear cost, and task progress (`reward.py`)
- `HriFearEnv` Gymnasium environment and Q-learning agent
- Residual-caution demonstration versus proximity-only speed
- Draft ROS 2 behaviour package (`ros_draft/`) and MuJoCo scenario YAML (`sim_draft/`)

## Documentation

| Document | Description |
|----------|-------------|
| [docs/TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md) | Full method, parameters, results, biology mapping, limitations |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | Local vs ROS sensing, team repositories, launch and copy steps |

## Repository layout

```text
fear_mecanumbot/          Core Python package
tests/                    Unit tests (pytest)
scripts/                  Demos and training utilities
models/                   Trained Q-table artefacts
ros_draft/                Draft ROS 2 Fear HRI behaviour package
sim_draft/                Draft simulation scenario (sim_human_0 patrol)
docs/                     Technical report and integration guide
```

## Requirements

- Python 3.10+ recommended
- Dependencies listed in `requirements.txt` (`gymnasium`, `numpy`, `pytest`)

## Setup

Install dependencies **inside this repository**. A separate Conda or venv used only for other Mecanumbot packages is not sufficient if `pytest` is missing here.

### Windows

```bat
cd fear_mecanumbot
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python scripts\check_setup.py
pytest -v
```

### Linux / macOS

```bash
cd fear_mecanumbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_setup.py
python -m pytest -q
```

## Running demos

```bash
# Residual caution (fear-modulated speed vs proximity-only)
python scripts/residual_fear_demo.py

# Full V1 summary: tests + residual gap + Q vs heuristic episode
python scripts/v1_final_demo.py

# Train / evaluate tabular Q-learning
python scripts/train_hri_rl.py
python scripts/run_hri_rl.py

# Preview fear update from scan-style range sequences
python scripts/scan_fear_preview.py
```

Results from `v1_final_demo.py` are written to `output/v1_summary.json` (gitignored).

## Activate fear in simulation

Offline (this PC, no ROS):

```bash
python scripts/sim_fear_activate_demo.py
```

Full MuJoCo / Gazebo (ROS 2 Humble lab machine): see [docs/INTEGRATION.md](docs/INTEGRATION.md).


## Team repositories (read-only from this project)

Integration drafts in this repository are intended to be **copied** into the team stack when maintainers request it. This project does not modify teammate `main` branches directly.

| Component | Repository |
|-----------|------------|
| Simulation package | [Fortuz/mecanumbot_remote](https://github.com/Fortuz/mecanumbot_remote) (`mecanumbot_sim`) |
| Behaviour trees | [hubaycsenge/mecanumbot_behaviours](https://github.com/hubaycsenge/mecanumbot_behaviours) |
| Sensor processing | [hubaycsenge/mecanumbot_sensorprocess_smart](https://github.com/hubaycsenge/mecanumbot_sensorprocess_smart) |
| Onboard robot packages | [Fortuz/mecanumbot](https://github.com/Fortuz/mecanumbot) |

## Licence and contribution

Work produced for the MicroLab Mecanumbot Fear HRI track. Prefer personal branches and pull requests when contributing to shared team repositories.
