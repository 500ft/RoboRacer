"""Publish a finite steering chirp without requiring project-specific state topics."""

from __future__ import annotations

import math

from ackermann_msgs.msg import AckermannDriveStamped
import rclpy
from rclpy.node import Node


def chirp_steer(
    time_s: float,
    amplitude_rad: float,
    duration_s: float,
    frequency_start_hz: float,
    frequency_end_hz: float,
) -> float:
    ramp = (frequency_end_hz - frequency_start_hz) / duration_s
    phase = 2.0 * math.pi * (frequency_start_hz * time_s + 0.5 * ramp * time_s**2)
    return amplitude_rad * math.sin(phase)


class CommandOnlyExcitationNode(Node):
    """Publish standard Ackermann commands for stock simulator ingestion tests."""

    def __init__(self) -> None:
        super().__init__("command_only_excitation_node")
        self.declare_parameter("drive_topic", "/drive")
        self.declare_parameter("publish_period_s", 0.01)
        self.declare_parameter("target_speed_mps", 2.0)
        self.declare_parameter("amplitude_rad", 0.04)
        self.declare_parameter("duration_s", 20.0)
        self.declare_parameter("freq_start_hz", 0.2)
        self.declare_parameter("freq_end_hz", 2.0)
        self.declare_parameter("rtf_compensation", 1.0)

        self.target_speed_mps = float(self.get_parameter("target_speed_mps").value)
        self.amplitude_rad = float(self.get_parameter("amplitude_rad").value)
        self.duration_s = float(self.get_parameter("duration_s").value)
        compensation = float(self.get_parameter("rtf_compensation").value)
        self.freq_start_hz = float(self.get_parameter("freq_start_hz").value) * compensation
        self.freq_end_hz = float(self.get_parameter("freq_end_hz").value) * compensation
        self.publisher = self.create_publisher(
            AckermannDriveStamped,
            str(self.get_parameter("drive_topic").value),
            10,
        )
        self.start_time = self.get_clock().now()
        self.done = False
        self.create_timer(float(self.get_parameter("publish_period_s").value), self.publish_command)

    def elapsed_s(self) -> float:
        return float((self.get_clock().now() - self.start_time).nanoseconds) * 1e-9

    def publish_command(self) -> None:
        if self.done:
            return
        elapsed = self.elapsed_s()
        if elapsed >= self.duration_s:
            stop = AckermannDriveStamped()
            stop.header.stamp = self.get_clock().now().to_msg()
            self.publisher.publish(stop)
            self.done = True
            return
        message = AckermannDriveStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.drive.speed = self.target_speed_mps
        message.drive.steering_angle = chirp_steer(
            elapsed,
            self.amplitude_rad,
            self.duration_s,
            self.freq_start_hz,
            self.freq_end_hz,
        )
        self.publisher.publish(message)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CommandOnlyExcitationNode()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

