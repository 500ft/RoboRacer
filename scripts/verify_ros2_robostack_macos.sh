#!/usr/bin/env bash
set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ "${CONDA_DEFAULT_ENV:-}" != "f1tenth-ros2-verify" ]]; then
  echo "Activate the RoboStack environment first: conda activate f1tenth-ros2-verify" >&2
  exit 2
fi

python -m pip install -e . --no-deps
rm -rf ros2_ws/build ros2_ws/install ros2_ws/log
colcon --log-base ros2_ws/log build \
  --base-paths ros2_ws/src \
  --build-base ros2_ws/build \
  --install-base ros2_ws/install
source ros2_ws/install/setup.bash
ros2 launch f1tenth_modeling sysid_excitation.launch.py
python experiments/validate_sysid_excitation.py \
  --telemetry runs/ros2_sysid_steering_excitation/telemetry.csv \
  --quality runs/ros2_sysid_steering_excitation/quality_metrics.csv
