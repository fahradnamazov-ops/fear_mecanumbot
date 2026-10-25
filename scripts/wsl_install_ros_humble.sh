#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export LANG=en_US.UTF-8

echo ">>> [1/5] apt update + locales"
sudo apt-get update -qq
sudo apt-get install -y -qq locales curl gnupg lsb-release software-properties-common ca-certificates
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

echo ">>> [2/5] add ROS 2 apt repository"
sudo apt-get install -y -qq curl
if [ ! -f /usr/share/keyrings/ros-archive-keyring.gpg ]; then
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

echo ">>> [3/5] apt update"
sudo apt-get update -qq

echo ">>> [4/5] install ROS Humble (this takes a while)"
sudo apt-get install -y \
  ros-humble-desktop \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-pip \
  python3-venv \
  python3-yaml \
  ros-humble-nav2-msgs \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-xacro \
  ros-humble-robot-state-publisher \
  ros-humble-tf2-ros \
  ros-humble-rviz2

echo ">>> [5/5] rosdep"
sudo rosdep init 2>/dev/null || true
rosdep update || true

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
python3 -m pip install --user -U pip
python3 -m pip install --user mujoco pyyaml py_trees py_trees_ros

echo ">>> DONE_ROS_INSTALL"
ros2 --help | head -2
python3 -c "import mujoco; print('mujoco', mujoco.__version__)"
