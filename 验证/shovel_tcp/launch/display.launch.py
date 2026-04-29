from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_xacro = LaunchConfiguration('use_xacro')
    model = LaunchConfiguration('model')

    default_model = PathJoinSubstitution([
        FindPackageShare('ur10_shovel_tool'),
        'urdf',
        'ur10_shovel_tool.urdf',
    ])

    robot_description = {
        'robot_description': Command(['xacro ', model])
    }

    return LaunchDescription([
        DeclareLaunchArgument('use_xacro', default_value='false'),
        DeclareLaunchArgument('model', default_value=default_model),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[robot_description],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
        ),
    ])
