import os

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
    description_package = LaunchConfiguration("description_package")
    description_file = LaunchConfiguration("description_file")
    moveit_config_package = LaunchConfiguration("moveit_config_package")
    moveit_config_file = LaunchConfiguration("moveit_config_file")
    warehouse_sqlite_path = LaunchConfiguration("warehouse_sqlite_path")
    use_sim_time = LaunchConfiguration("use_sim_time")
    launch_rviz = LaunchConfiguration("launch_rviz")
    gantry_x_initial = LaunchConfiguration("gantry_x_initial")
    gantry_y_initial = LaunchConfiguration("gantry_y_initial")
    gantry_z_initial = LaunchConfiguration("gantry_z_initial")
    gantry_x_min = LaunchConfiguration("gantry_x_min")
    gantry_x_max = LaunchConfiguration("gantry_x_max")
    gantry_y_min = LaunchConfiguration("gantry_y_min")
    gantry_y_max = LaunchConfiguration("gantry_y_max")
    gantry_z_min = LaunchConfiguration("gantry_z_min")
    gantry_z_max = LaunchConfiguration("gantry_z_max")
    gantry_base_height = LaunchConfiguration("gantry_base_height")

    joint_limit_params = PathJoinSubstitution(
        [FindPackageShare("ur_description"), "config", ur_type, "joint_limits.yaml"]
    )
    kinematics_params = PathJoinSubstitution(
        [FindPackageShare("ur_description"), "config", ur_type, "default_kinematics.yaml"]
    )
    physical_params = PathJoinSubstitution(
        [FindPackageShare("ur_description"), "config", ur_type, "physical_parameters.yaml"]
    )
    visual_params = PathJoinSubstitution(
        [FindPackageShare("ur_description"), "config", ur_type, "visual_parameters.yaml"]
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare(description_package), "urdf", description_file]),
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
            "gantry_x_min:=",
            gantry_x_min,
            " ",
            "gantry_x_max:=",
            gantry_x_max,
            " ",
            "gantry_y_min:=",
            gantry_y_min,
            " ",
            "gantry_y_max:=",
            gantry_y_max,
            " ",
            "gantry_z_min:=",
            gantry_z_min,
            " ",
            "gantry_z_max:=",
            gantry_z_max,
            " ",
            "gantry_base_height:=",
            gantry_base_height,
            " ",
            "robot_name:=ur ",
            "use_fake_hardware:=false ",
            "sim_gazebo:=true ",
            "joint_limit_params:=",
            joint_limit_params,
            " ",
            "kinematics_params:=",
            kinematics_params,
            " ",
            "physical_params:=",
            physical_params,
            " ",
            "visual_params:=",
            visual_params,
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    robot_description_semantic_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution([FindPackageShare(moveit_config_package), "srdf", moveit_config_file]),
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
        load_yaml("ur10_moveit_config", "config/ompl_planning.yaml")
    )

    moveit_controllers = {
        "moveit_simple_controller_manager": load_yaml(
            "ur10_moveit_config", "config/moveit_controllers.yaml"
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
            trajectory_execution,
            moveit_controllers,
            planning_scene_monitor_parameters,
            {"use_sim_time": use_sim_time},
            warehouse_ros_config,
        ],
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare(moveit_config_package), "rviz", "view_robot.rviz"]
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        condition=IfCondition(launch_rviz),
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

    return [move_group_node, rviz_node]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "ur_type",
                default_value="ur10",
                choices=[
                    "ur3",
                    "ur5",
                    "ur10",
                    "ur3e",
                    "ur5e",
                    "ur7e",
                    "ur10e",
                    "ur12e",
                    "ur16e",
                    "ur8long",
                    "ur15",
                    "ur18",
                    "ur20",
                    "ur30",
                ],
            ),
            DeclareLaunchArgument("description_package", default_value="ur10_description"),
            DeclareLaunchArgument("description_file", default_value="ur10_sim.urdf.xacro"),
            DeclareLaunchArgument("moveit_config_package", default_value="ur10_moveit_config"),
            DeclareLaunchArgument("moveit_config_file", default_value="ur.srdf.xacro"),
            DeclareLaunchArgument(
                "warehouse_sqlite_path",
                default_value=os.path.expanduser("~/.ros/warehouse_ros.sqlite"),
            ),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("gantry_x_initial", default_value="0.0"),
            DeclareLaunchArgument("gantry_y_initial", default_value="0.0"),
            DeclareLaunchArgument("gantry_z_initial", default_value="-0.6"),
            DeclareLaunchArgument("gantry_x_min", default_value="-1.0"),
            DeclareLaunchArgument("gantry_x_max", default_value="1.0"),
            DeclareLaunchArgument("gantry_y_min", default_value="-0.8"),
            DeclareLaunchArgument("gantry_y_max", default_value="0.8"),
            DeclareLaunchArgument("gantry_z_min", default_value="-1.0"),
            DeclareLaunchArgument("gantry_z_max", default_value="0.0"),
            DeclareLaunchArgument("gantry_base_height", default_value="2.2"),
            OpaqueFunction(function=launch_setup),
        ]
    )
