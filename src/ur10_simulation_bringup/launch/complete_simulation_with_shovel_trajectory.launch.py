from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    planner_mode = LaunchConfiguration('planner_mode')
    start_rviz = LaunchConfiguration('start_rviz')

    complete_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare('ur10_simulation_bringup'), 'launch', 'complete_simulation.launch.py']
            )
        ),
        launch_arguments={
            'start_rviz': start_rviz,
            'enable_overhead_camera': 'false',
            'start_cpp_demo': 'false',
            'start_py_demo': 'false',
            'start_py_tools': 'false',
            'import_pcd_obstacle': 'false',
        }.items(),
    )

    shovel_pipeline = TimerAction(
        period=10.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare('ur10_trajectory_planner'), 'launch', 'shovel_bucket_pipeline.launch.py']
                    )
                ),
                launch_arguments={'planner_mode': planner_mode}.items(),
            )
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('planner_mode', default_value='dp_rrt'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        complete_sim,
        shovel_pipeline,
    ])
