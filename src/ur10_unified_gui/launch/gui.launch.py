from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ur10_unified_gui',
            executable='gui_node',
            name='ur10_unified_gui',
            output='screen',
        )
    ])
