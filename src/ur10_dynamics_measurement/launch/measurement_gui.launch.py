from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "joint_states_topic",
            default_value="/joint_states",
            description="Topic for UR10 joint states",
        ),
        DeclareLaunchArgument(
            "ft_data_topic",
            default_value="io_and_status_controller/ft_data",
            description="Topic for FT300 wrench data",
        ),
        DeclareLaunchArgument(
            "data_root",
            default_value="~/.ros/ur10_measurement_data",
            description="Root directory for recorded data",
        ),

        Node(
            package="ur10_dynamics_measurement",
            executable="measurement_gui",
            name="ur10_dynamics_measurement_gui",
            output="screen",
            parameters=[{
                "joint_states_topic": LaunchConfiguration("joint_states_topic"),
                "ft_data_topic": LaunchConfiguration("ft_data_topic"),
                "data_root": LaunchConfiguration("data_root"),
            }],
        ),
    ])
