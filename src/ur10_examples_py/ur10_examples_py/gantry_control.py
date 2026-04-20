import os
import sys
from typing import Sequence

import rclpy
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from ur10_examples_py.env_bootstrap import bootstrap_ros_python_environment


bootstrap_ros_python_environment()


def declare_if_missing(node: Node, name: str, default_value):
    if not node.has_parameter(name):
        node.declare_parameter(name, default_value)


class GantryControlClient(Node):
    def __init__(self):
        super().__init__(
            "ur10_gantry_control", automatically_declare_parameters_from_overrides=True
        )
        declare_if_missing(self, "x", 0.0)
        declare_if_missing(self, "y", 0.0)
        declare_if_missing(self, "z", -0.6)
        declare_if_missing(self, "duration_sec", 5.0)
        declare_if_missing(
            self,
            "controller_name", "/gantry_trajectory_controller/follow_joint_trajectory"
        )
        declare_if_missing(self, "use_sim_time", True)
        self._client = ActionClient(
            self,
            FollowJointTrajectory,
            self.get_parameter("controller_name").value,
        )

    def send_goal(self, positions: Sequence[float], duration_sec: float) -> int:
        if not self._client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("gantry_trajectory_controller action server is not available.")
            return 1

        trajectory = JointTrajectory()
        trajectory.joint_names = ["gantry_x_joint", "gantry_y_joint", "gantry_z_joint"]
        point = JointTrajectoryPoint()
        point.positions = list(positions)
        seconds = int(duration_sec)
        nanoseconds = int((duration_sec - seconds) * 1e9)
        point.time_from_start = Duration(sec=seconds, nanosec=nanoseconds)
        trajectory.points = [point]

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = trajectory

        send_future = self._client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        if not send_future.done():
            self.get_logger().error("Timed out sending the gantry trajectory goal.")
            return 2

        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("The gantry trajectory goal was rejected.")
            return 3

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=max(duration_sec + 10.0, 20.0))
        if not result_future.done():
            self.get_logger().error("Timed out waiting for the gantry trajectory result.")
            return 4

        result = result_future.result()
        error_code = result.result.error_code if result and result.result else None
        if error_code != FollowJointTrajectory.Result.SUCCESSFUL:
            self.get_logger().error(f"Gantry motion failed with error code: {error_code}")
            return 5

        self.get_logger().info(
            f"Gantry motion succeeded: x={positions[0]:.3f}, y={positions[1]:.3f}, z={positions[2]:.3f}"
        )
        return 0


def main():
    rclpy.init(args=sys.argv)
    node = GantryControlClient()
    exit_code = node.send_goal(
        [
            float(node.get_parameter("x").value),
            float(node.get_parameter("y").value),
            float(node.get_parameter("z").value),
        ],
        float(node.get_parameter("duration_sec").value),
    )
    node.destroy_node()
    rclpy.shutdown()
    os._exit(exit_code)


if __name__ == "__main__":
    main()
