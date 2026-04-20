from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

from ur10_moveit_config.launch_common import load_yaml


def launch_setup(context, *args, **kwargs):
    ur_type = LaunchConfiguration("ur_type")
    planning_group = LaunchConfiguration("planning_group")
    wait_for_obstacle = LaunchConfiguration("wait_for_obstacle")
    obstacle_id = LaunchConfiguration("obstacle_id")
    use_pose_target = LaunchConfiguration("use_pose_target")

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare("ur10_description"), "urdf", "ur10_sim.urdf.xacro"]),
            " ",
            "ur_type:=",
            ur_type,
            " ",
            "robot_name:=ur ",
            "use_fake_hardware:=false ",
            "sim_gazebo:=true",
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    robot_description_semantic_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare("ur10_moveit_config"), "srdf", "ur.srdf.xacro"]),
            " ",
            "name:=ur",
        ]
    )
    robot_description_semantic = {
        "robot_description_semantic": ParameterValue(
            robot_description_semantic_content, value_type=str
        )
    }
    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml("ur10_moveit_config", "config/kinematics.yaml")[
            "/**"
        ]["ros__parameters"]["robot_description_kinematics"]
    }
    robot_description_planning = {
        "robot_description_planning": load_yaml("ur10_moveit_config", "config/joint_limits.yaml")[
            "joint_limits"
        ]
    }

    common_parameters = [
        robot_description,
        robot_description_semantic,
        robot_description_kinematics,
        robot_description_planning,
        {
            "planning_group": planning_group,
            "pose_target_frame": "base_link",
            "execute": True,
            "use_sim_time": True,
            "wait_for_obstacle": wait_for_obstacle,
            "obstacle_id": obstacle_id,
            "use_pose_target": use_pose_target,
        },
    ]

    return [
        Node(
            package="ur10_examples",
            executable="move_group_interface_demo",
            output="screen",
            condition=IfCondition(LaunchConfiguration("start_cpp_demo")),
            parameters=common_parameters,
        ),
        Node(
            package="ur10_examples_py",
            executable="moveit_py_demo",
            output="screen",
            condition=IfCondition(LaunchConfiguration("start_py_demo")),
            parameters=common_parameters,
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("planning_group", default_value="ur_manipulator"),
            DeclareLaunchArgument("start_cpp_demo", default_value="true"),
            DeclareLaunchArgument("start_py_demo", default_value="false"),
            DeclareLaunchArgument("wait_for_obstacle", default_value="true"),
            DeclareLaunchArgument("obstacle_id", default_value="pcd_obstacle_box"),
            DeclareLaunchArgument("use_pose_target", default_value="false"),
            OpaqueFunction(function=launch_setup),
        ]
    )
