from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_params = PathJoinSubstitution([
        FindPackageShare("ft300_gui_ros2"), "config", "ft300_gui_params.yaml"
    ])

    return LaunchDescription([
        DeclareLaunchArgument("params_file", default_value=default_params),
        Node(
            package="ft300_gui_ros2",
            executable="ft300_gui_node",
            name="ft300_gui_node",
            output="screen",
            parameters=[LaunchConfiguration("params_file")],
        ),
    ])
