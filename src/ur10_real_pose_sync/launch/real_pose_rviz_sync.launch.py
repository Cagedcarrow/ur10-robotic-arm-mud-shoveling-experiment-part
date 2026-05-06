from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_ip = LaunchConfiguration('ur_ip')
    ur_port = LaunchConfiguration('ur_port')
    socket_timeout_sec = LaunchConfiguration('socket_timeout_sec')
    use_rviz = LaunchConfiguration('use_rviz')

    xacro_file = TextSubstitution(
        text='/root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro'
    )

    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
        ' ',
        'mesh_root:=file:///root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/meshes',
    ])
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    rviz_config = PathJoinSubstitution([
        FindPackageShare('assembly_description'),
        'rviz',
        'assembly.rviz',
    ])

    return LaunchDescription([
        DeclareLaunchArgument('ur_ip', default_value='10.160.9.21'),
        DeclareLaunchArgument('ur_port', default_value='30003'),
        DeclareLaunchArgument('socket_timeout_sec', default_value='3.0'),
        DeclareLaunchArgument('use_rviz', default_value='true'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[robot_description],
        ),

        Node(
            package='ur10_real_pose_sync',
            executable='ur10_joint_state_tcp_node',
            name='ur10_joint_state_tcp_node',
            output='screen',
            parameters=[{
                'ur_ip': ur_ip,
                'ur_port': ur_port,
                'socket_timeout_sec': socket_timeout_sec,
                'output_topic': '/joint_states',
            }],
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(use_rviz),
            arguments=['-d', rviz_config],
        ),
    ])
