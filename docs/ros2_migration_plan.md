# ROS 2 Migration Plan

## Purpose

The current project remains a Python/F1TENTH Gym evidence pipeline. The ROS 2 migration adds a runtime layer beside that pipeline so commands, vehicle state, and excitation data can move through topics before the same offline validation and fitting logic is reused.

This is not a wholesale rewrite. The existing Gym scripts remain the reference baseline.

## Current ROS 2 Scope

The first ROS 2 package is `ros2_ws/src/f1tenth_modeling`.

It contains:

- `gym_bridge_node`: wraps F1TENTH Gym behind ROS 2 topics.
- `sysid_excitation_node`: publishes chirp-steering commands and logs excitation telemetry.
- `sysid_excitation.launch.py`: launches the bridge and excitation node together.
- `sysid_excitation.yaml`: records runtime parameters and topic names.

## Topic Contract

### Command Topic

`/drive`

Message type:

```text
ackermann_msgs/AckermannDriveStamped
```

Fields used:

| Field | Meaning |
| --- | --- |
| `drive.steering_angle` | Environment-level steering command, logged as `command_steer_rad` |
| `drive.speed` | Environment-level speed command, logged as `command_speed_mps` |

These are commands passed to the environment. They are not treated as internal dynamic-model inputs for future fitting.

### Internal State Topic

`/f1tenth/internal_state`

Message type:

```text
std_msgs/Float64MultiArray
```

State order:

```text
[X, Y, delta, v, psi, r, beta]
```

Telemetry mapping:

| State entry | CSV column |
| --- | --- |
| `X` | `x_m` |
| `Y` | `y_m` |
| `delta` | `steer_rad` |
| `v` | `speed_mps` |
| `psi` | `theta_rad` |
| `r` | `yaw_rate_radps` |
| `beta` | `slip_angle_rad` |

Derived columns:

| Column | Definition |
| --- | --- |
| `vx_mps` | `speed_mps * cos(slip_angle_rad)` |
| `vy_mps` | `speed_mps * sin(slip_angle_rad)` |
| `steer_vel_radps` | finite difference of achieved `steer_rad` |
| `accel_x_mps2` | finite difference of achieved `speed_mps` |

### Odometry Topic

`/ego_racecar/odom`

Message type:

```text
nav_msgs/Odometry
```

This topic is for standard ROS consumers. The SysID data logger uses `/f1tenth/internal_state` because the slip angle and steering state are required for fitting.

## Build

From a ROS 2 environment with this repository as the working directory:

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

The Python dependencies from the original Gym workflow are still required because the bridge node runs F1TENTH Gym internally.

## Run

From the repository root after sourcing the ROS 2 workspace:

```bash
ros2 launch f1tenth_modeling sysid_excitation.launch.py
```

Default outputs are written to:

```text
runs/ros2_sysid_steering_excitation/
reports/ros2_sysid_steering_excitation.md
```

Generated runtime outputs remain ignored by git unless explicitly staged.

## Quality Gate

The ROS 2 logger preserves the same telemetry schema as the offline SysID excitation script. After a ROS 2 run, the existing validation logic can be adapted to point at:

```text
runs/ros2_sysid_steering_excitation/telemetry.csv
```

Run the shared validator with:

```bash
python experiments/validate_sysid_excitation.py \
  --telemetry runs/ros2_sysid_steering_excitation/telemetry.csv \
  --quality runs/ros2_sysid_steering_excitation/quality_metrics.csv
```

The gate should continue to enforce:

- required columns exist
- numeric columns are finite
- `time_s` is strictly increasing
- no collision
- duration is at least `15 s`
- steering range is at least `0.05 rad`
- yaw-rate range is at least `0.1 rad/s`
- speed coefficient of variation is at most `0.15`
- steering saturation fraction is at most `2%`
- no steering saturation segment exceeds `0.25 s`

## Next Migration Steps

1. Run the ROS 2 bridge and excitation nodes locally.
2. Point a validator at `runs/ros2_sysid_steering_excitation/telemetry.csv`.
3. Add a `bag_to_telemetry.py` converter if the workflow moves from direct CSV logging to rosbag logging.
4. Keep parameter fitting in a separate branch after ROS 2 excitation quality passes.

## Not In Scope Yet

- `C_Sf` or `C_Sr` fitting
- LQR, MPC, or controller tuning
- Real-car deployment
- Replacing the existing Python/Gym validation scripts
