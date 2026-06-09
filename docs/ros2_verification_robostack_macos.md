# ROS 2 Verification: RoboStack Humble on macOS

## Verified Environment

- Verification date: 2026-06-09
- Host: Apple Silicon macOS 14.7.3
- Runtime: RoboStack ROS 2 Humble
- Conda environment: `f1tenth-ros2-verify`
- Python: 3.11
- `ros-humble-ros-base`: 0.10.0
- `ros-humble-rclpy`: 3.3.16
- `ros-humble-ackermann-msgs`: 2.0.2
- Gym compatibility runtime: `gym==0.26.2`

## Recreate

```bash
conda env create -f environments/ros2_robostack_humble_macos.yml
conda activate f1tenth-ros2-verify
bash scripts/verify_ros2_robostack_macos.sh
```

RoboStack's `ament_python` combination did not support `colcon --symlink-install`, so the verified script intentionally uses a normal `colcon build`.

## Verified Result

The package built successfully, both ROS 2 nodes launched, the excitation node completed cleanly, and the launch system shut down the Gym bridge cleanly.

The generated ROS 2 telemetry passed the shared SysID validator:

| Metric | Verified value |
| --- | ---: |
| Duration | 20.000529 s |
| Samples | 1993 |
| Collision | 0 |
| Speed CV | 0.076247 |
| Steering range | 0.128000 rad |
| Yaw-rate range | 0.567181 rad/s |
| Steering saturation fraction | 0 |

## Compatibility Notes

- The repository's F1TENTH Gym uses the pre-0.26 Gym reset/step API.
- The ROS 2 Gym bridge disables modern Gym's checker and uses the registered environment's unwrapped implementation.
- Experiment timing begins when the first internal-state message arrives, preventing bridge startup time from shortening the excitation dataset.
- This environment is appropriate for macOS development and model-validation work. Use official Ubuntu verification before hardware-facing deployment.
