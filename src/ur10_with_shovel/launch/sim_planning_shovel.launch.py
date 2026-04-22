from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    start_rviz = LaunchConfiguration("start_rviz")
    use_sim_time = LaunchConfiguration("use_sim_time")
    world = LaunchConfiguration("world")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ur10_with_shovel"), "launch", "gazebo_shovel.launch.py"])
        ),
        launch_arguments={
            "use_fake_hardware": use_fake_hardware,
            "use_sim_time": use_sim_time,
            "world": world,
        }.items(),
    )

    moveit_launch = TimerAction(
        period=4.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_with_shovel"), "launch", "moveit_shovel.launch.py"]
                    )
                ),
                launch_arguments={
                    "start_rviz": start_rviz,
                    "use_sim_time": use_sim_time,
                    "sim_gazebo": "true",
                    "use_fake_hardware": use_fake_hardware,
                    "planning_tip_link": "shovel_tip",
                }.items(),
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ur10_simulation_bringup"), "worlds", "empty.world"]
                ),
            ),
            gazebo_launch,
            moveit_launch,
        ]
    )
