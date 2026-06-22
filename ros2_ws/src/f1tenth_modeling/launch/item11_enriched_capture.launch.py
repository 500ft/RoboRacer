from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution(
        [FindPackageShare("f1tenth_modeling"), "config", "sysid_excitation.yaml"]
    )
    bag_output = LaunchConfiguration("bag_output")
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
            "/f1tenth/collision",
            "/f1tenth/internal_state",
        ],
        output="screen",
    )
    bridge = Node(
        package="f1tenth_modeling",
        executable="gym_bridge_node",
        parameters=[config],
        output="screen",
    )
    excitation = Node(
        package="f1tenth_modeling",
        executable="sysid_excitation_node",
        parameters=[config],
        output="screen",
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bag_output",
                default_value="runs/item11_capture/enriched_bridge_bag",
            ),
            recorder,
            TimerAction(period=2.0, actions=[bridge]),
            # Gym/Numba import and DDS discovery take several seconds on the
            # verified macOS environment. Start excitation only after the
            # bridge topics have been available to the recorder.
            TimerAction(period=8.0, actions=[excitation]),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=excitation,
                    on_exit=[EmitEvent(event=Shutdown(reason="item 11 excitation completed"))],
                )
            ),
        ]
    )
