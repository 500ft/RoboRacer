#!/usr/bin/env bash
set -eo pipefail

if [[ "$(source /etc/os-release && echo "$VERSION_CODENAME")" != "jammy" ]]; then
  echo "This setup script requires Ubuntu 22.04 Jammy." >&2
  exit 2
fi

sudo apt-get update
sudo apt-get install -y software-properties-common curl
sudo add-apt-repository universe -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null

sudo apt-get update
sudo apt-get install -y \
  ros-humble-ros-base \
  ros-dev-tools \
  ros-humble-ackermann-msgs \
  python3-pip \
  python3-numpy \
  python3-scipy \
  python3-numba \
  python3-pil \
  python3-yaml \
  python3-pandas

python3 -m pip install --user "gym==0.26.2" "pyglet<1.5" PyOpenGL cloudpickle
