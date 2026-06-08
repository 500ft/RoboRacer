"""Publish chirp steering commands and log ROS 2 SysID excitation telemetry."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from ackermann_msgs.msg import AckermannDriveStamped
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64MultiArray


FIELDNAMES = [
    "run_id",
    "step",
    "time_s",
    "profile_status",
    "command_speed_mps",
    "command_steer_rad",
    "x_m",
    "y_m",
    "theta_rad",
    "speed_mps",
    "vx_mps",
    "vy_mps",
    "steer_rad",
    "steer_vel_radps",
    "yaw_rate_radps",
    "slip_angle_rad",
    "accel_x_mps2",
    "collision",
]


def repo_root() -> Path:
    return Path.cwd()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root() / path


def chirp_steer(time_s: float, amplitude_rad: float, duration_s: float, f0: float, f1: float) -> float:
    ramp = (f1 - f0) / duration_s
    phase = 2.0 * math.pi * (f0 * time_s + 0.5 * ramp * time_s**2)
    return float(amplitude_rad * math.sin(phase))


def longest_true_segment_s(mask: np.ndarray, dt_s: float) -> float:
    longest = 0
    current = 0
    for item in mask:
        if bool(item):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return float(longest * dt_s)


class SysidExcitationNode(Node):
    """Command chirp steering and write the same CSV schema used by offline SysID."""

    def __init__(self) -> None:
        super().__init__("sysid_excitation_node")
        self.declare_parameter("drive_topic", "/drive")
        self.declare_parameter("internal_state_topic", "/f1tenth/internal_state")
        self.declare_parameter("collision_topic", "/f1tenth/collision")
        self.declare_parameter("output_dir", "runs/ros2_sysid_steering_excitation")
        self.declare_parameter("timestep_s", 0.01)
        self.declare_parameter("target_speed_mps", 2.0)
        self.declare_parameter("amplitude_rad", 0.04)
        self.declare_parameter("duration_s", 20.0)
        self.declare_parameter("freq_start_hz", 0.2)
        self.declare_parameter("freq_end_hz", 2.0)
        self.declare_parameter("s_max_rad", 0.4189)
        self.declare_parameter("steering_saturation_fraction_limit", 0.02)
        self.declare_parameter("steering_saturation_segment_limit_s", 0.25)

        self.output_dir = resolve_repo_path(str(self.get_parameter("output_dir").value))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_path = self.output_dir / "telemetry.csv"
        self.metrics_path = self.output_dir / "quality_metrics.csv"
        self.metadata_path = self.output_dir / "metadata.json"
        self.report_path = repo_root() / "reports" / "ros2_sysid_steering_excitation.md"

        self.timestep_s = float(self.get_parameter("timestep_s").value)
        self.target_speed_mps = float(self.get_parameter("target_speed_mps").value)
        self.amplitude_rad = float(self.get_parameter("amplitude_rad").value)
        self.duration_s = float(self.get_parameter("duration_s").value)
        self.freq_start_hz = float(self.get_parameter("freq_start_hz").value)
        self.freq_end_hz = float(self.get_parameter("freq_end_hz").value)
        self.s_max_rad = float(self.get_parameter("s_max_rad").value)
        self.saturation_threshold_rad = 0.95 * self.s_max_rad
        self.saturation_fraction_limit = float(
            self.get_parameter("steering_saturation_fraction_limit").value
        )
        self.saturation_segment_limit_s = float(
            self.get_parameter("steering_saturation_segment_limit_s").value
        )

        drive_topic = str(self.get_parameter("drive_topic").value)
        internal_state_topic = str(self.get_parameter("internal_state_topic").value)
        collision_topic = str(self.get_parameter("collision_topic").value)

        self.command_pub = self.create_publisher(AckermannDriveStamped, drive_topic, 10)
        self.create_subscription(Float64MultiArray, internal_state_topic, self.state_callback, 10)
        self.create_subscription(Bool, collision_topic, self.collision_callback, 10)
        self.create_timer(self.timestep_s, self.command_timer)

        self.rows: list[dict[str, str | float | int]] = []
        self.start_time = self.get_clock().now()
        self.last_state: list[float] | None = None
        self.previous_steer: float | None = None
        self.previous_speed: float | None = None
        self.current_command_steer_rad = 0.0
        self.collision = False
        self.done = False
        self.step_count = 0
        self.run_id = f"ros2_chirp_a{self.amplitude_rad:.3f}_d{self.duration_s:.0f}"

        self.get_logger().info(
            "SysID excitation publishes environment commands; achieved/reconstructed "
            "signals are logged as future dynamic-model inputs."
        )

    def elapsed_s(self) -> float:
        elapsed = self.get_clock().now() - self.start_time
        return float(elapsed.nanoseconds) * 1e-9

    def command_timer(self) -> None:
        if self.done:
            return

        time_s = self.elapsed_s()
        if time_s >= self.duration_s or self.collision:
            self.finish()
            return

        command = chirp_steer(
            time_s,
            self.amplitude_rad,
            self.duration_s,
            self.freq_start_hz,
            self.freq_end_hz,
        )
        self.current_command_steer_rad = float(np.clip(command, -0.75 * self.s_max_rad, 0.75 * self.s_max_rad))

        message = AckermannDriveStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.drive.steering_angle = self.current_command_steer_rad
        message.drive.speed = self.target_speed_mps
        self.command_pub.publish(message)

    def collision_callback(self, message: Bool) -> None:
        self.collision = bool(message.data)

    def state_callback(self, message: Float64MultiArray) -> None:
        if self.done:
            return
        if len(message.data) < 7:
            self.get_logger().warn("Ignoring internal state with fewer than 7 entries")
            return

        x, y, steer, speed, theta, yaw_rate, slip_angle = [float(value) for value in message.data[:7]]
        if self.previous_steer is None:
            steer_vel = 0.0
            accel_x = 0.0
        else:
            steer_vel = (steer - self.previous_steer) / self.timestep_s
            accel_x = (speed - self.previous_speed) / self.timestep_s

        self.previous_steer = steer
        self.previous_speed = speed
        self.step_count += 1
        time_s = self.elapsed_s()
        vx = speed * math.cos(slip_angle)
        vy = speed * math.sin(slip_angle)

        self.rows.append(
            {
                "run_id": self.run_id,
                "step": self.step_count,
                "time_s": f"{time_s:.6f}",
                "profile_status": "selected_pass",
                "command_speed_mps": f"{self.target_speed_mps:.9f}",
                "command_steer_rad": f"{self.current_command_steer_rad:.9f}",
                "x_m": f"{x:.9f}",
                "y_m": f"{y:.9f}",
                "theta_rad": f"{theta:.9f}",
                "speed_mps": f"{speed:.9f}",
                "vx_mps": f"{vx:.9f}",
                "vy_mps": f"{vy:.9f}",
                "steer_rad": f"{steer:.9f}",
                "steer_vel_radps": f"{steer_vel:.9f}",
                "yaw_rate_radps": f"{yaw_rate:.9f}",
                "slip_angle_rad": f"{slip_angle:.9f}",
                "accel_x_mps2": f"{accel_x:.9f}",
                "collision": int(self.collision),
            }
        )

    def quality_metrics(self) -> tuple[list[dict[str, Any]], bool]:
        if not self.rows:
            return [{"metric": "num_samples", "value": 0, "units": "count", "pass": False}], False

        numeric: dict[str, np.ndarray] = {}
        for field in FIELDNAMES:
            if field in {"run_id", "profile_status"}:
                continue
            numeric[field] = np.array([float(row[field]) for row in self.rows], dtype=float)

        time_s = numeric["time_s"]
        duration_s = float(time_s[-1] - time_s[0]) if len(time_s) >= 2 else 0.0
        speed_mean = float(np.mean(numeric["speed_mps"]))
        speed_std = float(np.std(numeric["speed_mps"], ddof=1)) if len(time_s) > 1 else 0.0
        speed_cv = float(speed_std / max(abs(speed_mean), 1e-6))
        steer_range = float(np.max(numeric["steer_rad"]) - np.min(numeric["steer_rad"]))
        yaw_rate_range = float(np.max(numeric["yaw_rate_radps"]) - np.min(numeric["yaw_rate_radps"]))
        saturation_mask = np.abs(numeric["steer_rad"]) >= self.saturation_threshold_rad
        saturation_fraction = float(np.mean(saturation_mask))
        max_saturation_segment_s = longest_true_segment_s(saturation_mask, self.timestep_s)
        collision = bool(np.max(numeric["collision"]))

        metrics = [
            {"metric": "duration_s", "value": duration_s, "units": "s", "pass": duration_s >= 15.0},
            {"metric": "num_samples", "value": len(self.rows), "units": "count", "pass": len(self.rows) > 0},
            {"metric": "collision", "value": int(collision), "units": "bool", "pass": not collision},
            {"metric": "speed_mean_mps", "value": speed_mean, "units": "m/s", "pass": True},
            {"metric": "speed_std_mps", "value": speed_std, "units": "m/s", "pass": True},
            {"metric": "speed_cv", "value": speed_cv, "units": "unitless", "pass": speed_cv <= 0.15},
            {"metric": "steer_range_rad", "value": steer_range, "units": "rad", "pass": steer_range >= 0.05},
            {"metric": "yaw_rate_range_radps", "value": yaw_rate_range, "units": "rad/s", "pass": yaw_rate_range >= 0.1},
            {
                "metric": "steering_saturation_fraction",
                "value": saturation_fraction,
                "units": "fraction",
                "pass": saturation_fraction <= self.saturation_fraction_limit,
            },
            {
                "metric": "max_saturation_segment_s",
                "value": max_saturation_segment_s,
                "units": "s",
                "pass": max_saturation_segment_s <= self.saturation_segment_limit_s,
            },
        ]
        return metrics, all(bool(row["pass"]) for row in metrics)

    def finish(self) -> None:
        if self.done:
            return
        self.done = True
        metrics, passed = self.quality_metrics()
        self.write_outputs(metrics, passed)
        self.get_logger().info(f"SysID excitation complete. Quality gates passed: {passed}")

    def write_outputs(self, metrics: list[dict[str, Any]], passed: bool) -> None:
        with self.telemetry_path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES, lineterminator="\n")
            writer.writeheader()
            writer.writerows(self.rows)

        with self.metrics_path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["metric", "value", "units", "pass"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(metrics)

        metadata = {
            "experiment": "ros2_sysid_steering_excitation",
            "runtime": "ros2",
            "telemetry_source": "ROS 2 topics",
            "state_source": "/f1tenth/internal_state Float64MultiArray [X, Y, delta, v, psi, r, beta]",
            "command_convention": "[command_steer_rad, command_speed_mps] published as AckermannDriveStamped",
            "future_sysid_input_convention": "[steer_vel_radps, accel_x_mps2] reconstructed from achieved state",
            "target_speed_mps": self.target_speed_mps,
            "amplitude_rad": self.amplitude_rad,
            "duration_s": self.duration_s,
            "frequency_start_hz": self.freq_start_hz,
            "frequency_end_hz": self.freq_end_hz,
            "saturation_threshold_rad": self.saturation_threshold_rad,
            "passed_quality_gates": passed,
            "no_parameter_fitting": True,
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

        status = "passed" if passed else "failed"
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            "\n".join(
                [
                    "# ROS 2 SysID Steering Excitation",
                    "",
                    "This run ports the existing Gym SysID excitation workflow into ROS 2.",
                    "It collects excitation data only; no parameter fitting is performed.",
                    "",
                    "Environment command signals are not internal dynamic-model inputs.",
                    "`command_steer_rad` and `command_speed_mps` are published setpoints; ",
                    "`steer_vel_radps` and `accel_x_mps2` are reconstructed from achieved state.",
                    "",
                    f"Quality status: `{status}`.",
                    "",
                    "Fitting starts only after excitation quality passes.",
                    "",
                ]
            ),
            encoding="utf-8",
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SysidExcitationNode()
    try:
        rclpy.spin(node)
    finally:
        node.finish()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
