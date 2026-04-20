from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.conditions import UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    start_rviz = LaunchConfiguration("start_rviz")
    start_cpp_demo = LaunchConfiguration("start_cpp_demo")
    start_py_demo = LaunchConfiguration("start_py_demo")
    start_py_tools = LaunchConfiguration("start_py_tools")
    enable_overhead_camera = LaunchConfiguration("enable_overhead_camera")
    capture_pcd_on_start = LaunchConfiguration("capture_pcd_on_start")
    import_pcd_obstacle = LaunchConfiguration("import_pcd_obstacle")
    cleanup_existing_processes = LaunchConfiguration("cleanup_existing_processes")
    pcd_file = LaunchConfiguration("pcd_file")
    pointcloud_topic = LaunchConfiguration("pointcloud_topic")
    obstacle_id = LaunchConfiguration("obstacle_id")
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

    # Clean up any stale processes from a previous bringup so a second launch
    # doesn't attach to an old Gazebo/controller_manager instance.
    cleanup_processes = ExecuteProcess(
        cmd=[
            "bash",
            "-lc",
            (
                "pkill -9 -f '[g]zserver .*ur10_perception.*/obstacle_scene.world' || true; "
                "pkill -9 -f '[g]zserver .*ur10_perception.*/gantry_only.world' || true; "
                "pkill -9 -f '[g]zclient' || true; "
                "pkill -9 -f '/root/moveit_ws/install/moveit_ros_move_[g]roup/lib/moveit_ros_move_group/move_group' || true; "
                "pkill -9 -f '/opt/ros/humble/lib/[r]obot_state_publisher/robot_state_publisher' || true; "
                "pkill -9 -f '/root/ur10_ws/install/ur10_perception/lib/ur10_perception/[s]ynthetic_overhead_camera_node' || true; "
                "pkill -9 -f '/root/ur10_ws/install/ur10_perception/lib/ur10_perception/[p]cd_capture_node' || true; "
                "pkill -9 -f '/root/ur10_ws/install/ur10_perception/lib/ur10_perception/[p]cd_to_collision_scene_node' || true; "
                "pkill -9 -f '/root/ur10_ws/install/ur10_examples/lib/ur10_examples/move_group_interface_[d]emo' || true; "
                "pkill -9 -f '/root/ur10_ws/install/ur10_examples_py/bin/[m]oveit_py_demo' || true; "
                "pkill -9 -f '/root/ur10_ws/install/ur10_examples_py/bin/[c]apture_and_import_pcd' || true; "
                "sleep 2"
            ),
        ],
        output="screen",
        condition=IfCondition(cleanup_existing_processes),
    )

    gazebo_launch = TimerAction(
        period=2.5,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_simulation_bringup"), "launch", "gazebo_sim.launch.py"]
                    )
                ),
        launch_arguments={
            "ur_type": ur_type,
            "use_fake_hardware": use_fake_hardware,
            "world": world,
            "gantry_x_initial": gantry_x_initial,
            "gantry_y_initial": gantry_y_initial,
            "gantry_z_initial": gantry_z_initial,
            "gantry_x_min": gantry_x_min,
            "gantry_x_max": gantry_x_max,
            "gantry_y_min": gantry_y_min,
            "gantry_y_max": gantry_y_max,
            "gantry_z_min": gantry_z_min,
            "gantry_z_max": gantry_z_max,
            "gantry_base_height": gantry_base_height,
        }.items(),
    )
        ],
    )

    moveit_launch = TimerAction(
        period=5.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [
                            FindPackageShare("ur10_simulation_bringup"),
                            "launch",
                            "moveit_planning.launch.py",
                        ]
                    )
                ),
                launch_arguments={
                    "ur_type": ur_type,
                    "start_rviz": start_rviz,
                    "gantry_x_initial": gantry_x_initial,
                    "gantry_y_initial": gantry_y_initial,
                    "gantry_z_initial": gantry_z_initial,
                    "gantry_x_min": gantry_x_min,
                    "gantry_x_max": gantry_x_max,
                    "gantry_y_min": gantry_y_min,
                    "gantry_y_max": gantry_y_max,
                    "gantry_z_min": gantry_z_min,
                    "gantry_z_max": gantry_z_max,
                    "gantry_base_height": gantry_base_height,
                }.items(),
            )
        ],
    )

    demo_launch = TimerAction(
        period=9.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur10_simulation_bringup"), "launch", "demo_nodes.launch.py"]
                    )
                ),
                launch_arguments={
                    "start_cpp_demo": start_cpp_demo,
                    "start_py_demo": start_py_demo,
                    "obstacle_id": obstacle_id,
                    "wait_for_obstacle": import_pcd_obstacle,
                    "gantry_x_initial": gantry_x_initial,
                    "gantry_y_initial": gantry_y_initial,
                    "gantry_z_initial": gantry_z_initial,
                    "gantry_x_min": gantry_x_min,
                    "gantry_x_max": gantry_x_max,
                    "gantry_y_min": gantry_y_min,
                    "gantry_y_max": gantry_y_max,
                    "gantry_z_min": gantry_z_min,
                    "gantry_z_max": gantry_z_max,
                    "gantry_base_height": gantry_base_height,
                }.items(),
            )
        ],
    )

    pcd_capture = Node(
        package="ur10_perception",
        executable="pcd_capture_node",
        name="pcd_capture_node",
        output="screen",
        condition=IfCondition(capture_pcd_on_start),
        parameters=[{"pointcloud_topic": pointcloud_topic, "output_file": pcd_file, "use_sim_time": True}],
    )

    pcd_import = Node(
        package="ur10_perception",
        executable="pcd_to_collision_scene_node",
        name="pcd_to_collision_scene_node",
        output="screen",
        condition=IfCondition(import_pcd_obstacle),
        parameters=[{"pcd_file": pcd_file, "obstacle_id": obstacle_id, "use_sim_time": True}],
    )

    py_helper = Node(
        package="ur10_examples_py",
        executable="capture_and_import_pcd",
        output="screen",
        condition=IfCondition(start_py_tools),
        parameters=[{"pcd_file": pcd_file, "pointcloud_topic": pointcloud_topic, "obstacle_id": obstacle_id}],
    )

    synthetic_camera = TimerAction(
        period=2.5,
        actions=[
            Node(
                package="ur10_perception",
                executable="synthetic_overhead_camera_node",
                name="synthetic_overhead_camera_node",
                output="screen",
                condition=IfCondition(enable_overhead_camera),
                parameters=[
                    {"pointcloud_topic": pointcloud_topic, "frame_id": "world", "use_sim_time": True}
                ],
            )
        ],
    )

    direct_demo_launch = TimerAction(
        period=14.0,
        condition=UnlessCondition(import_pcd_obstacle),
        actions=[demo_launch],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("ur_type", default_value="ur10"),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument("start_rviz", default_value="true"),
            DeclareLaunchArgument("start_cpp_demo", default_value="false"),
            DeclareLaunchArgument("start_py_demo", default_value="false"),
            DeclareLaunchArgument("start_py_tools", default_value="false"),
            DeclareLaunchArgument("enable_overhead_camera", default_value="false"),
            DeclareLaunchArgument("capture_pcd_on_start", default_value="false"),
            DeclareLaunchArgument("import_pcd_obstacle", default_value="false"),
            DeclareLaunchArgument("cleanup_existing_processes", default_value="true"),
            DeclareLaunchArgument("pcd_file", default_value="/root/ur10_ws/data/latest_obstacle.pcd"),
            DeclareLaunchArgument("pointcloud_topic", default_value="/overhead_camera/points"),
            DeclareLaunchArgument("obstacle_id", default_value="pcd_obstacle_box"),
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
            cleanup_processes,
            gazebo_launch,
            synthetic_camera,
            moveit_launch,
            TimerAction(period=11.0, actions=[pcd_capture]),
            RegisterEventHandler(OnProcessExit(target_action=pcd_capture, on_exit=[pcd_import])),
            RegisterEventHandler(OnProcessExit(target_action=pcd_import, on_exit=[demo_launch])),
            direct_demo_launch,
            py_helper,
        ]
    )
