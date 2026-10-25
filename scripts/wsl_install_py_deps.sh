#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
sudo apt-get install -y ros-humble-py-trees ros-humble-py-trees-ros || sudo apt-get install -y python3-py-trees || true
python3 -m pip install --user mujoco
source /opt/ros/humble/setup.bash
python3 -c "import mujoco; print('mujoco', mujoco.__version__)"
python3 -c "import py_trees; print('py_trees ok')" || true
echo DONE_PY_DEPS
