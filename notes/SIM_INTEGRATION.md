# Sim integration

## Repos

| Layer | Repo | Piece |
|-------|------|-------|
| Sim + `/mecanumbot/scan` | `Fortuz/mecanumbot_remote` (`mecanumbot_sim`) | Scenario copy/PR (Csenge: final home) |
| Digital twin scripts | `hubaycsenge/mecanumbot_RL` | launch helpers if still used |
| Fear logic | `fear_mecanumbot` | tests + sensing |
| Fear HRI BT | `hubaycsenge/mecanumbot_behaviours` | draft in `ros_draft/` |

Csenge (Sep 2026): sims were briefly in `mecanumbot`, then **`mecanumbot_remote/mecanumbot_sim`**.

## Scenario

`sim_draft/fear_hri_brick_carry.yaml` → copy to:

`mecanumbot_remote/mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml`

Only when the team asks — AI lab deliverable is already accepted.

## Launch sim

```bash
ros2 launch mecanumbot_bringup sim.launch.py \
  mode:=truth_twin \
  scenario:=fear_hri_brick_carry \
  use_rviz:=true
```

## Launch fear tree

After building behaviours workspace:

```bash
ros2 launch mecanumbot_fear_hri_behaviour launch_fear_hri.launch.py
```

## Verify

```bash
ros2 topic echo /mecanumbot/scan --once
ros2 topic echo /sim/actors --once
```

Logs from `fear_hri_bt_node` show `fear=… range=… action=…`.

## Sensor plan

- Primary: `/mecanumbot/scan`
- Backup: `/mecanumbot/subject_pose` when turned away
- Avoid: Nav2 Approach; retreat distance scales with `fear_level`

## PR checklist

1. Open PR: scenario → `mecanumbot`
2. Open PR: `mecanumbot_fear_hri_behaviour` → `mecanumbot_behaviours`
3. Record sim demo → update report + Trello HRI
