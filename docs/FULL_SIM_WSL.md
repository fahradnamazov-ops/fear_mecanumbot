# Full MuJoCo simulation (WSL)

ROS 2 Humble + Mecanumbot workspace is installed under WSL Ubuntu 22.04.

## One-shot launch (Fear activated)

From **Windows PowerShell**:

```bat
wsl -e bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_launch_fear_sim.sh"
```

Or inside WSL:

```bash
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_launch_fear_sim.sh"
```

This starts:

1. MuJoCo `truth_twin` with `scenario:=fear_hri_brick_carry`
2. Fear HRI tree reading `/mecanumbot/scan`

Success looks like:

```text
fear=100.0 risk=1.00 range=0.07 action=freeze
```

## Manual two-terminal launch

```bash
source /opt/ros/humble/setup.bash
source ~/mecanumbot_ws/install/setup.bash
export MUJOCO_GL=glfw   # or egl if no display

# terminal 1
ros2 launch mecanumbot_bringup sim.launch.py \
  backend:=mujoco mode:=truth_twin \
  scenario:=fear_hri_brick_carry show_viewer:=true use_rviz:=false

# terminal 2
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
```

## Rebuild after code changes

```bash
bash "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/wsl_build_workspace.sh"
```

## Workspace layout

`~/mecanumbot_ws/src` symlinks into `Desktop/AI Lab` packages (sim from `mecanumbot_remote`).

## Note

`mecanumbot_sensorproc_node` may print an error on some WSL setups; MuJoCo still publishes `/mecanumbot/scan` and Fear HRI still activates.
