from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    headless = LaunchConfiguration('headless')
    start_rviz = LaunchConfiguration('start_rviz')
    gazebo_gui = LaunchConfiguration('gazebo_gui')
    planner_mode = LaunchConfiguration('planner_mode')
    execution_mode = LaunchConfiguration('execution_mode')
    use_bucket = LaunchConfiguration('use_bucket')

    world = LaunchConfiguration('world')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('my_robot'), 'launch', 'sim_planning_gantry.launch.py'])
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'start_rviz': PythonExpression(["'false' if '", headless, "' == 'true' else '", start_rviz, "'"]),
            'gui': PythonExpression(["'false' if '", headless, "' == 'true' else '", gazebo_gui, "'"]),
            'start_gantry_rviz_control': 'false',
            'world': world,
        }.items(),
    )

    planner_pipeline = TimerAction(
        period=7.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare('ur10_trajectory_planner'),
                        'launch',
                        'shovel_bucket_pipeline.launch.py',
                    ])
                ),
                launch_arguments={
                    'planner_mode': planner_mode,
                    'execution_mode': execution_mode,
                    'safe_margin': LaunchConfiguration('safe_margin'),
                }.items(),
            )
        ],
    )

    bucket_node = Node(
        package='ur10_bringup',
        executable='bucket_scene_node',
        name='bucket_scene_node',
        output='screen',
        parameters=[{
            'use_bucket': use_bucket,
            'bucket_center_x': LaunchConfiguration('bucket_center_x'),
            'bucket_center_y': LaunchConfiguration('bucket_center_y'),
            'bucket_center_z': LaunchConfiguration('bucket_center_z'),
            'bucket_radius': LaunchConfiguration('bucket_radius'),
            'bucket_height': LaunchConfiguration('bucket_height'),
            'bucket_wall_thickness': LaunchConfiguration('bucket_wall_thickness'),
            'safe_margin': LaunchConfiguration('safe_margin'),
        }],
    )

    gui_node = Node(
        package='ur10_unified_gui',
        executable='gui_node',
        name='ur10_unified_gui',
        output='screen',
        condition=UnlessCondition(headless),
        parameters=[{
            'planner_mode': planner_mode,
            'execution_mode': execution_mode,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        DeclareLaunchArgument('gazebo_gui', default_value='true'),
        DeclareLaunchArgument('planner_mode', default_value='dp_rrt'),
        DeclareLaunchArgument('execution_mode', default_value='demo'),
        DeclareLaunchArgument('use_bucket', default_value='true'),
        DeclareLaunchArgument(
            'world',
            default_value=PathJoinSubstitution([FindPackageShare('ur10_perception'), 'worlds', 'gantry_only.world']),
        ),
        DeclareLaunchArgument('bucket_center_x', default_value='0.8'),
        DeclareLaunchArgument('bucket_center_y', default_value='0.0'),
        DeclareLaunchArgument('bucket_center_z', default_value='0.0'),
        DeclareLaunchArgument('bucket_radius', default_value='0.18'),
        DeclareLaunchArgument('bucket_height', default_value='0.30'),
        DeclareLaunchArgument('bucket_wall_thickness', default_value='0.005'),
        DeclareLaunchArgument('safe_margin', default_value='0.03'),
        sim,
        bucket_node,
        planner_pipeline,
        gui_node,
    ])
