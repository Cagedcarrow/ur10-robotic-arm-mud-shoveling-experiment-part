#!/usr/bin/env python3
from __future__ import annotations

import math
import threading
import time
from typing import Dict, List

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from sensor_msgs.msg import JointState


class VirtualTrajectoryController(Node):
    def __init__(self) -> None:
        super().__init__('virtual_trajectory_controller')
        self._cbg = ReentrantCallbackGroup()

        self.declare_parameter('joint_names', [
            'ur10_shoulder_pan',
            'ur10_shoulder_lift',
            'ur10_elbow',
            'ur10_wrist_1',
            'ur10_wrist_2',
            'ur10_wrist_3',
        ])
        self.declare_parameter('initial_positions', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.declare_parameter('joint_state_topic', '/joint_states')
        self.declare_parameter('publish_rate_hz', 125.0)
        self.declare_parameter('passthrough_topic', '/real_joint_states')
        self.declare_parameter('passthrough_mode', 'until_first_goal')

        self._joint_names: List[str] = list(self.get_parameter('joint_names').value)
        self._positions: List[float] = [float(v) for v in self.get_parameter('initial_positions').value]
        self._joint_state_topic = str(self.get_parameter('joint_state_topic').value)
        self._publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self._passthrough_topic = str(self.get_parameter('passthrough_topic').value)
        self._passthrough_mode = str(self.get_parameter('passthrough_mode').value).strip().lower()
        if self._passthrough_mode not in ('always', 'never', 'until_first_goal'):
            self.get_logger().warn(
                f'Unknown passthrough_mode={self._passthrough_mode}, fallback to until_first_goal'
            )
            self._passthrough_mode = 'until_first_goal'

        if len(self._joint_names) != len(self._positions):
            raise ValueError('joint_names and initial_positions length mismatch')

        self._state_lock = threading.Lock()
        self._exec_cancel = False
        self._executing = False
        self._passthrough_disabled_after_goal = False

        self._pub = self.create_publisher(JointState, self._joint_state_topic, 50)
        self._timer = self.create_timer(max(1.0 / self._publish_rate_hz, 0.001), self._publish_state)

        self._sub_real = None
        if self._passthrough_topic:
            self._sub_real = self.create_subscription(JointState, self._passthrough_topic, self._on_passthrough_joint_state, 50)

        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            '/joint_trajectory_controller/follow_joint_trajectory',
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self._cbg,
        )

        self.get_logger().info('Virtual trajectory controller started.')

    def _on_passthrough_joint_state(self, msg: JointState) -> None:
        if self._executing:
            return
        if self._passthrough_mode == 'never':
            return
        if self._passthrough_mode == 'until_first_goal' and self._passthrough_disabled_after_goal:
            return
        idx = {n: i for i, n in enumerate(msg.name)}
        try:
            pos = [float(msg.position[idx[n]]) for n in self._joint_names]
        except Exception:
            return
        with self._state_lock:
            self._positions = pos

    def _publish_state(self) -> None:
        with self._state_lock:
            pos = list(self._positions)
        self._publish_state_positions(pos)

    def _publish_state_positions(self, pos: List[float]) -> None:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self._joint_names)
        msg.position = pos
        self._pub.publish(msg)

    def _goal_callback(self, goal_request: FollowJointTrajectory.Goal) -> GoalResponse:
        if self._executing:
            return GoalResponse.REJECT
        if not goal_request.trajectory.joint_names:
            return GoalResponse.REJECT
        if len(goal_request.trajectory.points) == 0:
            return GoalResponse.REJECT
        if self._passthrough_mode == 'until_first_goal':
            self._passthrough_disabled_after_goal = True
        return GoalResponse.ACCEPT

    def _cancel_callback(self, _goal_handle) -> CancelResponse:
        self._exec_cancel = True
        return CancelResponse.ACCEPT

    def _reorder_positions(self, names: List[str], positions: List[float]) -> List[float]:
        name_to_idx: Dict[str, int] = {n: i for i, n in enumerate(names)}
        reordered: List[float] = []
        for n in self._joint_names:
            if n not in name_to_idx:
                raise ValueError(f'Missing joint in trajectory: {n}')
            reordered.append(float(positions[name_to_idx[n]]))
        return reordered

    async def _execute_callback(self, goal_handle) -> FollowJointTrajectory.Result:
        self._executing = True
        self._exec_cancel = False
        result = FollowJointTrajectory.Result()

        try:
            traj = goal_handle.request.trajectory
            traj_names = list(traj.joint_names)
            points = list(traj.points)

            if not points:
                result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
                result.error_string = 'trajectory has no points'
                goal_handle.abort()
                return result

            for p in points:
                if len(p.positions) != len(traj_names):
                    result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
                    result.error_string = 'point positions size mismatch'
                    goal_handle.abort()
                    return result

            t0 = self.get_clock().now().nanoseconds / 1e9
            start_positions = None
            with self._state_lock:
                start_positions = list(self._positions)

            prev_time = 0.0
            prev_pos = start_positions

            for point in points:
                if self._exec_cancel:
                    goal_handle.canceled()
                    result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
                    result.error_string = 'trajectory canceled'
                    return result

                target_time = float(point.time_from_start.sec) + float(point.time_from_start.nanosec) * 1e-9
                target_pos = self._reorder_positions(traj_names, list(point.positions))

                dt = max(target_time - prev_time, 0.0)
                if dt <= 1e-6:
                    with self._state_lock:
                        self._positions = target_pos
                    self._publish_state_positions(target_pos)
                    prev_time = target_time
                    prev_pos = target_pos
                    continue

                hz = max(self._publish_rate_hz, 10.0)
                steps = max(int(math.ceil(dt * hz)), 1)
                for k in range(1, steps + 1):
                    if self._exec_cancel:
                        goal_handle.canceled()
                        result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
                        result.error_string = 'trajectory canceled'
                        return result
                    alpha = k / steps
                    interp = [prev_pos[i] + (target_pos[i] - prev_pos[i]) * alpha for i in range(len(target_pos))]
                    with self._state_lock:
                        self._positions = interp
                    self._publish_state_positions(interp)
                    now = self.get_clock().now().nanoseconds / 1e9
                    desired = t0 + prev_time + alpha * dt
                    sleep_s = desired - now
                    if sleep_s > 0:
                        time.sleep(min(sleep_s, 0.02))

                prev_time = target_time
                prev_pos = target_pos

            with self._state_lock:
                self._positions = list(prev_pos)
            self._publish_state_positions(list(prev_pos))
            goal_handle.succeed()
            result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
            result.error_string = 'trajectory executed'
            return result

        except Exception as exc:
            self.get_logger().error(f'Execution error: {exc}')
            goal_handle.abort()
            result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
            result.error_string = str(exc)
            return result
        finally:
            self._executing = False


def main() -> None:
    rclpy.init()
    node = VirtualTrajectoryController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
