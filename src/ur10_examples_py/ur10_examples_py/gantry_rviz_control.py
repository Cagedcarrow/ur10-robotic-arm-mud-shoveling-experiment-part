import rclpy
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Pose
from interactive_markers.interactive_marker_server import InteractiveMarkerServer
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from visualization_msgs.msg import InteractiveMarker
from visualization_msgs.msg import InteractiveMarkerControl
from visualization_msgs.msg import InteractiveMarkerFeedback
from visualization_msgs.msg import Marker

from ur10_examples_py.env_bootstrap import bootstrap_ros_python_environment


bootstrap_ros_python_environment()


def declare_if_missing(node: Node, name: str, default_value):
    if not node.has_parameter(name):
        node.declare_parameter(name, default_value)


class GantryRvizControl(Node):
    def __init__(self):
        super().__init__(
            "gantry_rviz_control", automatically_declare_parameters_from_overrides=True
        )
        declare_if_missing(self, "gantry_base_x", 0.95)
        declare_if_missing(self, "gantry_base_y", 0.0)
        declare_if_missing(self, "gantry_base_height", 2.2)
        declare_if_missing(self, "gantry_x_min", -1.0)
        declare_if_missing(self, "gantry_x_max", 1.0)
        declare_if_missing(self, "gantry_y_min", -0.8)
        declare_if_missing(self, "gantry_y_max", 0.8)
        declare_if_missing(self, "gantry_z_min", -1.0)
        declare_if_missing(self, "gantry_z_max", 0.0)
        declare_if_missing(self, "marker_scale", 0.35)
        declare_if_missing(self, "goal_duration_sec", 1.5)
        declare_if_missing(
            self, "controller_name", "/gantry_trajectory_controller/follow_joint_trajectory"
        )
        declare_if_missing(self, "use_sim_time", True)

        self._base_x = float(self.get_parameter("gantry_base_x").value)
        self._base_y = float(self.get_parameter("gantry_base_y").value)
        self._base_height = float(self.get_parameter("gantry_base_height").value)
        self._x_min = float(self.get_parameter("gantry_x_min").value)
        self._x_max = float(self.get_parameter("gantry_x_max").value)
        self._y_min = float(self.get_parameter("gantry_y_min").value)
        self._y_max = float(self.get_parameter("gantry_y_max").value)
        self._z_min = float(self.get_parameter("gantry_z_min").value)
        self._z_max = float(self.get_parameter("gantry_z_max").value)
        self._marker_scale = float(self.get_parameter("marker_scale").value)
        self._goal_duration = float(self.get_parameter("goal_duration_sec").value)
        self._current_xyz = [0.0, 0.0, -0.6]
        self._dragging = False

        self._server = InteractiveMarkerServer(self, "gantry_xyz_control")
        self._action_client = ActionClient(
            self,
            FollowJointTrajectory,
            self.get_parameter("controller_name").value,
        )
        self.create_subscription(JointState, "/joint_states", self._joint_state_callback, 10)
        self._insert_marker()
        self.create_timer(0.5, self._refresh_marker_from_state)

    def _joint_state_callback(self, msg: JointState):
        indices = {}
        for joint_name in ("gantry_x_joint", "gantry_y_joint", "gantry_z_joint"):
            if joint_name in msg.name:
                indices[joint_name] = msg.name.index(joint_name)
        if len(indices) != 3:
            return
        self._current_xyz = [
            float(msg.position[indices["gantry_x_joint"]]),
            float(msg.position[indices["gantry_y_joint"]]),
            float(msg.position[indices["gantry_z_joint"]]),
        ]

    def _make_marker_pose(self, x: float, y: float, z: float):
        pose = Pose()
        pose.position.x = self._base_x + x
        pose.position.y = self._base_y + y
        pose.position.z = self._base_height + z
        pose.orientation.w = 1.0
        return pose

    def _marker_to_joint_xyz(self, pose: Pose):
        x = min(max(pose.position.x - self._base_x, self._x_min), self._x_max)
        y = min(max(pose.position.y - self._base_y, self._y_min), self._y_max)
        z = min(max(pose.position.z - self._base_height, self._z_min), self._z_max)
        return [x, y, z]

    def _insert_marker(self):
        int_marker = InteractiveMarker()
        int_marker.header.frame_id = "world"
        int_marker.name = "gantry_xyz_slider"
        int_marker.description = "Drag X/Y/Z to move gantry"
        int_marker.scale = self._marker_scale
        int_marker.pose = self._make_marker_pose(*self._current_xyz)

        center_control = InteractiveMarkerControl()
        center_control.always_visible = True
        center_control.interaction_mode = InteractiveMarkerControl.NONE
        box = Marker()
        box.type = Marker.CUBE
        box.scale.x = 0.14
        box.scale.y = 0.14
        box.scale.z = 0.08
        box.color.r = 0.10
        box.color.g = 0.70
        box.color.b = 0.95
        box.color.a = 0.85
        center_control.markers.append(box)
        int_marker.controls.append(center_control)

        for axis_name, orientation in (
            ("x", (1.0, 1.0, 0.0, 0.0)),
            ("y", (1.0, 0.0, 1.0, 0.0)),
            ("z", (1.0, 0.0, 0.0, 1.0)),
        ):
            control = InteractiveMarkerControl()
            control.name = f"move_{axis_name}"
            control.orientation.w = orientation[0]
            control.orientation.x = orientation[1]
            control.orientation.y = orientation[2]
            control.orientation.z = orientation[3]
            control.interaction_mode = InteractiveMarkerControl.MOVE_AXIS
            int_marker.controls.append(control)

        self._server.insert(int_marker, feedback_callback=self._feedback_callback)
        self._server.applyChanges()

    def _refresh_marker_from_state(self):
        if self._dragging:
            return
        self._server.setPose(
            "gantry_xyz_slider", self._make_marker_pose(*self._current_xyz)
        )
        self._server.applyChanges()

    def _feedback_callback(self, feedback: InteractiveMarkerFeedback):
        if feedback.event_type == InteractiveMarkerFeedback.MOUSE_DOWN:
            self._dragging = True
            return

        if feedback.event_type == InteractiveMarkerFeedback.POSE_UPDATE:
            clamped_pose = self._make_marker_pose(*self._marker_to_joint_xyz(feedback.pose))
            self._server.setPose(feedback.marker_name, clamped_pose)
            self._server.applyChanges()
            return

        if feedback.event_type != InteractiveMarkerFeedback.MOUSE_UP:
            return

        self._dragging = False
        goal_xyz = self._marker_to_joint_xyz(feedback.pose)
        self._server.setPose(feedback.marker_name, self._make_marker_pose(*goal_xyz))
        self._server.applyChanges()
        self._send_gantry_goal(goal_xyz)

    def _send_gantry_goal(self, positions):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warning("gantry_trajectory_controller action server is not available.")
            return

        trajectory = JointTrajectory()
        trajectory.joint_names = ["gantry_x_joint", "gantry_y_joint", "gantry_z_joint"]
        point = JointTrajectoryPoint()
        point.positions = list(positions)
        seconds = int(self._goal_duration)
        nanoseconds = int((self._goal_duration - seconds) * 1e9)
        point.time_from_start = Duration(sec=seconds, nanosec=nanoseconds)
        trajectory.points = [point]

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = trajectory
        self._action_client.send_goal_async(goal)
        self.get_logger().info(
            f"Sent gantry goal from RViz marker: x={positions[0]:.3f}, y={positions[1]:.3f}, z={positions[2]:.3f}"
        )


def main():
    rclpy.init()
    node = GantryRvizControl()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
