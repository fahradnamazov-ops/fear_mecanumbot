# mecanumbot_fear_hri_behaviour

Draft ROS 2 package for the Mecanumbot **Fear HRI** experiment. It is developed in this repository and intended to be copied into the team `mecanumbot_behaviours` workspace when maintainers integrate the feature.

## Purpose

1. Subscribe to `/mecanumbot/scan` (and related interfaces as wired in the draft).
2. Maintain a continuous `fear_level` on the behaviour-tree blackboard.
3. Select among `freeze`, `avoid`, `catch_attention`, and `task`.
4. Execute avoid as a Nav2 Approach retreat when connected to the movement stack.

## Package layout

```text
config/fear_hri_constants.yaml     Thresholds and node parameters
launch/launch_fear_hri.launch.py   Launch entry point
mecanumbot_fear_hri_behaviour/
  behaviours/                      Fear update, actions, ROS interfaces
  tree_nodes/                      Tree assembly helpers
```

## Build (in a ROS 2 Humble workspace)

Place this package under `src/`, install dependencies used by the Mecanumbot behaviours stack, then:

```bash
colcon build --packages-select mecanumbot_fear_hri_behaviour
source install/setup.bash
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
```

## Status

This is an **integration draft**. Full closed-loop validation requires the team simulation (`mecanumbot_sim` under `mecanumbot_remote`) and existing movement / BT configuration packages. See `docs/INTEGRATION.md` in the parent repository.
