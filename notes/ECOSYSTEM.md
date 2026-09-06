# Mecanumbot ecosystem

| What | Repo | Owner |
|------|------|-------|
| Main page | https://fortuz.github.io/ | Balázs |
| Onboard (Pi) | https://github.com/Fortuz/mecanumbot | Balázs |
| Remote PC + sim | https://github.com/Fortuz/mecanumbot_remote (`mecanumbot_sim`) | Balázs / Csenge |
| Messages | https://github.com/Fortuz/mecanumbot_msgs | Balázs |
| Microcontrollers | https://github.com/Fortuz/mecanumbot_microcontrollers | Balázs |
| Sensor processing | https://github.com/hubaycsenge/mecanumbot_sensorprocess_smart | Csenge |
| Behaviour trees | https://github.com/hubaycsenge/mecanumbot_behaviours | Csenge |
| Fear RL env | https://github.com/rehawild/fear_RL | Reha |
| Fear HRI (this work) | https://github.com/fahradnamazov-ops/fear_mecanumbot | Fahrad |

## Fear HRI wiring

| Layer | Package | Role |
|-------|---------|------|
| Sim / I/O | `mecanumbot_sim`, `mecanumbot_bringup` | `/scan`, `/amcl_pose` |
| Perception | `mecanumbot_sensorprocess_smart` | people fusion |
| Decide | `fear_RL` or `fear_mecanumbot` | `fear_level`, actions |
| Execute | new package in `mecanumbot_behaviours` | freeze / avoid / catch_attention / task |
| Movement | `mecanumbot_movement_behaviours` | `Approach`, Nav2 |
| Config | `mecanumbot_bt_config` | YAML → blackboard |

Sim: `ros2 launch mecanumbot_bringup sim.launch.py`

Edit teammate repos via personal branch + PR only.
