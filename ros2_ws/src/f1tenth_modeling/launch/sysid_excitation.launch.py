from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    config = PathJoinSubstitution(
        [FindPackageShare("f1tenth_modeling"), "config", "sysid_excitation.yaml"]
    )

    gym_bridge = Node(
        package="f1tenth_modeling",
        executable="gym_bridge_node",
        name="gym_bridge_node",
        parameters=[config],
        output="screen",
    )
    sysid_excitation = Node(
        package="f1tenth_modeling",
        executable="sysid_excitation_node",
        name="sysid_excitation_node",
        parameters=[config],
        output="screen",
    )

    return LaunchDescription(
        [
            gym_bridge,
            sysid_excitation,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=sysid_excitation,
                    on_exit=[EmitEvent(event=Shutdown(reason="SysID excitation completed"))],
                )
            ),
        ]
    )
