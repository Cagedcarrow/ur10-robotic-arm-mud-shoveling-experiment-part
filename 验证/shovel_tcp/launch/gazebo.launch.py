from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_gazebo_ros = FindPackageShare('gazebo_ros')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_gazebo_ros, 'launch', 'gazebo.launch.py'])
        )
    )

    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'ur10_shovel_tool',
            '-file', PathJoinSubstitution([
                FindPackageShare('ur10_shovel_tool'),
                'urdf',
                'ur10_shovel_tool.urdf',
            ]),
        ],
        output='screen',
    )

    return LaunchDescription([
        gazebo,
        spawn,
    ])
