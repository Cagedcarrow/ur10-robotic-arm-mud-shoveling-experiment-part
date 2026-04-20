from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("gantry_x_initial", default_value="0.0"),
            DeclareLaunchArgument("gantry_y_initial", default_value="0.0"),
            DeclareLaunchArgument("gantry_z_initial", default_value="-0.6"),
            DeclareLaunchArgument("gantry_x_min", default_value="-1.0"),
            DeclareLaunchArgument("gantry_x_max", default_value="1.0"),
            DeclareLaunchArgument("gantry_y_min", default_value="-0.8"),
            DeclareLaunchArgument("gantry_y_max", default_value="0.8"),
            DeclareLaunchArgument("gantry_z_min", default_value="-1.0"),
            DeclareLaunchArgument("gantry_z_max", default_value="0.0"),
            DeclareLaunchArgument("gantry_base_height", default_value="2.2"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_moveit_config"), "launch", "ur_moveit.launch.py"]
                    )
                ),
                launch_arguments={
                    "ur_type": LaunchConfiguration("ur_type"),
                    "use_sim_time": "true",
                    "launch_rviz": LaunchConfiguration("start_rviz"),
                    "gantry_x_initial": LaunchConfiguration("gantry_x_initial"),
                    "gantry_y_initial": LaunchConfiguration("gantry_y_initial"),
                    "gantry_z_initial": LaunchConfiguration("gantry_z_initial"),
                    "gantry_x_min": LaunchConfiguration("gantry_x_min"),
                    "gantry_x_max": LaunchConfiguration("gantry_x_max"),
                    "gantry_y_min": LaunchConfiguration("gantry_y_min"),
                    "gantry_y_max": LaunchConfiguration("gantry_y_max"),
                    "gantry_z_min": LaunchConfiguration("gantry_z_min"),
                    "gantry_z_max": LaunchConfiguration("gantry_z_max"),
                    "gantry_base_height": LaunchConfiguration("gantry_base_height"),
                }.items(),
            ),
        ]
    )
