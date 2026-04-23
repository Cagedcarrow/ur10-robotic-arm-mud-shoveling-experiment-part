from launch import LaunchDescription
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    xacro_file = PathJoinSubstitution(
        [FindPackageShare("my_robot"), "my_robot.urdf.xacro"]
    )
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("my_robot"), "rviz", "view_my_robot.rviz"]
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            xacro_file,
            " ros_profile:=ros2",
            " ros_hardware_interface:=position",
            " inject_gazebo_ros_control_plugin:=false",
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    return LaunchDescription(
        [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                output="screen",
                parameters=[robot_description],
            ),
            Node(
                package="my_robot",
                executable="shovel_tcp_slider.py",
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                output="screen",
                arguments=["-d", rviz_config],
                parameters=[robot_description],
            ),
        ]
    )
