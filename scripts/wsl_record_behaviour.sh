#!/usr/bin/env bash
set -eo pipefail
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${HOME}/.local/lib/python3.10/site-packages:${PYTHONPATH:-}"
export MUJOCO_GL=egl
python3 "/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/scripts/record_mujoco_behaviour.py"
