# Fear HRI tree (V1)

New experiment package in `mecanumbot_behaviours`.

## Stack (Aug 2026)

| Topic | Use |
|-------|-----|
| Task + avoid | `mecanumbot_movement_behaviours.Approach` → `/navigate_to_pose` |
| Freeze / turn | `/cmd_vel` via `SmoothTurner`; cancel Nav2 on freeze |
| catch_attention | `DogBehaviourSequence` + `RelativeTurnPattern` |
| Params | `mecanumbot_bt_config` |
| LED | skip |
| Ostensive tree | different experiment |

avoid = Nav2 Approach to retreat pose.

## Leaves

freeze, avoid, catch_attention, go_to_brick, grab, go_to_goal, release

## Sketch

```text
ROOT
├── ParamsToBlackboard
├── UpdateFearFromLidar
└── PolicyGate
    ├── Freeze
    ├── Avoid
    ├── CatchAttention
    └── TaskSequence
```

Local stubs: `fear_mecanumbot/fear_hri_bt.py`  
Package source: `ros_draft/mecanumbot_fear_hri_behaviour/`
