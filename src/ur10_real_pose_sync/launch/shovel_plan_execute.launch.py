import os
import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PythonExpression, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def _load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _load_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_launch_description():
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config = LaunchConfiguration('rviz_config')
    ur_ip = LaunchConfiguration('ur_ip')
    ur_port = LaunchConfiguration('ur_port')
    socket_timeout_sec = LaunchConfiguration('socket_timeout_sec')
    cleanup_on_start = LaunchConfiguration('cleanup_on_start')
    run_micro_diag = LaunchConfiguration('run_micro_diag')
    execution_mode = LaunchConfiguration('execution_mode')
    real_pose_source = LaunchConfiguration('real_pose_source')
    real_joint_states_input_topic = LaunchConfiguration('real_joint_states_input_topic')
    real_controller_action = LaunchConfiguration('real_controller_action')

    xacro_file = TextSubstitution(
        text='/root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro'
    )

    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
        ' ',
        'mesh_root:=file:///root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/meshes',
    ])
    robot_description = {'robot_description': ParameterValue(robot_description_content, value_type=str)}

    moveit_pkg_share = '/root/ur10_ws/src/ur_base_xarco_model/assembly_moveit_config'
    this_pkg_share = '/root/ur10_ws/src/ur10_real_pose_sync'

    robot_description_semantic = {
        'robot_description_semantic': _load_text(os.path.join(this_pkg_share, 'config', 'assembly_xacro.srdf'))
    }

    robot_description_kinematics = {
        'robot_description_kinematics': _load_yaml(
            os.path.join(moveit_pkg_share, 'config', 'kinematics.yaml')
        )['/**']['ros__parameters']['robot_description_kinematics']
    }

    robot_description_planning = {
        'robot_description_planning': _load_yaml(
            os.path.join(moveit_pkg_share, 'config', 'joint_limits.yaml')
        )['joint_limits']
    }

    ompl_planning_pipeline_config = {
        'planning_pipelines': ['ompl'],
        'default_planning_pipeline': 'ompl',
        'ompl': {
            'planning_plugin': 'ompl_interface/OMPLPlanner',
            'request_adapters': 'default_planner_request_adapters/AddTimeOptimalParameterization '
                                'default_planner_request_adapters/FixWorkspaceBounds '
                                'default_planner_request_adapters/FixStartStateBounds '
                                'default_planner_request_adapters/FixStartStateCollision '
                                'default_planner_request_adapters/FixStartStatePathConstraints',
            'start_state_max_bounds_error': 0.1,
            'num_planning_attempts': 30,
            'planning_time': 15.0,
        },
    }
    ompl_planning_pipeline_config['ompl'].update(
        _load_yaml(os.path.join(moveit_pkg_share, 'config', 'ompl_planning.yaml'))
    )

    moveit_controllers = {
        'moveit_simple_controller_manager': _load_yaml(
            os.path.join(this_pkg_share, 'config', 'moveit_controllers_virtual.yaml')
        ),
        'moveit_controller_manager': 'moveit_simple_controller_manager/MoveItSimpleControllerManager',
    }

    trajectory_execution = {
        'moveit_manage_controllers': False,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.03,
        'trajectory_execution.execution_duration_monitoring': False,
        'allow_trajectory_execution': True,
    }

    planning_scene_monitor_parameters = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
        'publish_robot_description': True,
        'publish_robot_description_semantic': True,
    }

    warehouse_ros_config = {
        'warehouse_plugin': 'warehouse_ros_sqlite::DatabaseConnection',
        'warehouse_host': os.path.expanduser('~/.ros/warehouse_assembly.sqlite'),
    }

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='plan_exec_robot_state_publisher',
        output='screen',
        parameters=[robot_description],
        remappings=[
            ('/joint_states', '/assembly/joint_states'),
            ('joint_states', '/assembly/joint_states'),
        ],
    )

    real_state_node = Node(
        package='ur10_real_pose_sync',
        executable='ur10_joint_state_tcp_node',
        name='plan_exec_ur10_joint_state_tcp_node',
        condition=IfCondition(PythonExpression(["'", execution_mode, "' == 'virtual'"])),
        output='screen',
        parameters=[{
            'ur_ip': ur_ip,
            'ur_port': ur_port,
            'socket_timeout_sec': socket_timeout_sec,
            'output_topic': '/real_joint_states',
        }],
    )

    real_pose_tcp_node = Node(
        package='ur10_real_pose_sync',
        executable='ur10_joint_state_tcp_node',
        name='plan_exec_real_pose_tcp_node',
        condition=IfCondition(
            PythonExpression(["'", execution_mode, "' == 'real' and '", real_pose_source, "' == 'tcp_debug'"])
        ),
        output='screen',
        parameters=[{
            'ur_ip': ur_ip,
            'ur_port': ur_port,
            'socket_timeout_sec': socket_timeout_sec,
            'output_topic': '/assembly/joint_states',
        }],
    )

    virtual_controller_node = Node(
        package='ur10_real_pose_sync',
        executable='virtual_trajectory_controller',
        name='plan_exec_virtual_trajectory_controller',
        condition=IfCondition(PythonExpression(["'", execution_mode, "' == 'virtual'"])),
        output='screen',
        parameters=[{
            'joint_names': [
                'ur10_shoulder_pan', 'ur10_shoulder_lift', 'ur10_elbow',
                'ur10_wrist_1', 'ur10_wrist_2', 'ur10_wrist_3'
            ],
            'initial_positions': [2.2038776874542236, 0.06395161151885986, -1.7774718443499964,
                                  -0.04721385637392217, 1.8873671293258667, 0.9308245182037354],
            'joint_state_topic': '/assembly/joint_states',
            'publish_rate_hz': 125.0,
            'passthrough_topic': '/real_joint_states',
            'passthrough_mode': 'until_first_goal',
        }],
    )

    real_joint_state_remap_node = Node(
        package='ur10_real_pose_sync',
        executable='ur10_joint_state_remap_node',
        name='plan_exec_real_joint_state_remap_node',
        condition=IfCondition(
            PythonExpression(["'", execution_mode, "' == 'real' and '", real_pose_source, "' == 'driver'"])
        ),
        output='screen',
        parameters=[{
            'input_topic': real_joint_states_input_topic,
            'output_topic': '/assembly/joint_states',
            'source_joint_names': [
                'shoulder_pan_joint',
                'shoulder_lift_joint',
                'elbow_joint',
                'wrist_1_joint',
                'wrist_2_joint',
                'wrist_3_joint',
            ],
            'target_joint_names': [
                'ur10_shoulder_pan',
                'ur10_shoulder_lift',
                'ur10_elbow',
                'ur10_wrist_1',
                'ur10_wrist_2',
                'ur10_wrist_3',
            ],
            'position_signs': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            'position_offsets': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }],
    )

    real_trajectory_bridge_node = Node(
        package='ur10_real_pose_sync',
        executable='real_trajectory_bridge',
        name='plan_exec_real_trajectory_bridge',
        condition=IfCondition(PythonExpression(["'", execution_mode, "' == 'real'"])),
        output='screen',
        parameters=[{
            'incoming_action_name': '/joint_trajectory_controller/follow_joint_trajectory',
            'forward_action_name': real_controller_action,
            'source_joint_names': [
                'ur10_shoulder_pan',
                'ur10_shoulder_lift',
                'ur10_elbow',
                'ur10_wrist_1',
                'ur10_wrist_2',
                'ur10_wrist_3',
            ],
            'target_joint_names': [
                'shoulder_pan_joint',
                'shoulder_lift_joint',
                'elbow_joint',
                'wrist_1_joint',
                'wrist_2_joint',
                'wrist_3_joint',
            ],
        }],
    )

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        name='plan_exec_move_group',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            ompl_planning_pipeline_config,
            moveit_controllers,
            trajectory_execution,
            planning_scene_monitor_parameters,
            {'use_sim_time': False},
            warehouse_ros_config,
        ],
        remappings=[
            ('/joint_states', '/assembly/joint_states'),
            ('joint_states', '/assembly/joint_states'),
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='plan_exec_rviz2_moveit',
        output='screen',
        condition=IfCondition(use_rviz),
        arguments=['-d', rviz_config],
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            ompl_planning_pipeline_config,
            {'use_sim_time': False},
        ],
    )

    micro_diag_node = Node(
        package='ur10_real_pose_sync',
        executable='micro_plan_diagnostic_node',
        name='plan_exec_micro_plan_diagnostic',
        output='screen',
        condition=IfCondition(run_micro_diag),
        parameters=[{
            'group_name': 'assembly_manipulator',
            'target_link': 'sensor_shovel_tcp',
            'base_frame': 'base_jizuo',
            'joint_state_topic': '/assembly/joint_states',
            'dx': 0.005,
            'dy': 0.0,
            'dz': 0.0,
        }],
    )

    cleanup_process = ExecuteProcess(
        condition=IfCondition(cleanup_on_start),
        cmd=[
            'bash', '-lc',
            "for p in 'moveit_ros_move_group.*move_group' 'robot_state_publisher' 'virtual_trajectory_controller' 'ur10_joint_state_tcp_node' 'real_trajectory_bridge' 'ur10_joint_state_remap_node'; do "
            "pgrep -f \"$p\" | grep -vw $$ | xargs -r kill; "
            "done; exit 0"
        ],
        output='screen',
    )

    start_state_and_execution_chain = TimerAction(
        period=0.5,
        actions=[
            real_state_node,
            real_pose_tcp_node,
            virtual_controller_node,
            real_joint_state_remap_node,
            real_trajectory_bridge_node,
        ],
    )

    start_visual_and_planning_chain = TimerAction(
        period=1.5,
        actions=[
            robot_state_publisher_node,
            move_group_node,
            rviz_node,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('cleanup_on_start', default_value='true'),
        DeclareLaunchArgument('run_micro_diag', default_value='false'),
        DeclareLaunchArgument('execution_mode', default_value='real'),
        DeclareLaunchArgument('real_pose_source', default_value='driver'),
        DeclareLaunchArgument('real_joint_states_input_topic', default_value='/joint_states'),
        DeclareLaunchArgument('real_controller_action', default_value='/scaled_joint_trajectory_controller/follow_joint_trajectory'),
        DeclareLaunchArgument('ur_ip', default_value='10.160.9.21'),
        DeclareLaunchArgument('ur_port', default_value='30003'),
        DeclareLaunchArgument('socket_timeout_sec', default_value='3.0'),
        DeclareLaunchArgument(
            'rviz_config',
            default_value='/root/ur10_ws/src/ur10_real_pose_sync/config/shovel_plan_execute.rviz',
        ),
        cleanup_process,
        start_state_and_execution_chain,
        start_visual_and_planning_chain,
        micro_diag_node,
    ])
