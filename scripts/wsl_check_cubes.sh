#!/usr/bin/env bash
source /opt/ros/humble/setup.bash
source ~/mecanumbot_ws/install/setup.bash
timeout 3 ros2 topic echo /sim/props --once 2>/dev/null > /tmp/props.txt
python3 - <<'PY'
from pathlib import Path
text = Path("/tmp/props.txt").read_text()
blocks = text.split("- id:")
for b in blocks:
    if "kind: cube" not in b:
        continue
    name = x = y = ""
    for line in b.splitlines():
        s = line.strip()
        if s.startswith("name:"):
            name = s.split(":", 1)[1].strip()
        if s.startswith("x:") and not x:
            x = s.split(":", 1)[1].strip()
        elif s.startswith("y:") and x and not y:
            y = s.split(":", 1)[1].strip()
            break
    print(f"{name}: x={x} y={y}")
PY
grep -E "Released brick at goal|task:done|Grabbed " \
  /mnt/c/Users/Fahrad/.cursor/projects/c-Users-Fahrad-Desktop-AI-Lab/terminals/656219.txt \
  | tail -20
