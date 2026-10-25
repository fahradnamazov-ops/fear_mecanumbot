#!/usr/bin/env bash
set -euo pipefail

LAB="/mnt/c/Users/Fahrad/Desktop/AI Lab"
WS="${HOME}/mecanumbot_ws"
mkdir -p "${WS}/src"
cd "${WS}/src"

link() {
  local name="$1"
  local target="$2"
  if [ ! -e "$target" ]; then
    echo "MISSING: $target"
    return 1
  fi
  ln -sfn "$target" "$name"
  echo "linked $name -> $target"
}

# Messages
if [ -d "${LAB}/mecanumbot_msgs" ]; then
  link mecanumbot_msgs "${LAB}/mecanumbot_msgs"
else
  link mecanumbot_msgs "${LAB}/mecanumbot/mecanumbot_msgs"
fi

link mecanumbot_description "${LAB}/mecanumbot/mecanumbot_description"
link mecanumbot_core "${LAB}/mecanumbot/mecanumbot_core"
link mecanumbot_bringup "${LAB}/mecanumbot/mecanumbot_bringup"

# Simulation from remote repo (authoritative)
link mecanumbot_sim "${LAB}/mecanumbot_remote/mecanumbot_sim"

# Fear behaviour stack
link mecanumbot_bt_config "${LAB}/mecanumbot_behaviours/mecanumbot_bt_config"
link mecanumbot_movement_behaviours "${LAB}/mecanumbot_behaviours/mecanumbot_movement_behaviours"
link mecanumbot_fear_hri_behaviour "${LAB}/mecanumbot_behaviours/mecanumbot_fear_hri_behaviour"
link mecanumbot_leading_behaviour "${LAB}/mecanumbot_behaviours/mecanumbot_leading_behaviour"

echo "=== src ==="
ls -la
test -f mecanumbot_sim/config/sim_scenarios/fear_hri_brick_carry.yaml
echo ">>> DONE_WS_LINKS"
