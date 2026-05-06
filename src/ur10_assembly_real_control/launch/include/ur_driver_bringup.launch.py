from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")
    robot_ip = LaunchConfiguration("robot_ip")
    headless_mode = LaunchConfiguration("headless_mode")
    launch_dashboard_client = LaunchConfiguration("launch_dashboard_client")

    ur_control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur_robot_driver"), "launch", "ur_control.launch.py"]
            )
        ),
        launch_arguments={
            "ur_type": ur_type,
            "robot_ip": robot_ip,
            "use_mock_hardware": "false",
            "headless_mode": headless_mode,
            "launch_rviz": "false",
            "launch_dashboard_client": launch_dashboard_client,
            "initial_joint_controller": "joint_trajectory_controller",
            "activate_joint_controller": "true",
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("ur_type", default_value="ur10"),
        DeclareLaunchArgument("robot_ip"),
        DeclareLaunchArgument("headless_mode", default_value="false"),
        DeclareLaunchArgument("launch_dashboard_client", default_value="true"),
        ur_control,
    ])
