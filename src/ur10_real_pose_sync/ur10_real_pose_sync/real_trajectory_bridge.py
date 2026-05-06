#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, List

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node


class RealTrajectoryBridge(Node):
    def __init__(self) -> None:
        super().__init__('real_trajectory_bridge')

        self.declare_parameter('incoming_action_name', '/joint_trajectory_controller/follow_joint_trajectory')
        self.declare_parameter('forward_action_name', '/scaled_joint_trajectory_controller/follow_joint_trajectory')
        self.declare_parameter('source_joint_names', [
            'ur10_shoulder_pan',
            'ur10_shoulder_lift',
            'ur10_elbow',
            'ur10_wrist_1',
            'ur10_wrist_2',
            'ur10_wrist_3',
        ])
        self.declare_parameter('target_joint_names', [
            'shoulder_pan_joint',
            'shoulder_lift_joint',
            'elbow_joint',
            'wrist_1_joint',
            'wrist_2_joint',
            'wrist_3_joint',
        ])

        self._incoming_action_name = str(self.get_parameter('incoming_action_name').value)
        self._forward_action_name = str(self.get_parameter('forward_action_name').value)
        self._source_joint_names = list(self.get_parameter('source_joint_names').value)
        self._target_joint_names = list(self.get_parameter('target_joint_names').value)

        if len(self._source_joint_names) != len(self._target_joint_names):
            raise ValueError('source_joint_names and target_joint_names length mismatch')

        self._source_to_target: Dict[str, str] = dict(zip(self._source_joint_names, self._target_joint_names))

        self._client = ActionClient(self, FollowJointTrajectory, self._forward_action_name)
        self._server_ready_logged = False
        self._server_check_timer = self.create_timer(1.0, self._check_forward_server)
        self._server = ActionServer(
            self,
            FollowJointTrajectory,
            self._incoming_action_name,
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
        )

        self.get_logger().info(
            f'Real trajectory bridge started: {self._incoming_action_name} -> {self._forward_action_name}'
        )

    def _check_forward_server(self) -> None:
        if self._client.server_is_ready():
            if not self._server_ready_logged:
                self._server_ready_logged = True
                self.get_logger().info(
                    f'Forward action server is online: {self._forward_action_name}'
                )
            return
        self._server_ready_logged = False
        self.get_logger().warning(
            f'Forward action server is offline: {self._forward_action_name}. '
            f'Execute will fail until controller is started.',
            throttle_duration_sec=5.0,
        )

    def _goal_callback(self, goal_request: FollowJointTrajectory.Goal) -> GoalResponse:
        if not goal_request.trajectory.joint_names or not goal_request.trajectory.points:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _cancel_callback(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _map_goal(self, goal_in: FollowJointTrajectory.Goal) -> FollowJointTrajectory.Goal:
        mapped = FollowJointTrajectory.Goal()
        mapped.goal_time_tolerance = goal_in.goal_time_tolerance
        mapped.path_tolerance = list(goal_in.path_tolerance)
        mapped.goal_tolerance = list(goal_in.goal_tolerance)
        mapped.trajectory.header = goal_in.trajectory.header

        src_names = list(goal_in.trajectory.joint_names)
        src_idx = {n: i for i, n in enumerate(src_names)}

        for src in self._source_joint_names:
            if src not in src_idx:
                raise ValueError(f'Missing source joint in trajectory: {src}')

        mapped.trajectory.joint_names = [self._source_to_target[n] for n in self._source_joint_names]

        for p in goal_in.trajectory.points:
            out = type(p)()
            out.time_from_start = p.time_from_start
            out.positions = [float(p.positions[src_idx[n]]) for n in self._source_joint_names] if p.positions else []
            out.velocities = [float(p.velocities[src_idx[n]]) for n in self._source_joint_names] if p.velocities else []
            out.accelerations = [float(p.accelerations[src_idx[n]]) for n in self._source_joint_names] if p.accelerations else []
            out.effort = [float(p.effort[src_idx[n]]) for n in self._source_joint_names] if p.effort else []
            mapped.trajectory.points.append(out)

        return mapped

    async def _execute_callback(self, goal_handle):
        result = FollowJointTrajectory.Result()

        if not self._client.wait_for_server(timeout_sec=2.0):
            result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
            result.error_string = f'Forward action not available: {self._forward_action_name}'
            self.get_logger().error(result.error_string)
            goal_handle.abort()
            return result

        try:
            mapped_goal = self._map_goal(goal_handle.request)
        except Exception as exc:
            result.error_code = FollowJointTrajectory.Result.INVALID_JOINTS
            result.error_string = str(exc)
            self.get_logger().error(f'Trajectory mapping failed: {result.error_string}')
            goal_handle.abort()
            return result

        forward_goal_future = self._client.send_goal_async(mapped_goal)
        forward_goal_handle = await forward_goal_future

        if forward_goal_handle is None or not forward_goal_handle.accepted:
            result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
            result.error_string = (
                f'Forward controller rejected goal: {self._forward_action_name}'
            )
            self.get_logger().error(result.error_string)
            goal_handle.abort()
            return result

        forward_result_future = forward_goal_handle.get_result_async()
        forward_result = await forward_result_future

        fr = forward_result.result
        result.error_code = fr.error_code
        result.error_string = fr.error_string

        if fr.error_code == FollowJointTrajectory.Result.SUCCESSFUL:
            self.get_logger().info(
                f'Forward trajectory execution succeeded via {self._forward_action_name}'
            )
            goal_handle.succeed()
        else:
            self.get_logger().error(
                f'Forward trajectory execution failed via {self._forward_action_name}: '
                f'code={fr.error_code}, error={fr.error_string}'
            )
            goal_handle.abort()

        return result


def main() -> None:
    rclpy.init()
    node = RealTrajectoryBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
