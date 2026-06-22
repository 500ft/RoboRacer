"""Bridge F1TENTH Gym into ROS 2 topics for model-validation experiments."""

from __future__ import annotations

import math
from pathlib import Path

import gym
import numpy as np
from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Odometry
from PIL import Image
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float64MultiArray

from f110_gym.envs.base_classes import Integrator


STATE_ORDER = "[X, Y, delta, v, psi, r, beta, sim_time_s]"


def yaw_to_quaternion(yaw_rad: float) -> Quaternion:
    quat = Quaternion()
    quat.z = math.sin(0.5 * yaw_rad)
    quat.w = math.cos(0.5 * yaw_rad)
    return quat


def repo_root() -> Path:
    return Path.cwd()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root() / path


def create_open_map(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    map_stem = output_dir / "ros2_open_sysid_map"
    image_path = map_stem.with_suffix(".png")
    yaml_path = map_stem.with_suffix(".yaml")
    size_px = 2000
    border_px = 8
    resolution_m = 0.08
    image = np.full((size_px, size_px), 255, dtype=np.uint8)
    image[:border_px, :] = 0
    image[-border_px:, :] = 0
    image[:, :border_px] = 0
    image[:, -border_px:] = 0
    Image.fromarray(image).save(image_path)
    yaml_path.write_text(
        "\n".join(
            [
                "image: ros2_open_sysid_map.png",
                f"resolution: {resolution_m:.6f}",
                f"origin: [{-(size_px * resolution_m) / 2:.6f}, {-(size_px * resolution_m) / 2:.6f}, 0.000000]",
                "negate: 0",
                "occupied_thresh: 0.45",
                "free_thresh: 0.196",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return map_stem


class GymBridgeNode(Node):
    """Run F1TENTH Gym and expose command/state topics."""

    def __init__(self) -> None:
        super().__init__("gym_bridge_node")
        self.declare_parameter("drive_topic", "/drive")
        self.declare_parameter("odom_topic", "/ego_racecar/odom")
        self.declare_parameter("internal_state_topic", "/f1tenth/internal_state")
        self.declare_parameter("collision_topic", "/f1tenth/collision")
        self.declare_parameter("timestep_s", 0.01)
        self.declare_parameter("use_open_map", True)
        self.declare_parameter("open_map_dir", "runs/ros2_sysid_steering_excitation")
        self.declare_parameter("map_path", "examples/example_map")
        self.declare_parameter("map_ext", ".png")
        self.declare_parameter("start_x", 0.7)
        self.declare_parameter("start_y", 0.0)
        self.declare_parameter("start_theta", 1.37079632679)

        self.timestep_s = float(self.get_parameter("timestep_s").value)
        self.command_steer_rad = 0.0
        self.command_speed_mps = 0.0
        self.collision = False
        self.sim_time_s = 0.0

        drive_topic = str(self.get_parameter("drive_topic").value)
        odom_topic = str(self.get_parameter("odom_topic").value)
        internal_state_topic = str(self.get_parameter("internal_state_topic").value)
        collision_topic = str(self.get_parameter("collision_topic").value)

        if bool(self.get_parameter("use_open_map").value):
            map_stem = create_open_map(resolve_repo_path(str(self.get_parameter("open_map_dir").value)))
            map_ext = ".png"
        else:
            map_stem = resolve_repo_path(str(self.get_parameter("map_path").value))
            map_ext = str(self.get_parameter("map_ext").value)

        registered_env = gym.make(
            "f110_gym:f110-v0",
            map=str(map_stem),
            map_ext=map_ext,
            num_agents=1,
            timestep=self.timestep_s,
            integrator=Integrator.RK4,
            disable_env_checker=True,
        )
        # F1TENTH Gym implements the pre-0.26 reset/step API. Use the registered
        # environment without modern Gym's order/API wrappers.
        self.env = registered_env.unwrapped
        start_pose = np.array(
            [
                [
                    float(self.get_parameter("start_x").value),
                    float(self.get_parameter("start_y").value),
                    float(self.get_parameter("start_theta").value),
                ]
            ]
        )
        self.env.reset(start_pose)

        self.odom_pub = self.create_publisher(Odometry, odom_topic, 10)
        self.internal_state_pub = self.create_publisher(Float64MultiArray, internal_state_topic, 10)
        self.collision_pub = self.create_publisher(Bool, collision_topic, 10)
        self.create_subscription(AckermannDriveStamped, drive_topic, self.drive_callback, 10)
        self.create_timer(self.timestep_s, self.step)

        self.get_logger().info(
            f"F1TENTH Gym bridge running with state order {STATE_ORDER}, map={map_stem}{map_ext}"
        )

    def drive_callback(self, message: AckermannDriveStamped) -> None:
        self.command_steer_rad = float(message.drive.steering_angle)
        self.command_speed_mps = float(message.drive.speed)

    def step(self) -> None:
        if not self.collision:
            obs, _, done, _ = self.env.step(
                np.array([[self.command_steer_rad, self.command_speed_mps]])
            )
            self.collision = bool(obs["collisions"][0]) or bool(done)
            self.sim_time_s += self.timestep_s

        state = self.env.sim.agents[0].state
        self.publish_state(state, self.collision)

    def publish_state(self, state: np.ndarray, collision: bool) -> None:
        stamp = self.get_clock().now().to_msg()
        x, y, steer, speed, yaw, yaw_rate, slip_angle = [float(value) for value in state[:7]]

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "map"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.orientation = yaw_to_quaternion(yaw)
        odom.twist.twist.linear.x = speed * math.cos(slip_angle)
        odom.twist.twist.linear.y = speed * math.sin(slip_angle)
        odom.twist.twist.angular.z = yaw_rate
        self.odom_pub.publish(odom)

        state_msg = Float64MultiArray()
        state_msg.data = [x, y, steer, speed, yaw, yaw_rate, slip_angle, self.sim_time_s]
        self.internal_state_pub.publish(state_msg)

        collision_msg = Bool()
        collision_msg.data = collision
        self.collision_pub.publish(collision_msg)

    def destroy_node(self) -> bool:
        close = getattr(self.env, "close", None)
        if callable(close):
            close()
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = GymBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
