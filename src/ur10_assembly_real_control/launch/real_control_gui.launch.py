from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_ip = LaunchConfiguration("robot_ip")
    external_host_ip = LaunchConfiguration("external_host_ip")
    script_sender_port = LaunchConfiguration("script_sender_port")
    workspace = LaunchConfiguration("workspace")

    return LaunchDescription([
        DeclareLaunchArgument("robot_ip", default_value="10.160.9.21"),
        DeclareLaunchArgument("external_host_ip", default_value="10.160.9.100"),
        DeclareLaunchArgument("script_sender_port", default_value="50002"),
        DeclareLaunchArgument("workspace", default_value="/root/ur10_ws"),
        Node(
            package="ur10_assembly_real_control",
            executable="real_control_gui.py",
            name="ur10_external_control_gui",
            output="screen",
            arguments=[
                "--robot-ip",
                robot_ip,
                "--external-host-ip",
                external_host_ip,
                "--script-sender-port",
                script_sender_port,
                "--workspace",
                workspace,
            ],
        ),
    ])
