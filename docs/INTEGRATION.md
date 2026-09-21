# Integration Guide

How Fear HRI connects to Mecanumbot simulation and behaviour trees, and how to **activate fear in the simulated environment** (Csenge’s requirement).

---

## 1. Ecosystem

| Layer | Repository | Role |
|-------|------------|------|
| Simulation (MuJoCo + Gazebo) | [Fortuz/mecanumbot_remote](https://github.com/Fortuz/mecanumbot_remote) (`mecanumbot_sim`) | Publishes `scan`; hosts `fear_hri_brick_carry` |
| Launch orchestration | `mecanumbot_bringup` (`sim.launch.py`) | Starts sim backends and modes |
| Behaviour trees | [hubaycsenge/mecanumbot_behaviours](https://github.com/hubaycsenge/mecanumbot_behaviours) | Fear package on branch `fahrad/fear_hri_behaviour` |
| Fear model + drafts | [fahradnamazov-ops/fear_mecanumbot](https://github.com/fahradnamazov-ops/fear_mecanumbot) | Dynamics, RL, `ros_draft/`, offline demo |

Both **MuJoCo** and **Gazebo** backends live under `mecanumbot_remote` and expose the same `scan` / `cmd_vel` interface.

---

## 2. Local testing versus sim sensing

| Mode | What drives range |
|------|-------------------|
| Offline demo | Scenario waypoints → Euclidean range (`scripts/sim_fear_activate_demo.py`) |
| Unit tests / Q-learning | 2D geometric person in `HriFearEnv` |
| MuJoCo / Gazebo | `/mecanumbot/scan` LaserScan |

---

## 3. Activate fear in simulation

The scenario YAML alone is not enough. Fear must run as a node that reads `scan` and logs / acts.

### Terminal 1 — sim scene (no other BT)

```bash
ros2 launch mecanumbot_bringup sim.launch.py \
  mode:=behaviour \
  condition:=none \
  scenario:=fear_hri_brick_carry
```

Gazebo:

```bash
ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=gazebo \
  mode:=behaviour \
  condition:=none \
  scenario:=fear_hri_brick_carry
```

### Terminal 2 — Fear HRI tree

```bash
colcon build --packages-select mecanumbot_fear_hri_behaviour
source install/setup.bash
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
```

**Success:** logs like `fear=42.0 risk=0.61 range=0.48 action=avoid`.

Package sources:

- `fear_mecanumbot/ros_draft/mecanumbot_fear_hri_behaviour/`
- or `mecanumbot_behaviours` branch `fahrad/fear_hri_behaviour`

---

## 4. Offline activation (this PC, no ROS)

```bash
pip install -r requirements.txt
python scripts/sim_fear_activate_demo.py
```

Replays `fear_hri_brick_carry` person patrol against a robot on the carry line and prints fear / action over time.

---

## 5. Behaviour tree (activation V1)

```text
ROOT
├── LoadFearParams
└── FearLoop
    ├── UpdateFearFromScan
    ├── SelectFearAction
    ├── LogFearState
    └── ExecuteSelectedAction   # freeze / reverse avoid / yaw cue via /cmd_vel
```

Each tick logs fear. Actions return SUCCESS so the loop does not stall.

---

## 6. Scenario file

Shipped: `mecanumbot_remote/.../fear_hri_brick_carry.yaml`  
Synced copy: `sim_draft/fear_hri_brick_carry.yaml`
