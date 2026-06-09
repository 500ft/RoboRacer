#!/usr/bin/env bash
set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.local/bin:$PATH"

python3 -m pip install --user -e . --no-deps
source /opt/ros/humble/setup.bash
rm -rf ros2_ws/build ros2_ws/install ros2_ws/log
colcon --log-base ros2_ws/log build \
  --base-paths ros2_ws/src \
  --build-base ros2_ws/build \
  --install-base ros2_ws/install
source ros2_ws/install/setup.bash
ros2 launch f1tenth_modeling sysid_excitation.launch.py
python3 experiments/validate_sysid_excitation.py \
  --telemetry runs/ros2_sysid_steering_excitation/telemetry.csv \
  --quality runs/ros2_sysid_steering_excitation/quality_metrics.csv
