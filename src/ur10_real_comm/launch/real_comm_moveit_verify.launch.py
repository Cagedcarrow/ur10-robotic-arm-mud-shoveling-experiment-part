from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import ConcatSubstitution, LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")
    robot_ip = LaunchConfiguration("robot_ip")
    reverse_ip = LaunchConfiguration("reverse_ip")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_dashboard_client = LaunchConfiguration("launch_dashboard_client")
    initial_joint_controller = LaunchConfiguration("initial_joint_controller")
    headless_mode = LaunchConfiguration("headless_mode")
    wrist3_delta_deg = LaunchConfiguration("wrist3_delta_deg")
    confirm_execute = LaunchConfiguration("confirm_execute")
    planning_group = LaunchConfiguration("planning_group")
    planning_tip_link = LaunchConfiguration("planning_tip_link")

    driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ur_robot_driver"), "launch", "ur_control.launch.py"])
        ),
        launch_arguments={
            "ur_type": ur_type,
            "robot_ip": robot_ip,
            "reverse_ip": reverse_ip,
            "launch_dashboard_client": launch_dashboard_client,
            "initial_joint_controller": initial_joint_controller,
            "launch_rviz": "false",
            "use_fake_hardware": "false",
            "headless_mode": headless_mode,
        }.items(),
    )

    moveit_launch = TimerAction(
        period=4.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_moveit_config"), "launch", "ur_moveit.launch.py"]
                    )
                ),
                launch_arguments={
                    "ur_type": ur_type,
                    "description_package": "ur10_description",
                    "description_file": "ur10_sim.urdf.xacro",
                    "moveit_config_package": "ur10_moveit_config",
                    "moveit_config_file": "ur.srdf.xacro",
                    "use_sim_time": "false",
                    "sim_gazebo": "false",
                    "use_fake_hardware": "false",
                    "launch_rviz": launch_rviz,
                    "planning_tip_link": planning_tip_link,
                }.items(),
            )
        ],
    )

    verify_node_exec = PathJoinSubstitution(
        [FindPackageShare("ur10_real_comm"), "..", "..", "bin", "motion_verify_node"]
    )
    verify_node = TimerAction(
        period=8.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    verify_node_exec,
                    "--ros-args",
                    "--params-file",
                    PathJoinSubstitution([FindPackageShare("ur10_real_comm"), "config", "verify.yaml"]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="ur_type:="), ur_type]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="planning_group:="), planning_group]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="planning_tip_link:="), planning_tip_link]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="initial_joint_controller:="), initial_joint_controller]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="wrist3_delta_deg:="), wrist3_delta_deg]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="confirm_execute:="), confirm_execute]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="launch_dashboard_client:="), launch_dashboard_client]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="robot_ip:="), robot_ip]),
                    "-p",
                    ConcatSubstitution([TextSubstitution(text="reverse_ip:="), reverse_ip]),
                ],
                output="screen",
            )
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("robot_ip", default_value="192.168.56.101"),
            DeclareLaunchArgument("reverse_ip", default_value="192.168.56.1"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("launch_dashboard_client", default_value="true"),
            DeclareLaunchArgument(
                "initial_joint_controller", default_value="scaled_joint_trajectory_controller"
            ),
            DeclareLaunchArgument("headless_mode", default_value="false"),
            DeclareLaunchArgument("wrist3_delta_deg", default_value="0.5"),
            DeclareLaunchArgument("confirm_execute", default_value="true"),
            DeclareLaunchArgument("planning_group", default_value="ur_manipulator"),
            DeclareLaunchArgument("planning_tip_link", default_value="tool0"),
            driver_launch,
            moveit_launch,
            verify_node,
        ]
    )
