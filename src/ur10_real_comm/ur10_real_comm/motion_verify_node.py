from __future__ import annotations

import json
import math
import sys
import threading
from typing import Dict, List, Optional

import rclpy
from controller_manager_msgs.srv import ListControllers
from control_msgs.action import FollowJointTrajectory
from moveit_msgs.msg import Constraints, JointConstraint
from moveit_msgs.srv import GetMotionPlan
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node


def _degrees_to_radians(value_deg: float) -> float:
    return value_deg * math.pi / 180.0


def _to_dict(msg: JointState) -> Dict[str, float]:
    return {name: msg.position[i] for i, name in enumerate(msg.name) if i < len(msg.position)}


class MotionVerifyNode(Node):
    def __init__(self) -> None:
        super().__init__("ur10_real_comm_node")
        self.declare_parameter("planning_group", "ur_manipulator")
        self.declare_parameter("ur_type", "ur10")
        self.declare_parameter("description_package", "ur10_description")
        self.declare_parameter("description_file", "ur10_sim.urdf.xacro")
        self.declare_parameter("moveit_config_package", "ur10_moveit_config")
        self.declare_parameter("moveit_config_file", "ur.srdf.xacro")
        self.declare_parameter("planning_tip_link", "tool0")
        self.declare_parameter("planning_pipeline", "ompl")
        self.declare_parameter("planner_id", "RRTConnectkConfigDefault")
        self.declare_parameter("wrist3_joint_name", "wrist_3_joint")
        self.declare_parameter("wrist3_delta_deg", 0.5)
        self.declare_parameter("wrist3_tolerance_deg", 0.2)
        self.declare_parameter("verify_tolerance_ratio", 0.7)
        self.declare_parameter("planning_timeout_sec", 20.0)
        self.declare_parameter("execution_timeout_sec", 30.0)
        self.declare_parameter("joint_state_timeout_sec", 20.0)
        self.declare_parameter("controller_check_timeout_sec", 30.0)
        self.declare_parameter("wait_for_confirm_timeout_sec", 180.0)
        self.declare_parameter("velocity_scale", 0.05)
        self.declare_parameter("acceleration_scale", 0.05)
        self.declare_parameter("initial_joint_controller", "scaled_joint_trajectory_controller")
        self.declare_parameter("controller_manager_name", "controller_manager")
        self.declare_parameter("use_fake_hardware", False)
        self.declare_parameter("launch_rviz", True)
        self.declare_parameter("confirm_execute", True)

        self._group = ReentrantCallbackGroup()
        self._status_pub = self.create_publisher(String, "/ur10_real_comm/status", 10)

        self._plan_client: Optional[object] = None
        self._controller_client: Optional[object] = None
        self._trajectory_client: Optional[ActionClient] = None
        self._confirm_execute_service = self.create_service(
            Trigger, "/ur10_real_comm/confirm_execute", self._confirm_execute_callback
        )

        self._latest_joint_state: Optional[JointState] = None
        self._latest_joint_state_time = self.get_clock().now()
        self._latest_joint_state_received = threading.Event()
        self._confirm_event = threading.Event()
        self._confirm_event.set()

        self._joint_state_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self._joint_state_cb,
            10,
            callback_group=self._group,
        )

    def _publish_status(self, state: str, reason: str, extra: Optional[Dict[str, object]] = None) -> None:
        data = {
            "state": state,
            "reason": reason,
            "wrist3_delta_deg": self.get_parameter("wrist3_delta_deg").value,
        }
        if extra:
            data.update(extra)
        msg = String()
        msg.data = json.dumps(data)
        self._status_pub.publish(msg)
        self.get_logger().info(f"[{state}] {reason}")

    def _joint_state_cb(self, msg: JointState) -> None:
        self._latest_joint_state = msg
        self._latest_joint_state_time = self.get_clock().now()
        self._latest_joint_state_received.set()

    def _confirm_execute_callback(self, request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        _ = request
        self._confirm_event.set()
        response.success = True
        response.message = "Execution confirmed."
        self._publish_status("CONFIRM", "Remote execution confirmed through service call.")
        return response

    def _wait_for_joint_state(self, timeout_sec: float) -> bool:
        end_time = self.get_clock().now() + rclpy.duration.Duration(seconds=timeout_sec)
        while self._latest_joint_state_received.wait(timeout=0.2) is False:
            if self.get_clock().now() > end_time:
                self._publish_status("FAIL", "Timed out waiting for /joint_states.")
                return False
            rclpy.spin_once(self, timeout_sec=0.1)
        return True

    def _wait_for_service_by_candidates(
        self, type_name: str, candidates: List[str], timeout_sec: float
    ):
        end_time = self.get_clock().now() + rclpy.duration.Duration(seconds=timeout_sec)
        suffix_checks = {
            "moveit_msgs/srv/GetMotionPlan": "plan_kinematic_path",
            "controller_manager_msgs/srv/ListControllers": "list_controllers",
        }
        while self.get_clock().now() < end_time:
            available = self.get_service_names_and_types()
            service_types = {name: types for name, types in available}

            for candidate in candidates:
                if candidate not in service_types:
                    continue
                if type_name in service_types[candidate]:
                    return candidate

            suffix = suffix_checks.get(type_name)
            if suffix:
                for name, types in service_types.items():
                    if not name.endswith(f"/{suffix}"):
                        continue
                    if type_name in types:
                        return name

            for name, types in service_types.items():
                if type_name not in types:
                    continue
                if type_name in types:
                    return name

            rclpy.spin_once(self, timeout_sec=0.1)
        return None

    def _await_service(self, client, timeout_sec: float, service_name: str) -> bool:
        if client.service_is_ready():
            return True
        if not client.wait_for_service(timeout_sec=timeout_sec):
            return False
        if not client.service_is_ready():
            self._publish_status("FAIL", f"{service_name} not ready.")
            return False
        return True

    def _build_plan_request(self, current: JointState) -> GetMotionPlan.Request:
        planning_group = str(self.get_parameter("planning_group").value)
        planner_id = str(self.get_parameter("planner_id").value)
        planning_timeout = float(self.get_parameter("planning_timeout_sec").value)
        velocity_scale = float(self.get_parameter("velocity_scale").value)
        acceleration_scale = float(self.get_parameter("acceleration_scale").value)
        wrist_joint_name = str(self.get_parameter("wrist3_joint_name").value)
        wrist_delta_deg = float(self.get_parameter("wrist3_delta_deg").value)
        wrist_tolerance_deg = float(self.get_parameter("wrist3_tolerance_deg").value)
        planning_pipeline = str(self.get_parameter("planning_pipeline").value)

        current_positions = _to_dict(current)
        if wrist_joint_name not in current_positions:
            raise RuntimeError(f"Joint '{wrist_joint_name}' not found in /joint_states.")
        target_rad = current_positions[wrist_joint_name] + _degrees_to_radians(wrist_delta_deg)
        tolerance_rad = _degrees_to_radians(wrist_tolerance_deg)

        constraint = JointConstraint()
        constraint.joint_name = wrist_joint_name
        constraint.position = target_rad
        constraint.tolerance_above = tolerance_rad
        constraint.tolerance_below = tolerance_rad
        constraint.weight = 1.0

        constraints = Constraints()
        constraints.joint_constraints.append(constraint)

        request = GetMotionPlan.Request()
        request.motion_plan_request.group_name = planning_group
        request.motion_plan_request.num_planning_attempts = 5
        request.motion_plan_request.allowed_planning_time = planning_timeout
        request.motion_plan_request.max_velocity_scaling_factor = velocity_scale
        request.motion_plan_request.max_acceleration_scaling_factor = acceleration_scale
        request.motion_plan_request.planner_id = planner_id
        request.motion_plan_request.pipeline_id = planning_pipeline
        request.motion_plan_request.start_state.joint_state = current
        request.motion_plan_request.goal_constraints.append(constraints)

        return request

    def _check_drivers_and_controllers(self, timeout_sec: float) -> bool:
        controller_manager_name = str(self.get_parameter("controller_manager_name").value).strip("/")
        candidates = [
            "/controller_manager/list_controllers",
            f"/{controller_manager_name}/list_controllers",
        ]
        service_name = self._wait_for_service_by_candidates(
            "controller_manager_msgs/srv/ListControllers", candidates, timeout_sec
        )
        if not service_name:
            self._publish_status("FAIL", "Controller manager service not found.")
            return False
        self._controller_client = self.create_client(ListControllers, service_name)
        if not self._await_service(self._controller_client, timeout_sec, "ListControllers"):
            self._publish_status(
                "FAIL",
                f"Controller manager service not available within timeout: {service_name}",
            )
            return False

        expected_trajectory_controller = str(
            self.get_parameter("initial_joint_controller").value
        )
        required = {"joint_state_broadcaster", expected_trajectory_controller}
        service_timeout = rclpy.duration.Duration(seconds=timeout_sec)
        end = self.get_clock().now() + service_timeout
        found = set()

        while self.get_clock().now() < end:
            future = self._controller_client.call_async(ListControllers.Request())
            rclpy.spin_until_future_complete(self, future)
            if not future.done():
                self._publish_status("WARN", "Controller list request timeout, retrying.")
                rclpy.spin_once(self, timeout_sec=0.2)
                continue
            response = future.result()
            if response is None:
                self._publish_status("WARN", "Controller list request returned empty, retrying.")
                rclpy.spin_once(self, timeout_sec=0.2)
                continue

            for controller in response.controller:
                if controller.name in required:
                    if controller.state == "active":
                        found.add(controller.name)

            if found == required:
                self._publish_status("INFO", "Driver and required controllers active.")
                return True

            rclpy.spin_once(self, timeout_sec=0.2)

        missing = ", ".join(sorted(required - found))
        self._publish_status("FAIL", f"Required controllers not active: {missing}")
        return False

    def _discover_plan_service(self) -> bool:
        candidates = [
            "/plan_kinematic_path",
            "/move_group/plan_kinematic_path",
            "plan_kinematic_path",
            "/move_group/plan_kinematic_path/get_plan",
        ]
        service_name = self._wait_for_service_by_candidates(
            "moveit_msgs/srv/GetMotionPlan", candidates, 30.0
        )
        if not service_name:
            self._publish_status("FAIL", "MoveIt motion planning service not found.")
            return False

        self._plan_client = self.create_client(GetMotionPlan, service_name)
        if not self._await_service(self._plan_client, 10.0, "GetMotionPlan"):
            self._publish_status("FAIL", "GetMotionPlan service not available.")
            return False

        self._publish_status("INFO", f"Using MoveIt planning service: {service_name}")
        return True

    def _plan_motion(self, current: JointState):
        request = self._build_plan_request(current)
        future = self._plan_client.call_async(request)
        planning_timeout = float(self.get_parameter("planning_timeout_sec").value)
        rclpy.spin_until_future_complete(self, future)
        if not future.done():
            raise RuntimeError("Motion planning service call timeout.")
        response = future.result()
        if response is None:
            raise RuntimeError("Motion planning service returned no response.")
        result_code = response.motion_plan_response.error_code.val
        if result_code != 1:
            raise RuntimeError(f"MoveIt planning failed, error_code={result_code}.")
        trajectory = response.motion_plan_response.trajectory.joint_trajectory
        if not trajectory.joint_names:
            raise RuntimeError("Planning result has an empty trajectory.")
        return trajectory, response.motion_plan_response.trajectory.joint_trajectory.points[-1]

    def _wait_for_confirm(self, timeout_sec: float) -> bool:
        if not self.get_parameter("confirm_execute").value:
            return True
        self._confirm_event.clear()
        self._publish_status(
            "WAIT_CONFIRM",
            "Waiting for /ur10_real_comm/confirm_execute service call to proceed.",
        )
        timeout_ns = int(timeout_sec * 1e9)
        end = self.get_clock().now().nanoseconds + timeout_ns
        while self.get_clock().now().nanoseconds < end:
            if self._confirm_event.is_set():
                return True
            rclpy.spin_once(self, timeout_sec=0.2)
        self._publish_status("FAIL", "Confirmation timeout.")
        return False

    def _execute_plan(self, trajectory) -> bool:
        expected_controller = str(self.get_parameter("initial_joint_controller").value)
        action_name = f"/{expected_controller}/follow_joint_trajectory"
        self._trajectory_client = ActionClient(
            self,
            FollowJointTrajectory,
            action_name,
            callback_group=self._group,
        )
        if not self._trajectory_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("FollowJointTrajectory action server not available.")

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = trajectory
        send_future = self._trajectory_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None:
            raise RuntimeError("Action server rejected the trajectory goal.")
        if not goal_handle.accepted:
            raise RuntimeError("Trajectory goal rejected by controller.")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(
            self, result_future, timeout_sec=float(self.get_parameter("execution_timeout_sec").value)
        )
        if not result_future.done():
            raise RuntimeError("Trajectory execution timeout.")

        result = result_future.result().result
        if result.error_code != 0:
            raise RuntimeError(f"Execution error code={result.error_code}, msg={result.error_string}")
        return True

    def _check_execution_delta(self, start_state: JointState, delta_deg: float) -> bool:
        tolerance_ratio = float(self.get_parameter("verify_tolerance_ratio").value)
        wrist_joint_name = str(self.get_parameter("wrist3_joint_name").value)

        start = _to_dict(start_state).get(wrist_joint_name)
        if start is None:
            raise RuntimeError("Could not read wrist_3_joint from start state.")

        expected = _degrees_to_radians(delta_deg)
        required = abs(expected * tolerance_ratio)
        end_time = self.get_clock().now() + rclpy.duration.Duration(seconds=5.0)

        while self.get_clock().now() < end_time:
            if self._latest_joint_state is None:
                rclpy.spin_once(self, timeout_sec=0.2)
                continue
            current = _to_dict(self._latest_joint_state).get(wrist_joint_name)
            if current is not None:
                delta = current - start
                if abs(delta) >= required:
                    self._publish_status(
                        "PASS",
                        "Micro-move verified.",
                        {
                            "planned_delta_deg": delta_deg,
                            "actual_delta_deg": delta * 180.0 / math.pi,
                        },
                    )
                    return True
            rclpy.spin_once(self, timeout_sec=0.2)

        raise RuntimeError(
            "Motion effect was too small. "
            f"Expected at least {required:.6f} rad but did not observe enough wrist movement."
        )

    def run(self) -> bool:
        if not self._wait_for_joint_state(float(self.get_parameter("joint_state_timeout_sec").value)):
            return False
        if not self._check_drivers_and_controllers(
            float(self.get_parameter("controller_check_timeout_sec").value)
        ):
            return False
        if not self._discover_plan_service():
            return False

        if self._latest_joint_state is None:
            self._publish_status("FAIL", "No joint state available after startup.")
            return False
        current_state = self._latest_joint_state
        current_state = JointState(
            header=current_state.header,
            name=list(current_state.name),
            position=list(current_state.position),
            velocity=list(current_state.velocity),
            effort=list(current_state.effort),
        )

        self._publish_status("PLAN", "Requesting MoveIt micro-move plan.")
        try:
            trajectory, goal_point = self._plan_motion(current_state)
        except Exception as exc:
            self._publish_status("FAIL", f"Planning failed: {exc}")
            return False

        self._publish_status(
            "PLAN_OK",
            "Plan found. Verify workspace is clear, then confirm execution service.",
            {
                "planned_delta_deg": float(self.get_parameter("wrist3_delta_deg").value),
                "plan_point_count": len(trajectory.points),
                "goal_point_count": len(trajectory.points),
                "last_goal_positions": [
                    float(v) for v in (goal_point.positions if goal_point.positions else [])
                ],
            },
        )

        if not self._wait_for_confirm(float(self.get_parameter("wait_for_confirm_timeout_sec").value)):
            return False

        wrist_delta_deg = float(self.get_parameter("wrist3_delta_deg").value)
        start_map = _to_dict(current_state)
        start_rad = start_map.get(str(self.get_parameter("wrist3_joint_name").value))
        if start_rad is None:
            self._publish_status("FAIL", "Missing wrist_3_joint in current state.")
            return False

        try:
            self._publish_status("EXECUTE", "Executing planned micro-move.")
            self._execute_plan(trajectory)
        except Exception as exc:
            self._publish_status("FAIL", f"Execution failed: {exc}")
            return False

        try:
            return self._check_execution_delta(current_state, wrist_delta_deg)
        except Exception as exc:
            self._publish_status("FAIL", f"Post-execution check failed: {exc}")
            if start_rad is not None:
                self._publish_status("INFO", "Recent joint state after execution (for debug).")
            return False


def main() -> None:
    rclpy.init()
    node = MotionVerifyNode()
    ok = False
    try:
        ok = node.run()
    except KeyboardInterrupt:
        node._publish_status("FAIL", "Interrupted by user.")
    except Exception as exc:
        node.get_logger().error(f"Unhandled exception: {exc}")
        node._publish_status("FAIL", f"Unhandled exception: {exc}")
        ok = False
    finally:
        node.destroy_node()
        rclpy.shutdown()

    if ok:
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
