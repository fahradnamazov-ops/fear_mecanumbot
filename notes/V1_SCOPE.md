# V1 scope

Fahrad Namazov · Csenge Hubay · Reha · deadline 31 Aug 2026

## Scenario

Person follows exercise videos (calf-level movement). Robot carries bricks to one goal.

## Fear

Continuous `fear_level` from LIDAR distance / closing speed. Near-collision spike. Slow decay after the person steps away (not the same as proximity-only slow-down).

## Actions

freeze · avoid · catch_attention (human looks at robot) · task (brick pipeline)

Skip: LED, pay_attention unless asked.

## Software

1. Local / `fear_RL` for decisions  
2. New Fear HRI tree in `mecanumbot_behaviours` (`mecanumbot_bt_config` + `mecanumbot_movement_behaviours`)  
3. Thin ROS2 Humble bridge  
4. Sim via `Fortuz/mecanumbot` → `mecanumbot_sim` (MuJoCo)  

avoid = Nav2 `Approach` retreat (not a custom inflation leaf).
## By 31 Aug

Fear + residual effect, policy, BT leaves (PR), bridge path, brick HRI (sim or robot), short report.
