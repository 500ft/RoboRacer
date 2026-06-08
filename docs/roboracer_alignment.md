# RoboRacer Alignment

## Purpose

RoboRacer is the current continuation of the F1TENTH ecosystem. This repository still uses F1TENTH Gym as its offline modeling baseline, but the runtime direction is ROS 2-compatible so the same modeling evidence can be connected to RoboRacer-style simulator and hardware data.

## Project Position

The current evidence chain remains:

```text
F1TENTH Gym / Python experiments
-> CSV telemetry
-> model replay
-> validation gates
-> reports and figures
```

The ROS 2 layer is added beside that chain:

```text
ROS 2 topics or bags
-> rosbag_to_telemetry.py
-> same CSV schema
-> same validation gates
```

This avoids rewriting the model-validation work while still supporting RoboRacer data formats.

## Interface Policy

Standard RoboRacer compatibility starts with common ROS 2 topics:

| Topic | Type | Role |
| --- | --- | --- |
| `/drive` | `ackermann_msgs/AckermannDriveStamped` | environment or vehicle command |
| `/ego_racecar/odom` | `nav_msgs/Odometry` | pose and velocity state |
| `/f1tenth/collision` | `std_msgs/Bool` | simulator collision flag when available |

The project-specific `/f1tenth/internal_state` topic is optional enrichment. It carries:

```text
[X, Y, delta, v, psi, r, beta]
```

That topic is useful for simulator oracle checks and tire-parameter fitting because it exposes achieved steering and slip angle. It is not treated as an upstream RoboRacer standard.

## Modeling Boundary

This alignment step does not fit tire parameters, tune controllers, or prepare real-car deployment. Its job is to make ROS 2 bag data compatible with the existing SysID telemetry contract.

Future fitting should prefer achieved steering and achieved acceleration. If a bag only contains command steering, conversion is allowed for compatibility checks, but the metadata marks `steer_rad_source = command_proxy`.
