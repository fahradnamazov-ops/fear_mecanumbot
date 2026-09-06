# Local 2D env vs ROS / sim

## Local testing

Scripts use a 2D person path (geometry → min_range), not raw `LaserScan`.

| Script | Role |
|--------|------|
| `residual_fear_demo.py` | Residual gap demo |
| `scan_fear_preview.py` | Scan-style ranges → fear |
| `v1_final_demo.py` | Full summary + pytest |

Install deps in this repo: `pip install -r requirements.txt`

## On robot / sim

| Source | Role |
|--------|------|
| `/mecanumbot/scan` | Primary range + closing speed |
| `/mecanumbot/subject_pose` | Backup when LIDAR misses person |
| Nav2 Approach | Avoid retreat; distance ∝ `fear_level` |

See `notes/SIM_INTEGRATION.md`.
