from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    start_rviz = LaunchConfiguration("start_rviz")
    world = LaunchConfiguration("world")
    gui = LaunchConfiguration("gui")
    gantry_config_file = LaunchConfiguration("gantry_config_file")

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("my_robot"), "launch", "gazebo_gantry.launch.py"])
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "world": world,
            "gui": gui,
            "gantry_config_file": gantry_config_file,
        }.items(),
    )

    moveit_launch = TimerAction(
        period=5.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("my_robot_moveit_config"), "launch", "my_robot_moveit.launch.py"]
                    )
                ),
                launch_arguments={
                    "use_sim_time": use_sim_time,
                    "start_rviz": start_rviz,
                    "gantry_config_file": gantry_config_file,
                }.items(),
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("gui", default_value="true"),
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ur10_perception"), "worlds", "gantry_only.world"]
                ),
            ),
            DeclareLaunchArgument(
                "gantry_config_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("my_robot"), "config", "gantry_config.json"]
                ),
            ),
            gazebo_launch,
            moveit_launch,
        ]
    )
