# ROS 2 Verification Summary

Both supported ROS 2 paths were verified independently on 2026-06-09.

| Path | Purpose | Result | Reproduce |
| --- | --- | --- | --- |
| RoboStack ROS 2 Humble on macOS | Fast local development and validation | Passed | `bash scripts/verify_ros2_robostack_macos.sh` |
| Official ROS 2 Humble on Ubuntu 22.04 | RoboRacer-compatible deployment reference | Passed | `bash scripts/verify_ros2_ubuntu_lima.sh` |

## Which Environment To Use

Use RoboStack when:

- developing on the current Apple Silicon Mac
- iterating on nodes, topics, telemetry, or offline model validation
- avoiding a VM for routine work

Use official Ubuntu ROS 2 Humble when:

- preparing for RoboRacer hardware
- checking compatibility with the expected Ubuntu/ROS deployment stack
- validating before moving code to a Jetson or other Ubuntu computer

## Shared Verified Behavior

Both environments proved:

- `colcon` builds `f1tenth_modeling`
- `gym_bridge_node` launches and publishes internal state/odometry
- `sysid_excitation_node` publishes chirp steering commands
- the experiment starts on the first state sample
- the 20-second excitation completes without collision or steering saturation
- launch shuts down both nodes cleanly
- generated telemetry passes `experiments/validate_sysid_excitation.py`

## Switching

RoboStack:

```bash
conda activate f1tenth-ros2-verify
bash scripts/verify_ros2_robostack_macos.sh
```

Official Ubuntu:

```bash
bash scripts/verify_ros2_ubuntu_lima.sh
```

No model, telemetry schema, or validation-script changes are required when switching.
