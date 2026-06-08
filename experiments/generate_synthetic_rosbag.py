#!/usr/bin/env python
"""Generate deterministic ROS 2 bags for rosbag-to-telemetry converter tests."""

from __future__ import annotations

import argparse
import math
import shutil
from pathlib import Path

import numpy as np
from rosbags.rosbag2 import Writer
from rosbags.typesys import Stores, get_types_from_msg, get_typestore

ACKERMANN_DRIVE_MSG = """float32 steering_angle
float32 steering_angle_velocity
float32 speed
float32 acceleration
float32 jerk
"""

ACKERMANN_DRIVE_STAMPED_MSG = """std_msgs/Header header
ackermann_msgs/AckermannDrive drive
"""


def build_typestore():
    typestore = get_typestore(Stores.ROS2_HUMBLE)
    typestore.register(get_types_from_msg(ACKERMANN_DRIVE_MSG, "ackermann_msgs/msg/AckermannDrive"))
    typestore.register(get_types_from_msg(ACKERMANN_DRIVE_STAMPED_MSG, "ackermann_msgs/msg/AckermannDriveStamped"))
    return typestore


def yaw_to_quaternion(yaw: float, typestore):
    quaternion = typestore.types["geometry_msgs/msg/Quaternion"]
    return quaternion(0.0, 0.0, math.sin(0.5 * yaw), math.cos(0.5 * yaw))


def time_msg(time_s: float, typestore):
    time_type = typestore.types["builtin_interfaces/msg/Time"]
    sec = int(math.floor(time_s))
    nanosec = int(round((time_s - sec) * 1e9))
    return time_type(sec, nanosec)


def header(time_s: float, frame_id: str, typestore):
    header_type = typestore.types["std_msgs/msg/Header"]
    return header_type(time_msg(time_s, typestore), frame_id)


def make_odom(time_s: float, x: float, y: float, yaw: float, vx: float, vy: float, yaw_rate: float, typestore):
    point = typestore.types["geometry_msgs/msg/Point"]
    pose = typestore.types["geometry_msgs/msg/Pose"]
    pose_cov = typestore.types["geometry_msgs/msg/PoseWithCovariance"]
    vector = typestore.types["geometry_msgs/msg/Vector3"]
    twist = typestore.types["geometry_msgs/msg/Twist"]
    twist_cov = typestore.types["geometry_msgs/msg/TwistWithCovariance"]
    odom = typestore.types["nav_msgs/msg/Odometry"]
    covariance = np.zeros(36, dtype=np.float64)
    return odom(
        header(time_s, "map", typestore),
        "base_link",
        pose_cov(pose(point(x, y, 0.0), yaw_to_quaternion(yaw, typestore)), covariance.copy()),
        twist_cov(twist(vector(vx, vy, 0.0), vector(0.0, 0.0, yaw_rate)), covariance.copy()),
    )


def make_drive(time_s: float, steer: float, speed: float, typestore):
    drive = typestore.types["ackermann_msgs/msg/AckermannDrive"]
    stamped = typestore.types["ackermann_msgs/msg/AckermannDriveStamped"]
    return stamped(header(time_s, "base_link", typestore), drive(steer, 0.0, speed, 0.0, 0.0))


def make_collision(value: bool, typestore):
    bool_type = typestore.types["std_msgs/msg/Bool"]
    return bool_type(value)


def make_internal_state(x: float, y: float, steer: float, speed: float, yaw: float, yaw_rate: float, beta: float, typestore):
    layout_type = typestore.types["std_msgs/msg/MultiArrayLayout"]
    array_type = typestore.types["std_msgs/msg/Float64MultiArray"]
    data = np.array([x, y, steer, speed, yaw, yaw_rate, beta], dtype=np.float64)
    return array_type(layout_type([], 0), data)


def create_bag(output: Path, include_internal_state: bool, duration_s: float = 20.0, dt_s: float = 0.01, force: bool = False) -> None:
    if output.exists():
        if not force:
            raise SystemExit(f"FAIL: output bag already exists: {output}")
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    typestore = build_typestore()
    odom_type = "nav_msgs/msg/Odometry"
    drive_type = "ackermann_msgs/msg/AckermannDriveStamped"
    collision_type = "std_msgs/msg/Bool"
    internal_type = "std_msgs/msg/Float64MultiArray"

    x = 0.0
    y = 0.0
    yaw = 0.0
    with Writer(output, version=9) as writer:
        odom_conn = writer.add_connection("/ego_racecar/odom", odom_type, typestore=typestore)
        drive_conn = writer.add_connection("/drive", drive_type, typestore=typestore)
        collision_conn = writer.add_connection("/f1tenth/collision", collision_type, typestore=typestore)
        internal_conn = (
            writer.add_connection("/f1tenth/internal_state", internal_type, typestore=typestore)
            if include_internal_state
            else None
        )

        steps = int(round(duration_s / dt_s)) + 1
        for step in range(steps):
            time_s = step * dt_s
            steer_cmd = 0.064 * math.sin(2.0 * math.pi * 0.5 * time_s)
            steer_achieved = 0.8 * steer_cmd
            speed = 2.0 + 0.02 * math.sin(2.0 * math.pi * 0.2 * time_s)
            beta = 0.03 * math.sin(2.0 * math.pi * 0.5 * time_s + 0.2)
            yaw_rate = 0.26 * math.sin(2.0 * math.pi * 0.5 * time_s + 0.4)
            vx = speed * math.cos(beta)
            vy = speed * math.sin(beta)
            yaw += yaw_rate * dt_s
            x += (vx * math.cos(yaw) - vy * math.sin(yaw)) * dt_s
            y += (vx * math.sin(yaw) + vy * math.cos(yaw)) * dt_s
            timestamp = int(round(time_s * 1e9))

            odom = make_odom(time_s, x, y, yaw, vx, vy, yaw_rate, typestore)
            drive = make_drive(time_s, steer_cmd, speed, typestore)
            collision = make_collision(False, typestore)
            writer.write(odom_conn, timestamp, typestore.serialize_cdr(odom, odom_type))
            writer.write(drive_conn, timestamp, typestore.serialize_cdr(drive, drive_type))
            writer.write(collision_conn, timestamp, typestore.serialize_cdr(collision, collision_type))
            if internal_conn is not None:
                internal = make_internal_state(x, y, steer_achieved, speed, yaw, yaw_rate, beta, typestore)
                writer.write(internal_conn, timestamp, typestore.serialize_cdr(internal, internal_type))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-internal-state", action="store_true")
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    create_bag(args.output, args.include_internal_state, args.duration, args.dt, args.force)
    print(f"Wrote synthetic bag to {args.output}")


if __name__ == "__main__":
    main()
