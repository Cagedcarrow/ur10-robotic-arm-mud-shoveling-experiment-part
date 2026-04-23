import json
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

from my_robot_moveit_config.launch_common import load_yaml


def _load_gantry_config(config_path):
    with open(config_path, "r", encoding="utf-8") as config_stream:
        config = json.load(config_stream)

    required_paths = (
        ("initial", "x"),
        ("initial", "y"),
        ("initial", "z"),
        ("limits", "x", "min"),
        ("limits", "x", "max"),
        ("limits", "y", "min"),
        ("limits", "y", "max"),
        ("limits", "z", "min"),
        ("limits", "z", "max"),
        ("structure", "base_height"),
    )

    for path in required_paths:
        cursor = config
        for key in path:
            if key not in cursor:
                dotted_path = ".".join(path)
                raise RuntimeError(f"Missing gantry JSON field: {dotted_path}")
            cursor = cursor[key]

    return config


def _launch_setup(context, *args, **kwargs):
    gantry_config_file = LaunchConfiguration("gantry_config_file").perform(context)
    gantry_config = _load_gantry_config(gantry_config_file)

    use_sim_time = LaunchConfiguration("use_sim_time")
    start_rviz = LaunchConfiguration("start_rviz")
    start_gantry_rviz_control = LaunchConfiguration("start_gantry_rviz_control")
    planning_group = LaunchConfiguration("planning_group")
    planning_tip_link = LaunchConfiguration("planning_tip_link")
    warehouse_sqlite_path = LaunchConfiguration("warehouse_sqlite_path")

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare("my_robot"), "urdf", "my_robot_gantry.urdf.xacro"]),
            " ",
            "ros_profile:=ros2 ",
            "ros_hardware_interface:=position ",
            "sim_gazebo:=true ",
            "simulation_controllers:=",
            PathJoinSubstitution([FindPackageShare("my_robot"), "config", "ros2_controllers.yaml"]),
            " ",
            "gantry_x_initial:=",
            str(gantry_config["initial"]["x"]),
            " ",
            "gantry_y_initial:=",
            str(gantry_config["initial"]["y"]),
            " ",
            "gantry_z_initial:=",
            str(gantry_config["initial"]["z"]),
            " ",
            "gantry_x_min:=",
            str(gantry_config["limits"]["x"]["min"]),
            " ",
            "gantry_x_max:=",
            str(gantry_config["limits"]["x"]["max"]),
            " ",
            "gantry_y_min:=",
            str(gantry_config["limits"]["y"]["min"]),
            " ",
            "gantry_y_max:=",
            str(gantry_config["limits"]["y"]["max"]),
            " ",
            "gantry_z_min:=",
            str(gantry_config["limits"]["z"]["min"]),
            " ",
            "gantry_z_max:=",
            str(gantry_config["limits"]["z"]["max"]),
            " ",
            "gantry_base_height:=",
            str(gantry_config["structure"]["base_height"]),
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    robot_description_semantic_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare("my_robot_moveit_config"), "srdf", "my_robot.srdf.xacro"]),
            " ",
            "name:=my_robot_gantry ",
            "tip_link:=",
            planning_tip_link,
        ]
    )
    robot_description_semantic = {
        "robot_description_semantic": ParameterValue(
            robot_description_semantic_content, value_type=str
        )
    }

    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml(
            "my_robot_moveit_config", "config/kinematics.yaml"
        )["/**"]["ros__parameters"]["robot_description_kinematics"]
    }
    robot_description_planning = {
        "robot_description_planning": load_yaml(
            "my_robot_moveit_config", "config/joint_limits.yaml"
        )["joint_limits"]
    }

    ompl_planning_pipeline_config = {
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": {
            "planning_plugin": "ompl_interface/OMPLPlanner",
            "request_adapters": "default_planner_request_adapters/AddTimeOptimalParameterization "
            "default_planner_request_adapters/FixWorkspaceBounds "
            "default_planner_request_adapters/FixStartStateBounds "
            "default_planner_request_adapters/FixStartStateCollision "
            "default_planner_request_adapters/FixStartStatePathConstraints",
            "start_state_max_bounds_error": 0.1,
        },
    }
    ompl_planning_pipeline_config["ompl"].update(
        load_yaml("my_robot_moveit_config", "config/ompl_planning.yaml")
    )

    moveit_controllers = {
        "moveit_simple_controller_manager": load_yaml(
            "my_robot_moveit_config", "config/moveit_controllers.yaml"
        ),
        "moveit_controller_manager": "moveit_simple_controller_manager/MoveItSimpleControllerManager",
    }

    trajectory_execution = {
        "moveit_manage_controllers": False,
        "trajectory_execution.allowed_execution_duration_scaling": 1.2,
        "trajectory_execution.allowed_goal_duration_margin": 0.5,
        "trajectory_execution.allowed_start_tolerance": 0.01,
        "trajectory_execution.execution_duration_monitoring": False,
    }

    planning_scene_monitor_parameters = {
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        "publish_robot_description": True,
        "publish_robot_description_semantic": True,
    }

    warehouse_ros_config = {
        "warehouse_plugin": "warehouse_ros_sqlite::DatabaseConnection",
        "warehouse_host": warehouse_sqlite_path,
    }

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            ompl_planning_pipeline_config,
            moveit_controllers,
            trajectory_execution,
            planning_scene_monitor_parameters,
            {"use_sim_time": use_sim_time},
            warehouse_ros_config,
        ],
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("my_robot_moveit_config"), "rviz", "view_robot.rviz"]
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        condition=IfCondition(start_rviz),
        arguments=["-d", rviz_config_file],
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            ompl_planning_pipeline_config,
            warehouse_ros_config,
            {"use_sim_time": use_sim_time},
        ],
    )

    gantry_rviz_control_node = Node(
        package="ur10_examples_py",
        executable="gantry_rviz_control",
        name="gantry_rviz_control",
        output="screen",
        condition=IfCondition(
            PythonExpression(
                ["'", start_rviz, "' == 'true' and '", start_gantry_rviz_control, "' == 'true'"]
            )
        ),
        parameters=[
            {
                "gantry_base_x": 0.95,
                "gantry_base_y": 0.0,
                "gantry_base_height": float(gantry_config["structure"]["base_height"]),
                "gantry_x_min": float(gantry_config["limits"]["x"]["min"]),
                "gantry_x_max": float(gantry_config["limits"]["x"]["max"]),
                "gantry_y_min": float(gantry_config["limits"]["y"]["min"]),
                "gantry_y_max": float(gantry_config["limits"]["y"]["max"]),
                "gantry_z_min": float(gantry_config["limits"]["z"]["min"]),
                "gantry_z_max": float(gantry_config["limits"]["z"]["max"]),
                "use_sim_time": True,
            }
        ],
    )

    return [move_group_node, rviz_node, gantry_rviz_control_node]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("start_gantry_rviz_control", default_value="true"),
            DeclareLaunchArgument("planning_group", default_value="my_robot_manipulator"),
            DeclareLaunchArgument("planning_tip_link", default_value="shovel_tip"),
            DeclareLaunchArgument(
                "warehouse_sqlite_path",
                default_value=os.path.expanduser("~/.ros/warehouse_my_robot.sqlite"),
            ),
            DeclareLaunchArgument(
                "gantry_config_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("my_robot"), "config", "gantry_config.json"]
                ),
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
