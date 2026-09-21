# Integration Guide

This document describes how the Fear HRI package relates to the Mecanumbot software ecosystem, how local testing differs from robot/simulation sensing, and how to copy draft artefacts into team repositories when maintainers request it.

---

## 1. Ecosystem map

| Layer | Repository / package | Role relative to Fear HRI |
|-------|----------------------|---------------------------|
| Onboard robot (Raspberry Pi / Jetson packages) | [Fortuz/mecanumbot](https://github.com/Fortuz/mecanumbot) | Hardware bring-up; not the primary home of MuJoCo scenarios |
| Remote PC + simulation | [Fortuz/mecanumbot_remote](https://github.com/Fortuz/mecanumbot_remote) (`mecanumbot_sim`) | **Target home for simulation scenarios** (confirmed by supervisor, Sep 2026) |
| Messages | [Fortuz/mecanumbot_msgs](https://github.com/Fortuz/mecanumbot_msgs) | Shared message types |
| Sensor processing | [hubaycsenge/mecanumbot_sensorprocess_smart](https://github.com/hubaycsenge/mecanumbot_sensorprocess_smart) | People fusion and related perception |
| Behaviour trees | [hubaycsenge/mecanumbot_behaviours](https://github.com/hubaycsenge/mecanumbot_behaviours) | Execution of freeze / avoid / catch_attention / task |
| Decision (this work) | [fahradnamazov-ops/fear_mecanumbot](https://github.com/fahradnamazov-ops/fear_mecanumbot) | Fear dynamics, reward, local RL, integration drafts |
| Legacy / alternate RL shell | [rehawild/fear_RL](https://github.com/rehawild/fear_RL) | Early Gym shell; Fear HRI logic was developed here instead for V1 |
| Web study platform | [rehawild/mecanumbot_web](https://github.com/rehawild/mecanumbot_web) | Separate guiding/HRI study; not required for Fear V1 |

**Process:** do not edit teammate `main` directly. Use a personal branch and pull request, or provide this repository for maintainers to copy from.

---

## 2. Local testing versus robot / simulation sensing

### 2.1 Local (this repository)

Scripts compute person distance from a **2D geometric trajectory**. They do not subscribe to ROS topics.

| Script | Purpose |
|--------|---------|
| `scripts/residual_fear_demo.py` | Residual caution versus proximity-only speed |
| `scripts/scan_fear_preview.py` | Fear update from synthetic range sequences |
| `scripts/train_hri_rl.py` / `run_hri_rl.py` | Train and run Q-learning |
| `scripts/v1_final_demo.py` | Tests + summary metrics → `output/v1_summary.json` |
| `scripts/check_setup.py` | Dependency sanity check |

### 2.2 Robot or MuJoCo truth twin

| Source | Role |
|--------|------|
| `/mecanumbot/scan` | Primary LaserScan; min range and closing speed |
| `/mecanumbot/subject_pose` or people fusion | Backup when the person leaves the LIDAR field of view |
| Nav2 `Approach` | Avoid retreat; retreat distance may scale with `fear_level` |
| Brick task behaviours | Existing movement / manipulation leaves in `mecanumbot_behaviours` |

Scan field-of-view and pose-fusion utilities are implemented in `fear_mecanumbot/sensing.py`.

---

## 3. Simulation scenario draft

**Source file:** `sim_draft/fear_hri_brick_carry.yaml`

**Intended destination:**

```text
mecanumbot_remote/mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml
```

The scenario places an exercising person on body `sim_human_0` with patrol motion, following the same schema as team scenarios such as `moving_human_patrol.yaml`. It does not copy proprietary simulation engine code; it only provides scenario configuration.

### Example launch (team workspace)

Exact launch file names may evolve with `mecanumbot_bringup`. A representative command used in the project is:

```bash
ros2 launch mecanumbot_bringup sim.launch.py \
  mode:=truth_twin \
  scenario:=fear_hri_brick_carry \
  use_rviz:=true
```

Verify:

```bash
ros2 topic echo /mecanumbot/scan --once
ros2 topic echo /sim/actors --once
```

---

## 4. Behaviour package draft

**Source tree:** `ros_draft/mecanumbot_fear_hri_behaviour/`

**Intended destination:** a new package under `hubaycsenge/mecanumbot_behaviours` (or equivalent workspace), built with `colcon`.

### Capabilities (draft)

- Subscribe to `/mecanumbot/scan`
- Update blackboard `fear_level` using shared fear logic
- Select among freeze / avoid / catch_attention / task
- Launch file: `launch/launch_fear_hri.launch.py`
- Thresholds: `config/fear_hri_constants.yaml`

### Build and run (after copy into a ROS 2 workspace)

```bash
colcon build --packages-select mecanumbot_fear_hri_behaviour
source install/setup.bash
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
```

Node logs are expected to report fear, range, and selected action.

### Avoid semantics

`avoid` should call Nav2 **Approach** toward a retreat pose, not a custom costmap inflation leaf. Retreat distance may increase with `fear_level`.

### Tree sketch

```text
ROOT
├── ParamsToBlackboard
├── UpdateFearFromRange
└── PolicyGate
    ├── Freeze
    ├── Avoid
    ├── CatchAttention
    └── TaskSequence
```

---

## 5. Suggested integration checklist

When the team schedules integration:

1. Copy `sim_draft/fear_hri_brick_carry.yaml` into `mecanumbot_remote` / `mecanumbot_sim`.
2. Copy `ros_draft/mecanumbot_fear_hri_behaviour` into the behaviours workspace; resolve package dependencies (`mecanumbot_movement_behaviours`, `mecanumbot_bt_config`, etc.).
3. Launch truth twin with the Fear scenario; launch the fear behaviour node.
4. Confirm `/mecanumbot/scan` updates fear and that avoid retreats via Nav2.
5. Record a short demonstration if required for HRI documentation.
6. Optionally port discrete actions and LIDAR-driven fear into other RL repositories if the team consolidates decision code.

---

## 6. Relationship to other RL repositories

| Repository | Relationship |
|------------|--------------|
| `fear_mecanumbot` (this) | Complete V1 fear model, local env, Q-learning, drafts |
| `rehawild/fear_RL` | Early continuous-control shell; fear spike was not LIDAR-driven HRI |
| `hubaycsenge/mecanumbot_RL` | Digital twin / MuJoCo tooling owned by the team |
| `rehawild/mecanumbot_web` | Browser-based guiding study; separate experiment |

Fear V1 decision logic should be treated as residing in **this repository** unless and until maintainers explicitly merge it elsewhere.
