from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, TimerAction
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
    pcd_file = LaunchConfiguration("pcd_file")
    pointcloud_topic = LaunchConfiguration("pointcloud_topic")
    obstacle_id = LaunchConfiguration("obstacle_id")
    world = LaunchConfiguration("world")

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur10_simulation_bringup"), "launch", "gazebo_sim.launch.py"]
            )
        ),
        launch_arguments={
            "ur_type": ur_type,
            "use_fake_hardware": use_fake_hardware,
            "world": world,
        }.items(),
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
                launch_arguments={"ur_type": ur_type, "start_rviz": start_rviz}.items(),
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

    synthetic_camera = Node(
        package="ur10_perception",
        executable="synthetic_overhead_camera_node",
        name="synthetic_overhead_camera_node",
        output="screen",
        condition=IfCondition(enable_overhead_camera),
        parameters=[{"pointcloud_topic": pointcloud_topic, "frame_id": "world", "use_sim_time": True}],
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
            DeclareLaunchArgument("start_cpp_demo", default_value="true"),
            DeclareLaunchArgument("start_py_demo", default_value="false"),
            DeclareLaunchArgument("start_py_tools", default_value="false"),
            DeclareLaunchArgument("enable_overhead_camera", default_value="true"),
            DeclareLaunchArgument("capture_pcd_on_start", default_value="true"),
            DeclareLaunchArgument("import_pcd_obstacle", default_value="true"),
            DeclareLaunchArgument("pcd_file", default_value="/root/ur10_ws/data/latest_obstacle.pcd"),
            DeclareLaunchArgument("pointcloud_topic", default_value="/overhead_camera/points"),
            DeclareLaunchArgument("obstacle_id", default_value="pcd_obstacle_box"),
            DeclareLaunchArgument(
                "world",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("ur10_perception"), "worlds", "obstacle_scene.world"]
                ),
            ),
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
