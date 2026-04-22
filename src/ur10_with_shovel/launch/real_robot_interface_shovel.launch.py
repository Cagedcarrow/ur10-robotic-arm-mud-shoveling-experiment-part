from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")
    robot_ip = LaunchConfiguration("robot_ip")
    reverse_ip = LaunchConfiguration("reverse_ip")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_dashboard_client = LaunchConfiguration("launch_dashboard_client")
    initial_joint_controller = LaunchConfiguration("initial_joint_controller")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    headless_mode = LaunchConfiguration("headless_mode")

    driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur10_simulation_bringup"), "launch", "real_robot_driver.launch.py"]
            )
        ),
        launch_arguments={
            "ur_type": ur_type,
            "robot_ip": robot_ip,
            "reverse_ip": reverse_ip,
            "launch_rviz": "false",
            "launch_dashboard_client": launch_dashboard_client,
            "initial_joint_controller": initial_joint_controller,
            "use_fake_hardware": use_fake_hardware,
            "headless_mode": headless_mode,
        }.items(),
    )

    moveit_launch = TimerAction(
        period=3.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_with_shovel"), "launch", "moveit_shovel.launch.py"]
                    )
                ),
                launch_arguments={
                    "start_rviz": launch_rviz,
                    "use_sim_time": "false",
                    "sim_gazebo": "false",
                    "use_fake_hardware": use_fake_hardware,
                    "planning_tip_link": "shovel_tip",
                }.items(),
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("robot_ip", default_value="192.168.56.101"),
            DeclareLaunchArgument("reverse_ip", default_value="192.168.56.1"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("launch_dashboard_client", default_value="true"),
            DeclareLaunchArgument(
                "initial_joint_controller", default_value="scaled_joint_trajectory_controller"
            ),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument("headless_mode", default_value="false"),
            driver_launch,
            moveit_launch,
        ]
    )
