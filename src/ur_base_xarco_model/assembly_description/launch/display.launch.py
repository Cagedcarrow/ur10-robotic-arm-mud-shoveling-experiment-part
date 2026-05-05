from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_rviz = LaunchConfiguration('use_rviz')
    use_gui = LaunchConfiguration('use_gui')

    xacro_file = PathJoinSubstitution([
        FindPackageShare('assembly_description'),
        'urdf',
        'assembly.urdf.xacro'
    ])

    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
        ' ',
        'ros_profile:=ros2',
        ' ',
        'ros_hardware_interface:=position'
    ])

    robot_description = {'robot_description': robot_description_content}

    rviz_config = PathJoinSubstitution([
        FindPackageShare('assembly_description'),
        'rviz',
        'assembly.rviz'
    ])

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('use_gui', default_value='true'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[robot_description]
        ),

        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            condition=IfCondition(use_gui),
            parameters=[
                robot_description,
                {
                    'zeros.ur10_shoulder_pan': 2.2038776874542236,
                    'zeros.ur10_shoulder_lift': 0.06395161151885986,
                    'zeros.ur10_elbow': -1.7774718443499964,
                    'zeros.ur10_wrist_1': -0.04721385637392217,
                    'zeros.ur10_wrist_2': 1.8873671293258667,
                    'zeros.ur10_wrist_3': 0.9308245182037354,
                }
            ]
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            condition=IfCondition(use_rviz)
        )
    ])
