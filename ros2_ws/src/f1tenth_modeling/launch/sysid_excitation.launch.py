from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    config = PathJoinSubstitution(
        [FindPackageShare("f1tenth_modeling"), "config", "sysid_excitation.yaml"]
    )

    return LaunchDescription(
        [
            Node(
                package="f1tenth_modeling",
                executable="gym_bridge_node",
                name="gym_bridge_node",
                parameters=[config],
                output="screen",
            ),
            Node(
                package="f1tenth_modeling",
                executable="sysid_excitation_node",
                name="sysid_excitation_node",
                parameters=[config],
                output="screen",
            ),
        ]
    )
