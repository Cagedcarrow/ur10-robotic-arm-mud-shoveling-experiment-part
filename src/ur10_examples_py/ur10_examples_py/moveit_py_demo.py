import os
import sys
import time
from pathlib import Path
import subprocess
from typing import Optional

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory

from ur10_examples_py.env_bootstrap import bootstrap_ros_python_environment


bootstrap_ros_python_environment()


def _get_string_parameter(node, name: str) -> Optional[str]:
    if not node.has_parameter(name):
        return None
    parameter = node.get_parameter(name)
    if parameter.type_ == parameter.Type.NOT_SET:
        return None
    return parameter.value


def _declare_if_missing(node, name: str, default_value):
    if not node.has_parameter(name):
        node.declare_parameter(name, default_value)


def main():
    try:
        from moveit.core.robot_state import RobotState
        from moveit.planning import MoveItPy, PlanRequestParameters
        from ur10_moveit_config.launch_common import load_yaml
    except ImportError as exc:
        raise RuntimeError(
            "moveit_py is not available. Build /root/moveit_ws with the moveit_py package first."
        ) from exc

    rclpy.init(args=sys.argv)
    node = rclpy.create_node(
        "ur10_moveit_py_demo", automatically_declare_parameters_from_overrides=True
    )
    _declare_if_missing(node, "planning_group", "ur_manipulator")
    _declare_if_missing(node, "execute", True)
    _declare_if_missing(
        node,
        "goal_joint_positions",
        [-1.20, -1.70, 2.05, -1.95, -1.57, 0.0],
    )
    _declare_if_missing(node, "ur_type", "ur10")
    _declare_if_missing(node, "description_package", "ur10_description")
    _declare_if_missing(node, "description_file", "ur10_sim.urdf.xacro")
    _declare_if_missing(node, "moveit_config_package", "ur10_moveit_config")
    _declare_if_missing(node, "moveit_config_file", "ur.srdf.xacro")
    _declare_if_missing(node, "semantic_robot_name", "ur")
    _declare_if_missing(node, "planning_tip_link", "tool0")
    _declare_if_missing(node, "gantry_x_initial", 0.0)
    _declare_if_missing(node, "gantry_y_initial", 0.0)
    _declare_if_missing(node, "gantry_z_initial", -0.6)
    _declare_if_missing(node, "gantry_x_min", -1.0)
    _declare_if_missing(node, "gantry_x_max", 1.0)
    _declare_if_missing(node, "gantry_y_min", -0.8)
    _declare_if_missing(node, "gantry_y_max", 0.8)
    _declare_if_missing(node, "gantry_z_min", -1.0)
    _declare_if_missing(node, "gantry_z_max", 0.0)
    _declare_if_missing(node, "gantry_base_height", 2.2)

    if not node.has_parameter("use_sim_time"):
      node.declare_parameter("use_sim_time", True)

    use_sim_time = node.get_parameter("use_sim_time").value

    planning_group = node.get_parameter("planning_group").value
    execute = node.get_parameter("execute").value
    goal_joint_positions = node.get_parameter("goal_joint_positions").value
    ur_type = node.get_parameter("ur_type").value
    description_package = node.get_parameter("description_package").value
    description_file = node.get_parameter("description_file").value
    moveit_config_package = node.get_parameter("moveit_config_package").value
    moveit_config_file = node.get_parameter("moveit_config_file").value
    semantic_robot_name = node.get_parameter("semantic_robot_name").value
    planning_tip_link = node.get_parameter("planning_tip_link").value

    robot_description = _get_string_parameter(node, "robot_description")
    robot_description_semantic = _get_string_parameter(node, "robot_description_semantic")

    if robot_description is None or robot_description_semantic is None:
        description_share = Path(get_package_share_directory(description_package))
        moveit_config_share = Path(get_package_share_directory(moveit_config_package))

        if description_package == "ur10_description" and description_file == "ur10_sim.urdf.xacro":
            ur_description_share = Path(get_package_share_directory("ur_description"))
            robot_description_command = [
                "xacro",
                str(description_share / "urdf" / description_file),
                f"ur_type:={ur_type}",
                "robot_name:=ur",
                "use_fake_hardware:=false",
                "sim_gazebo:=true",
                f"joint_limit_params:={ur_description_share / 'config' / ur_type / 'joint_limits.yaml'}",
                f"kinematics_params:={ur_description_share / 'config' / ur_type / 'default_kinematics.yaml'}",
                f"physical_params:={ur_description_share / 'config' / ur_type / 'physical_parameters.yaml'}",
                f"visual_params:={ur_description_share / 'config' / ur_type / 'visual_parameters.yaml'}",
                f"gantry_x_initial:={node.get_parameter('gantry_x_initial').value}",
                f"gantry_y_initial:={node.get_parameter('gantry_y_initial').value}",
                f"gantry_z_initial:={node.get_parameter('gantry_z_initial').value}",
                f"gantry_x_min:={node.get_parameter('gantry_x_min').value}",
                f"gantry_x_max:={node.get_parameter('gantry_x_max').value}",
                f"gantry_y_min:={node.get_parameter('gantry_y_min').value}",
                f"gantry_y_max:={node.get_parameter('gantry_y_max').value}",
                f"gantry_z_min:={node.get_parameter('gantry_z_min').value}",
                f"gantry_z_max:={node.get_parameter('gantry_z_max').value}",
                f"gantry_base_height:={node.get_parameter('gantry_base_height').value}",
            ]
        else:
            robot_description_command = [
                "xacro",
                str(description_share / "urdf" / description_file),
                "ros_profile:=ros2",
                "ros_hardware_interface:=position",
                "sim_gazebo:=true",
                f"gantry_x_initial:={node.get_parameter('gantry_x_initial').value}",
                f"gantry_y_initial:={node.get_parameter('gantry_y_initial').value}",
                f"gantry_z_initial:={node.get_parameter('gantry_z_initial').value}",
                f"gantry_x_min:={node.get_parameter('gantry_x_min').value}",
                f"gantry_x_max:={node.get_parameter('gantry_x_max').value}",
                f"gantry_y_min:={node.get_parameter('gantry_y_min').value}",
                f"gantry_y_max:={node.get_parameter('gantry_y_max').value}",
                f"gantry_z_min:={node.get_parameter('gantry_z_min').value}",
                f"gantry_z_max:={node.get_parameter('gantry_z_max').value}",
                f"gantry_base_height:={node.get_parameter('gantry_base_height').value}",
            ]
            controllers_yaml = description_share / "config" / "ros2_controllers.yaml"
            if controllers_yaml.exists():
                robot_description_command.append(f"simulation_controllers:={controllers_yaml}")

        robot_description = subprocess.check_output(robot_description_command, text=True)
        robot_description_semantic = subprocess.check_output(
            [
                "xacro",
                str(moveit_config_share / "srdf" / moveit_config_file),
                f"name:={semantic_robot_name}",
                f"tip_link:={planning_tip_link}",
            ],
            text=True,
        )

    ompl_config = {
        "planning_plugin": "ompl_interface/OMPLPlanner",
        "request_adapters": "default_planner_request_adapters/AddTimeOptimalParameterization "
        "default_planner_request_adapters/FixWorkspaceBounds "
        "default_planner_request_adapters/FixStartStateBounds "
        "default_planner_request_adapters/FixStartStateCollision "
        "default_planner_request_adapters/FixStartStatePathConstraints",
        "start_state_max_bounds_error": 0.1,
    }
    ompl_config.update(load_yaml(moveit_config_package, "config/ompl_planning.yaml"))

    config_dict = {
        "robot_description": robot_description,
        "robot_description_semantic": robot_description_semantic,
        "robot_description_kinematics": load_yaml(moveit_config_package, "config/kinematics.yaml")[
            "/**"
        ]["ros__parameters"]["robot_description_kinematics"],
        "robot_description_planning": load_yaml(moveit_config_package, "config/joint_limits.yaml")[
            "joint_limits"
        ],
        "planning_scene_monitor_options": {
            "name": "planning_scene_monitor",
            "robot_description": "robot_description",
            "joint_state_topic": "joint_states",
            "attached_collision_object_topic": "attached_collision_object",
            "monitored_planning_scene_topic": "monitored_planning_scene",
            "publish_planning_scene_topic": "planning_scene",
            "wait_for_initial_state_timeout": 0.0,
        },
        "planning_pipelines": {
            "pipeline_names": ["ompl"],
            "namespace": "",
        },
        "ompl": ompl_config,
        "moveit_simple_controller_manager": load_yaml(
            moveit_config_package, "config/moveit_controllers.yaml"
        ),
        "moveit_controller_manager": "moveit_simple_controller_manager/MoveItSimpleControllerManager",
        "trajectory_execution.allowed_execution_duration_scaling": 1.2,
        "trajectory_execution.allowed_goal_duration_margin": 0.5,
        "trajectory_execution.allowed_start_tolerance": 0.0,
        "trajectory_execution.execution_duration_monitoring": False,
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        "publish_robot_description": True,
        "publish_robot_description_semantic": True,
    }

    moveit_py = MoveItPy(node_name="ur10_moveit_py_client", config_dict=config_dict)
    planning_component = moveit_py.get_planning_component(planning_group)
    time.sleep(2.0)

    try:
        robot_model = moveit_py.get_robot_model()
        goal_state = RobotState(robot_model)
        goal_state.set_joint_group_positions(
            planning_group, np.array(goal_joint_positions, dtype=float)
        )
        goal_state.update()

        planning_component.set_start_state_to_current_state()
        planning_component.set_goal_state(robot_state=goal_state)
        plan_parameters = PlanRequestParameters(moveit_py)
        plan_parameters.planning_pipeline = "ompl"
        plan_parameters.planner_id = "RRTConnectkConfigDefault"
        plan_parameters.planning_time = 10.0
        plan_parameters.max_velocity_scaling_factor = 0.05
        plan_parameters.max_acceleration_scaling_factor = 0.05
        plan_result = planning_component.plan(plan_parameters)
        if not plan_result:
            raise RuntimeError("Failed to generate a joint-space plan with moveit_py.")

        if execute:
            execution_status = moveit_py.execute(
                planning_group, plan_result.trajectory, blocking=True
            )
            status_text = getattr(execution_status, "status", str(execution_status))
            node.get_logger().info(f"moveit_py execution status: {status_text}")
            if not execution_status:
                raise RuntimeError(f"moveit_py execution failed with status: {status_text}")
            time.sleep(1.0)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    except Exception as exc:
        node.get_logger().error(str(exc))
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
    finally:
        pass


if __name__ == "__main__":
    main()
