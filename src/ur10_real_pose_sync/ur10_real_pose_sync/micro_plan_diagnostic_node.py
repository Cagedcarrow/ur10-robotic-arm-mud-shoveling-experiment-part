#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    MotionPlanRequest,
    MoveItErrorCodes,
    OrientationConstraint,
    PositionConstraint,
    WorkspaceParameters,
)
from moveit_msgs.srv import GetPositionIK, GetStateValidity
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
import tf2_ros


class MicroPlanDiagnostic(Node):
    def __init__(self) -> None:
        super().__init__('micro_plan_diagnostic_node')

        self.declare_parameter('group_name', 'assembly_manipulator')
        self.declare_parameter('target_link', 'sensor_shovel_tcp')
        self.declare_parameter('base_frame', 'base_jizuo')
        self.declare_parameter('joint_state_topic', '/joint_states')
        self.declare_parameter('dx', 0.005)
        self.declare_parameter('dy', 0.0)
        self.declare_parameter('dz', 0.0)

        self.group_name = str(self.get_parameter('group_name').value)
        self.target_link = str(self.get_parameter('target_link').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.joint_state_topic = str(self.get_parameter('joint_state_topic').value)
        self.dx = float(self.get_parameter('dx').value)
        self.dy = float(self.get_parameter('dy').value)
        self.dz = float(self.get_parameter('dz').value)

        self.latest_state: Optional[JointState] = None
        self.create_subscription(JointState, self.joint_state_topic, self._on_joint_state, 20)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.move_action = ActionClient(self, MoveGroup, '/move_action')
        self.ik_client = self.create_client(GetPositionIK, '/compute_ik')
        self.validity_client = self.create_client(GetStateValidity, '/check_state_validity')

        self.timer = self.create_timer(0.5, self._try_run_once)
        self.ran = False

    def _on_joint_state(self, msg: JointState) -> None:
        self.latest_state = msg

    def _build_goal_constraints(self, goal_pose: PoseStamped) -> Constraints:
        pc = PositionConstraint()
        pc.header = goal_pose.header
        pc.link_name = self.target_link
        box = SolidPrimitive()
        box.type = SolidPrimitive.SPHERE
        box.dimensions = [0.002]
        pc.constraint_region.primitives = [box]
        pc.constraint_region.primitive_poses = [goal_pose.pose]
        pc.weight = 1.0

        oc = OrientationConstraint()
        oc.header = goal_pose.header
        oc.link_name = self.target_link
        oc.orientation = goal_pose.pose.orientation
        oc.absolute_x_axis_tolerance = 0.05
        oc.absolute_y_axis_tolerance = 0.05
        oc.absolute_z_axis_tolerance = 0.05
        oc.weight = 1.0

        c = Constraints()
        c.position_constraints = [pc]
        c.orientation_constraints = [oc]
        return c

    def _try_run_once(self) -> None:
        if self.ran:
            return
        if self.latest_state is None:
            self.get_logger().info('Waiting /joint_states...')
            return
        if not self.move_action.wait_for_server(timeout_sec=0.2):
            self.get_logger().info('Waiting /move_action...')
            return
        if not self.ik_client.wait_for_service(timeout_sec=0.2):
            self.get_logger().info('Waiting /compute_ik...')
            return
        if not self.validity_client.wait_for_service(timeout_sec=0.2):
            self.get_logger().info('Waiting /check_state_validity...')
            return

        try:
            tf = self.tf_buffer.lookup_transform(self.base_frame, self.target_link, rclpy.time.Time())
        except Exception as exc:
            self.get_logger().error(f'TF lookup failed: {exc}')
            return

        goal_pose = PoseStamped()
        goal_pose.header.frame_id = self.base_frame
        goal_pose.header.stamp = self.get_clock().now().to_msg()
        goal_pose.pose.position.x = tf.transform.translation.x + self.dx
        goal_pose.pose.position.y = tf.transform.translation.y + self.dy
        goal_pose.pose.position.z = tf.transform.translation.z + self.dz
        goal_pose.pose.orientation = tf.transform.rotation

        constraints = self._build_goal_constraints(goal_pose)

        req = MotionPlanRequest()
        req.group_name = self.group_name
        req.num_planning_attempts = 20
        req.allowed_planning_time = 10.0
        req.max_velocity_scaling_factor = 0.2
        req.max_acceleration_scaling_factor = 0.2
        req.goal_constraints = [constraints]
        req.start_state.joint_state = self.latest_state
        req.workspace_parameters = WorkspaceParameters()
        req.workspace_parameters.header.frame_id = self.base_frame
        req.workspace_parameters.min_corner.x = -5.0
        req.workspace_parameters.min_corner.y = -5.0
        req.workspace_parameters.min_corner.z = -5.0
        req.workspace_parameters.max_corner.x = 5.0
        req.workspace_parameters.max_corner.y = 5.0
        req.workspace_parameters.max_corner.z = 5.0

        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options.plan_only = True

        self.ran = True
        future = self.move_action.send_goal_async(goal)
        future.add_done_callback(self._on_move_goal_response)

    def _on_move_goal_response(self, future) -> None:
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error('MoveGroup action goal rejected')
            self._shutdown()
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_move_result)

    def _decode_error(self, code: int) -> str:
        mapping: Dict[int, str] = {
            MoveItErrorCodes.SUCCESS: 'SUCCESS',
            MoveItErrorCodes.PLANNING_FAILED: 'PLANNING_FAILED',
            MoveItErrorCodes.INVALID_MOTION_PLAN: 'INVALID_MOTION_PLAN',
            MoveItErrorCodes.NO_IK_SOLUTION: 'NO_IK_SOLUTION',
            MoveItErrorCodes.GOAL_IN_COLLISION: 'GOAL_IN_COLLISION',
            MoveItErrorCodes.GOAL_CONSTRAINTS_VIOLATED: 'GOAL_CONSTRAINTS_VIOLATED',
            MoveItErrorCodes.START_STATE_IN_COLLISION: 'START_STATE_IN_COLLISION',
            MoveItErrorCodes.START_STATE_VIOLATES_PATH_CONSTRAINTS: 'START_STATE_VIOLATES_PATH_CONSTRAINTS',
        }
        return mapping.get(code, f'UNKNOWN({code})')

    def _on_move_result(self, future) -> None:
        res = future.result().result
        code = int(res.error_code.val)
        code_str = self._decode_error(code)
        self.get_logger().info(f'Micro plan diagnostic result: {code_str}')

        if code != MoveItErrorCodes.SUCCESS:
            self._run_secondary_diagnostics()
        self._shutdown()

    def _run_secondary_diagnostics(self) -> None:
        if self.latest_state is None:
            return

        ik_req = GetPositionIK.Request()
        ik_req.ik_request.group_name = self.group_name
        ik_req.ik_request.ik_link_name = self.target_link
        ik_req.ik_request.robot_state.joint_state = self.latest_state

        try:
            tf = self.tf_buffer.lookup_transform(self.base_frame, self.target_link, rclpy.time.Time())
        except Exception:
            return

        ik_req.ik_request.pose_stamped.header.frame_id = self.base_frame
        ik_req.ik_request.pose_stamped.pose.position.x = tf.transform.translation.x + self.dx
        ik_req.ik_request.pose_stamped.pose.position.y = tf.transform.translation.y + self.dy
        ik_req.ik_request.pose_stamped.pose.position.z = tf.transform.translation.z + self.dz
        ik_req.ik_request.pose_stamped.pose.orientation = tf.transform.rotation

        ik_resp = self.ik_client.call(ik_req)
        ik_code = int(ik_resp.error_code.val)
        self.get_logger().info(f'IK diagnostic: {self._decode_error(ik_code)}')

        if ik_code == MoveItErrorCodes.SUCCESS:
            val_req = GetStateValidity.Request()
            val_req.group_name = self.group_name
            val_req.robot_state = ik_resp.solution
            val_resp = self.validity_client.call(val_req)
            self.get_logger().info(f'Collision validity diagnostic: valid={val_resp.valid}')

    def _shutdown(self) -> None:
        self.timer.cancel()
        self.get_logger().info('Micro plan diagnostic finished.')
        self.create_timer(0.2, lambda: rclpy.shutdown())


def main() -> None:
    rclpy.init()
    node = MicroPlanDiagnostic()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
