from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    use_sim_time = LaunchConfiguration("use_sim_time")
    world = LaunchConfiguration("world")
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
            "use_fake_hardware:=",
            use_fake_hardware,
            " ",
            "sim_gazebo:=true",
        ]
    )
    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("gazebo_ros"), "launch", "gazebo.launch.py"])
        ),
        launch_arguments={"world": world}.items(),
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
        arguments=["-topic", "robot_description", "-entity", "ur10"],
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
                "x": gantry_x_initial,
                "y": gantry_y_initial,
                "z": gantry_z_initial,
                "duration_sec": 4.0,
                "use_sim_time": use_sim_time,
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
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
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ur10_perception"), "worlds", "gantry_only.world"]
                ),
            ),
            gazebo,
            robot_state_publisher,
            spawn_robot,
            RegisterEventHandler(
                OnProcessExit(target_action=spawn_robot, on_exit=[joint_state_broadcaster])
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=joint_state_broadcaster, on_exit=[joint_trajectory_controller]
                )
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=joint_trajectory_controller, on_exit=[gantry_trajectory_controller]
                )
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=gantry_trajectory_controller, on_exit=[gantry_initializer]
                )
            ),
        ]
    )
