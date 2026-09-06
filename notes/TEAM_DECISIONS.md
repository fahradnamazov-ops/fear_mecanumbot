# Team decisions

Aug 2026

## Fear HRI

- `fear_level` in observation, slow decay
- trigger: LIDAR risk / near-collision (not IMU pickup)
- catch_attention = human looks at the robot
- skip LED and demo package
- own Fear HRI tree
- avoid = Nav2 Approach retreat

## Stack

- decide: `fear_RL` or local env
- execute: new package in `mecanumbot_behaviours`
- sim: `Fortuz/mecanumbot` / `mecanumbot_sim`
- no cxrlgym

## Process

Personal branch + PR on teammate repos.
