from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import IncludeLaunchDescription
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    start_rviz = LaunchConfiguration("start_rviz")
    use_sim_time = LaunchConfiguration("use_sim_time")
    sim_gazebo = LaunchConfiguration("sim_gazebo")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    planning_tip_link = LaunchConfiguration("planning_tip_link")

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("sim_gazebo", default_value="true"),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument("planning_tip_link", default_value="shovel_tip"),
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
                    "use_sim_time": use_sim_time,
                    "launch_rviz": start_rviz,
                    "sim_gazebo": sim_gazebo,
                    "use_fake_hardware": use_fake_hardware,
                    "planning_tip_link": planning_tip_link,
                }.items(),
            ),
        ]
    )
