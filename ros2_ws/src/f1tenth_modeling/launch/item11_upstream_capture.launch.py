from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bag_output = LaunchConfiguration("bag_output")
    map_path = LaunchConfiguration("map_path")
    recorder = ExecuteProcess(
        cmd=[
            "ros2",
            "bag",
            "record",
            "--storage",
            "sqlite3",
            "-o",
            bag_output,
            "/ego_racecar/odom",
            "/drive",
        ],
        output="screen",
    )
    upstream_bridge = Node(
        package="f1tenth_gym_ros",
        executable="gym_bridge",
        name="bridge",
        parameters=[
            {
                "use_sim_time": False,
                "ego_namespace": "ego_racecar",
                "ego_scan_topic": "scan",
                "ego_odom_topic": "odom",
                "ego_opp_odom_topic": "opp_odom",
                "ego_drive_topic": "drive",
                "opp_namespace": "opp_racecar",
                "opp_scan_topic": "opp_scan",
                "opp_odom_topic": "odom",
                "opp_ego_odom_topic": "opp_odom",
                "opp_drive_topic": "opp_drive",
                "scan_distance_to_base_link": 0.275,
                "scan_fov": 4.7,
                "scan_beams": 1080,
                "map_path": map_path,
                "map_img_ext": ".png",
                "num_agent": 1,
                "sx": 0.7,
                "sy": 0.0,
                "stheta": 1.37079632679,
                "sx1": 2.0,
                "sy1": 0.5,
                "stheta1": 0.0,
                "kb_teleop": False,
            }
        ],
        output="screen",
    )
    excitation = Node(
        package="f1tenth_modeling",
        executable="command_only_excitation_node",
        parameters=[
            {
                "use_sim_time": False,
                "drive_topic": "/drive",
                "publish_period_s": 0.01,
                "target_speed_mps": 2.0,
                "amplitude_rad": 0.04,
                "duration_s": 20.0,
                "freq_start_hz": 0.2,
                "freq_end_hz": 2.0,
                "rtf_compensation": 1.0,
            }
        ],
        output="screen",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bag_output",
                default_value="runs/item11_capture/upstream_gym_ros_bag",
            ),
            DeclareLaunchArgument(
                "map_path",
                default_value="runs/ros2_sysid_steering_excitation/ros2_open_sysid_map",
            ),
            recorder,
            TimerAction(period=2.0, actions=[upstream_bridge]),
            TimerAction(period=8.0, actions=[excitation]),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=excitation,
                    on_exit=[EmitEvent(event=Shutdown(reason="upstream item 11 excitation completed"))],
                )
            ),
        ]
    )

