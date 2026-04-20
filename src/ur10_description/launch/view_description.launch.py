from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")
    gantry_x_initial = LaunchConfiguration("gantry_x_initial")
    gantry_y_initial = LaunchConfiguration("gantry_y_initial")
    gantry_z_initial = LaunchConfiguration("gantry_z_initial")
    gantry_base_height = LaunchConfiguration("gantry_base_height")
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare("ur10_description"), "urdf", "ur10_sim.urdf.xacro"]),
            " ",
            "ur_type:=",
            ur_type,
            " ",
            "gantry_x_initial:=",
            gantry_x_initial,
            " ",
            "gantry_y_initial:=",
            gantry_y_initial,
            " ",
            "gantry_z_initial:=",
            gantry_z_initial,
            " ",
            "gantry_base_height:=",
            gantry_base_height,
            " ",
            "use_fake_hardware:=true ",
            "sim_gazebo:=false",
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("gantry_x_initial", default_value="0.0"),
            DeclareLaunchArgument("gantry_y_initial", default_value="0.0"),
            DeclareLaunchArgument("gantry_z_initial", default_value="-0.6"),
            DeclareLaunchArgument("gantry_base_height", default_value="2.2"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                output="screen",
                parameters=[robot_description],
            ),
            Node(
                package="joint_state_publisher_gui",
                executable="joint_state_publisher_gui",
                output="screen",
            ),
            Node(package="rviz2", executable="rviz2", output="screen"),
        ]
    )
