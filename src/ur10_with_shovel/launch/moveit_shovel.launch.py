from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import IncludeLaunchDescription
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    start_rviz = LaunchConfiguration("start_rviz")

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_moveit_config"), "launch", "ur_moveit.launch.py"]
                    )
                ),
                launch_arguments={
                    "ur_type": "ur10",
                    "description_package": "ur10_with_shovel",
                    "description_file": "ur10_shovel.urdf.xacro",
                    "moveit_config_package": "ur10_moveit_config",
                    "moveit_config_file": "ur.srdf.xacro",
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "launch_rviz": start_rviz,
                }.items(),
            ),
        ]
    )
