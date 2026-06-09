# ROS 2 Verification: Official Humble on Ubuntu 22.04

## Verified Environment

- Verification date: 2026-06-09
- Guest OS: Ubuntu 22.04.5 LTS ARM64
- Runtime: ROS 2 Humble installed from the official ROS apt repository
- VM runtime used for verification: Lima on Apple Silicon
- Python: Ubuntu system Python 3
- `ros-humble-ros-base`: `0.10.0-1jammy.20260426.092717`
- `ros-humble-rclpy`: `3.3.21-1jammy.20260421.034905`
- `ros-humble-ackermann-msgs`: `2.0.2-3jammy.20260416.055921`
- Gym compatibility runtime: `gym==0.26.2`

This is independent of RoboStack. It verifies the official Ubuntu/ROS deployment path expected for RoboRacer hardware-facing work.

## Recreate With Lima

Install Lima if required:

```bash
brew install lima
```

Run the complete setup/build/launch/validation flow:

```bash
bash scripts/verify_ros2_ubuntu_lima.sh
```

The first run creates an Ubuntu 22.04 ARM64 VM named `f1tenth-ubuntu22`, installs ROS 2 Humble from `packages.ros.org`, copies the repository into the VM, and runs the verification script.

## Recreate On Existing Ubuntu 22.04

```bash
bash scripts/setup_ros2_ubuntu_humble.sh
bash scripts/verify_ros2_ubuntu_humble.sh
```

## Verified Result

The package built successfully with official ROS 2 Humble. Both nodes launched, exchanged commands/state, completed the excitation run, and shut down cleanly.

The generated telemetry passed the shared SysID validator:

| Metric | Verified value |
| --- | ---: |
| Duration | 19.993934 s |
| Samples | 1996 |
| Collision | 0 |
| Speed CV | 0.076189 |
| Steering range | 0.128000 rad |
| Yaw-rate range | 0.567181 rad/s |
| Steering saturation fraction | 0 |
