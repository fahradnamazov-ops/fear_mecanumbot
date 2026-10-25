#!/usr/bin/env bash
set +e
# Kill by exact node names via pgrep -f carefully, excluding this script.
me=$$
for pat in \
  'fear_hri_bt_node' \
  'mecanumbot_sim_mujoco_io_node' \
  'mecanumbot_sim_nav_shim_node' \
  'launch_fear_hri.launch.py' \
  'sim.launch.py'
do
  pgrep -af "$pat" | while read -r pid rest; do
    if [[ "$pid" != "$me" ]] && [[ "$rest" != *wsl_kill_fear* ]]; then
      kill "$pid" 2>/dev/null || true
    fi
  done
done
sleep 2
echo KILL_DONE
pgrep -af 'fear_hri_bt_node|mecanumbot_sim_mujoco|nav_shim|launch_fear_hri|sim.launch' || echo 'no leftover matches'
