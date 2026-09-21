# Simulation scenario draft

## File

`fear_hri_brick_carry.yaml` — person actor on `sim_human_0` with patrol motion near the robot work area.

## Destination

Copy into the team simulation package:

```text
Fortuz/mecanumbot_remote → mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml
```

The YAML follows the same actor schema as existing team scenarios (for example `moving_human_patrol.yaml`). It configures the scenario only; it does not embed simulation engine code.

## Usage

See the parent repository document `docs/INTEGRATION.md` for launch commands and verification steps.
