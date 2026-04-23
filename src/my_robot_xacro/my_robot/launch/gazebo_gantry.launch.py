import json

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


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
    world = LaunchConfiguration("world")
    gui = LaunchConfiguration("gui")

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

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("gazebo_ros"), "launch", "gazebo.launch.py"])
        ),
        launch_arguments={
            "world": world,
            "gui": gui,
        }.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description, {"use_sim_time": use_sim_time}],
    )

    spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        output="screen",
        arguments=["-topic", "robot_description", "-entity", "my_robot_gantry"],
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    joint_trajectory_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    gantry_trajectory_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gantry_trajectory_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    gantry_initializer = Node(
        package="ur10_examples_py",
        executable="gantry_control",
        output="screen",
        parameters=[
            {
                "x": float(gantry_config["initial"]["x"]),
                "y": float(gantry_config["initial"]["y"]),
                "z": float(gantry_config["initial"]["z"]),
                "duration_sec": 4.0,
                "use_sim_time": True,
            }
        ],
    )

    return [
        gazebo,
        robot_state_publisher,
        TimerAction(period=2.0, actions=[spawn_robot]),
        RegisterEventHandler(
            OnProcessExit(target_action=spawn_robot, on_exit=[joint_state_broadcaster])
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=joint_state_broadcaster,
                on_exit=[joint_trajectory_controller],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=joint_trajectory_controller,
                on_exit=[gantry_trajectory_controller],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=gantry_trajectory_controller,
                on_exit=[gantry_initializer],
            )
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("gui", default_value="true"),
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ur10_perception"), "worlds", "gantry_only.world"]
                ),
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
