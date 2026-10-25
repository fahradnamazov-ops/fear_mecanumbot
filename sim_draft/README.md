# Simulation scenario draft (synced with Fortuz/mecanumbot_remote)

`fear_hri_brick_carry.yaml` matches the scenario shipped in:

```text
mecanumbot_remote/mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml
```

It places the exercising person on `sim_human_0` between start and goal brick areas so residual fear can be exercised without hardware.

`mujoco/mujoco_io_node.py` and `mujoco/mecanumbot.xml` are the brick-carry runtime used for that run. Copy them over the same paths in `mecanumbot_sim`. They keep a tipped chassis upright and carry a gripped cube onto the goal mat.

## Activate fear in simulation

Terminal 1 — MuJoCo truth twin with the Fear scene (no other BT):

```bash
ros2 launch mecanumbot_bringup sim.launch.py \
  mode:=behaviour \
  condition:=none \
  scenario:=fear_hri_brick_carry
```

Gazebo backend:

```bash
ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=gazebo \
  mode:=behaviour \
  condition:=none \
  scenario:=fear_hri_brick_carry
```

Terminal 2 — Fear HRI tree (after building `mecanumbot_fear_hri_behaviour`):

```bash
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
```

Expect log lines: `fear=… risk=… range=… action=…`

## Offline check (no ROS)

From `fear_mecanumbot`:

```bash
pip install pyyaml
python scripts/sim_fear_activate_demo.py
```
