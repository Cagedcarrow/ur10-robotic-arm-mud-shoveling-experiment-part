from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_share = get_package_share_directory('ur10_trajectory_planner')
    traj_cfg = os.path.join(pkg_share, 'config', 'trajectory_params.yaml')
    plan_cfg = os.path.join(pkg_share, 'config', 'planner_params.yaml')
    exec_cfg = os.path.join(pkg_share, 'config', 'executor_params.yaml')

    planner_mode = LaunchConfiguration('planner_mode')
    execution_mode = LaunchConfiguration('execution_mode')
    safe_margin = LaunchConfiguration('safe_margin')

    return LaunchDescription([
        DeclareLaunchArgument('planner_mode', default_value='dp_rrt'),
        DeclareLaunchArgument('execution_mode', default_value='demo'),
        DeclareLaunchArgument('safe_margin', default_value='0.03'),
        Node(
            package='ur10_trajectory_planner',
            executable='trajectory_node',
            name='trajectory_node',
            parameters=[traj_cfg, {'bucket.safe_margin': safe_margin}],
            output='screen'),
        Node(
            package='ur10_trajectory_planner',
            executable='planner_node',
            name='planner_node',
            parameters=[plan_cfg, {'planner_mode': planner_mode}],
            output='screen'),
        Node(
            package='ur10_trajectory_planner',
            executable='executor_node',
            name='executor_node',
            parameters=[exec_cfg, {'execution_mode': execution_mode}],
            output='screen'),
    ])
