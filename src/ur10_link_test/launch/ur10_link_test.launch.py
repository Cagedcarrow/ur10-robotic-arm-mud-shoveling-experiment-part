from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_ip',
            default_value='10.160.9.21',
            description='UR10 robot controller IP address.',
        ),
        DeclareLaunchArgument(
            'host_ip',
            default_value='10.160.9.100',
            description='Expected ROS host IP configured in External Control.',
        ),
        DeclareLaunchArgument(
            'external_control_port',
            default_value='50002',
            description='URCap External Control script sender port.',
        ),
        DeclareLaunchArgument(
            'report_json',
            default_value='/root/ur10_ws/link_test_report.json',
            description='JSON report output path.',
        ),
        DeclareLaunchArgument(
            'report_md',
            default_value='/root/ur10_ws/link_test_report.md',
            description='Markdown report output path.',
        ),
        DeclareLaunchArgument(
            'speed_slider_mask_observed',
            default_value='true',
            description='Whether the current driver symptom includes speed_slider_mask ownership error.',
        ),
        Node(
            package='ur10_link_test',
            executable='ur10_link_test_node',
            name='ur10_link_test_node',
            output='screen',
            parameters=[{
                'robot_ip': LaunchConfiguration('robot_ip'),
                'host_ip': LaunchConfiguration('host_ip'),
                'external_control_port': LaunchConfiguration('external_control_port'),
                'robot_ports': [29999, 30001, 30002, 30003, 30004],
                'report_json': LaunchConfiguration('report_json'),
                'report_md': LaunchConfiguration('report_md'),
                'speed_slider_mask_observed': LaunchConfiguration('speed_slider_mask_observed'),
            }],
        ),
    ])
