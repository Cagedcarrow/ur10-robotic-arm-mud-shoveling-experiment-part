from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    start_rviz = LaunchConfiguration('start_rviz')
    use_sim_time = LaunchConfiguration('use_sim_time')
    gantry_config_file = LaunchConfiguration('gantry_config_file')

    moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare('my_robot_moveit_config'), 'launch', 'my_robot_moveit.launch.py']
            )
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'start_rviz': start_rviz,
            'start_gantry_rviz_control': 'false',
            'gantry_config_file': gantry_config_file,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('start_rviz', default_value='true'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'gantry_config_file',
            default_value=PathJoinSubstitution(
                [FindPackageShare('my_robot'), 'config', 'gantry_config.json']
            ),
        ),
        moveit_launch,
    ])
