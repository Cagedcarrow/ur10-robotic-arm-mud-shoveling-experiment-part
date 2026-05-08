import os
import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

from ament_index_python.packages import get_package_share_directory


def load_yaml(pkg, relpath):
    with open(os.path.join(get_package_share_directory(pkg), relpath), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_text(pkg, relpath):
    with open(os.path.join(get_package_share_directory(pkg), relpath), "r", encoding="utf-8") as f:
        return f.read()


def generate_launch_description():
    pkg = "ur10_assembly_real_control"

    robot_ip = LaunchConfiguration("robot_ip")
    ur_type = LaunchConfiguration("ur_type")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_driver = LaunchConfiguration("launch_driver")
    headless_mode = LaunchConfiguration("headless_mode")
    launch_dashboard_client = LaunchConfiguration("launch_dashboard_client")
    reverse_ip = LaunchConfiguration("reverse_ip")

    xacro_file = PathJoinSubstitution([FindPackageShare(pkg), "config", "assembly_real.urdf.xacro"])
    mesh_root = PathJoinSubstitution([FindPackageShare(pkg), "config", "meshes"])

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        xacro_file,
        " ",
        "mesh_root:=",
        "file://",
        mesh_root,
    ])

    robot_description = {"robot_description": ParameterValue(robot_description_content, value_type=str)}
    robot_description_semantic = {"robot_description_semantic": load_text(pkg, "config/assembly_real.srdf")}
    robot_description_kinematics = {
        "robot_description_kinematics": load_yaml(pkg, "config/kinematics.yaml")["/**"][
            "ros__parameters"
        ]["robot_description_kinematics"]
    }
    robot_description_planning = {"robot_description_planning": load_yaml(pkg, "config/joint_limits.yaml")["joint_limits"]}
    ompl_planning = load_yaml(pkg, "config/ompl_planning.yaml")
    moveit_controllers = load_yaml(pkg, "config/moveit_controllers.yaml")

    planning_pipeline = {
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
    planning_pipeline["ompl"].update(ompl_planning)

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            planning_pipeline,
            moveit_controllers,
            {
                "publish_robot_description": True,
                "publish_robot_description_semantic": True,
                "publish_planning_scene": True,
                "publish_geometry_updates": True,
                "publish_state_updates": True,
                "publish_transforms_updates": True,
                "trajectory_execution.execution_duration_monitoring": False,
                "trajectory_execution.allowed_start_tolerance": 0.05,
                "trajectory_execution.allowed_execution_duration_scaling": 1.2,
                "trajectory_execution.allowed_goal_duration_margin": 0.5,
                "allow_trajectory_execution": True,
            },
        ],
    )

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        condition=IfCondition(launch_rviz),
        arguments=["-d", PathJoinSubstitution([FindPackageShare(pkg), "config", "moveit.rviz"])],
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            planning_pipeline,
            robot_description_planning,
        ],
    )

    ur_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare(pkg), "launch", "include", "ur_driver_bringup.launch.py"])
        ),
        condition=IfCondition(launch_driver),
        launch_arguments={
            "ur_type": ur_type,
            "robot_ip": robot_ip,
            "headless_mode": headless_mode,
            "launch_dashboard_client": launch_dashboard_client,
            "reverse_ip": reverse_ip,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("robot_ip"),
        DeclareLaunchArgument("ur_type", default_value="ur10"),
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument("launch_driver", default_value="true"),
        DeclareLaunchArgument("headless_mode", default_value="false"),
        DeclareLaunchArgument("launch_dashboard_client", default_value="true"),
        DeclareLaunchArgument("reverse_ip", default_value="10.160.9.100"),
        ur_driver,
        rsp,
        move_group,
        rviz,
    ])
