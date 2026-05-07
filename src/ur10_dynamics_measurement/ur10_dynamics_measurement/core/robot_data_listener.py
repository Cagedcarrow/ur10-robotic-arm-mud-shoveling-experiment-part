from __future__ import annotations

import copy
import threading
from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

from .config import MeasurementConfig
from .dynamics_estimator import DynamicsEstimator


class RobotDataListener(Node):
    """ROS2 node subscribing to UR10 joint states and FT300 wrench data.

    Provides thread-safe access to the latest synchronized data snapshot.
    """

    def __init__(self, config: MeasurementConfig) -> None:
        super().__init__("robot_data_listener")

        self.cfg = config
        self.estimator = DynamicsEstimator(config.motor_gains)

        # Latest raw data storage
        self._lock = threading.Lock()
        self._latest: Dict = {
            "q": [0.0] * 6,
            "dq": [0.0] * 6,
            "current": [0.0] * 6,
            "force": [0.0] * 3,
            "torque": [0.0] * 3,
            "tau_estimated": [0.0] * 6,
            "tau_ft": [0.0] * 6,
            "sec": 0,
            "nanosec": 0,
            "speed_scaling": 1.0,
            "_fresh": False,
        }

        # FT tare state
        self.ft_zero_offset: Dict[str, float] = {
            "Fx": 0.0, "Fy": 0.0, "Fz": 0.0,
            "Mx": 0.0, "My": 0.0, "Mz": 0.0,
        }
        self.ft_raw_buffer: List[List[float]] = []  # for tare accumulation
        self.ft_tare_samples_collected = 0
        self._tare_mode = False
        self._ft_tare_applied = False

        # Subscribers
        self._joint_sub = self.create_subscription(
            JointState, config.topic_joint_states,
            self._on_joint_state, 10,
        )
        self._ft_sub = self.create_subscription(
            WrenchStamped, config.topic_ft_data,
            self._on_ft_data, 10,
        )
        self._speed_sub = self.create_subscription(
            Float64, config.topic_speed_scaling,
            self._on_speed_scaling, 10,
        )

    def _extract_joint_data(self, msg: JointState) -> tuple:
        """Extract q, dq, current for our 6 UR10 joints by name lookup."""
        q_map = {}
        dq_map = {}
        curr_map = {}
        for i, name in enumerate(msg.name):
            if i < len(msg.position):
                q_map[name] = msg.position[i]
            if i < len(msg.velocity):
                dq_map[name] = msg.velocity[i]
            if i < len(msg.effort):
                curr_map[name] = msg.effort[i]

        q_out = [0.0] * 6
        dq_out = [0.0] * 6
        curr_out = [0.0] * 6

        for j, jname in enumerate(self.cfg.joint_names):
            if jname in q_map:
                q_out[j] = q_map[jname]
            elif j < len(msg.position):
                q_out[j] = msg.position[j]
            if jname in dq_map:
                dq_out[j] = dq_map[jname]
            elif j < len(msg.velocity):
                dq_out[j] = msg.velocity[j]
            if jname in curr_map:
                curr_out[j] = curr_map[jname]
            elif j < len(msg.effort):
                curr_out[j] = msg.effort[j]

        return q_out, dq_out, curr_out

    def _on_joint_state(self, msg: JointState) -> None:
        q, dq, current = self._extract_joint_data(msg)
        tau_estimated = self.estimator.estimate_joint_torques(current)

        with self._lock:
            self._latest["q"] = q
            self._latest["dq"] = dq
            self._latest["current"] = current
            self._latest["tau_estimated"] = tau_estimated.tolist()
            self._latest["sec"] = msg.header.stamp.sec
            self._latest["nanosec"] = msg.header.stamp.nanosec

            # Compute tau_ft if sufficient data available
            if self._latest["_fresh"]:
                try:
                    tau_ft = self.estimator.compute_ft_joint_torques(
                        q, self._latest["force"], self._latest["torque"],
                    )
                    self._latest["tau_ft"] = tau_ft.tolist()
                except Exception as exc:
                    self.get_logger().debug(f"Jacobian failed: {exc}")

            self._latest["_fresh"] = True

    def _on_ft_data(self, msg: WrenchStamped) -> None:
        raw_force = [msg.wrench.force.x, msg.wrench.force.y, msg.wrench.force.z]
        raw_torque = [msg.wrench.torque.x, msg.wrench.torque.y, msg.wrench.torque.z]

        # Apply tare offset
        offset_f = [self.ft_zero_offset["Fx"], self.ft_zero_offset["Fy"], self.ft_zero_offset["Fz"]]
        offset_t = [self.ft_zero_offset["Mx"], self.ft_zero_offset["My"], self.ft_zero_offset["Mz"]]

        with self._lock:
            self._latest["force_raw"] = raw_force
            self._latest["torque_raw"] = raw_torque
            self._latest["force"] = [raw_force[i] - offset_f[i] for i in range(3)]
            self._latest["torque"] = [raw_torque[i] - offset_t[i] for i in range(3)]

        # Tare mode: accumulate samples
        if self._tare_mode and self.ft_tare_samples_collected < self.cfg.ft_tare_samples:
            self.ft_raw_buffer.append(raw_force + raw_torque)
            self.ft_tare_samples_collected += 1
            if self.ft_tare_samples_collected >= self.cfg.ft_tare_samples:
                self._finalize_tare()

    def _on_speed_scaling(self, msg: Float64) -> None:
        with self._lock:
            self._latest["speed_scaling"] = msg.data

    def get_latest_data(self) -> Dict:
        """Thread-safe snapshot of latest data."""
        with self._lock:
            data = copy.deepcopy(self._latest)
            self._latest["_fresh"] = False
        return data

    def start_tare(self) -> None:
        """Begin collecting FT samples for tare offset computation."""
        self.ft_raw_buffer = []
        self.ft_tare_samples_collected = 0
        self._tare_mode = True
        self.get_logger().info(
            f"FT tare started: collecting {self.cfg.ft_tare_samples} samples..."
        )

    def _finalize_tare(self) -> None:
        """Compute mean offset from collected raw samples."""
        if not self.ft_raw_buffer:
            return
        arr = self.ft_raw_buffer
        means = [sum(vals) / len(vals) for vals in zip(*arr)]
        self.ft_zero_offset["Fx"] = means[0]
        self.ft_zero_offset["Fy"] = means[1]
        self.ft_zero_offset["Fz"] = means[2]
        self.ft_zero_offset["Mx"] = means[3]
        self.ft_zero_offset["My"] = means[4]
        self.ft_zero_offset["Mz"] = means[5]
        self._ft_tare_applied = True
        self._tare_mode = False
        self.get_logger().info(
            "FT tare applied: "
            + ", ".join(f"{k}={self.ft_zero_offset[k]:.3f}" for k in self.ft_zero_offset)
        )

    def get_tare_offsets(self) -> Dict[str, float]:
        return dict(self.ft_zero_offset)

    def is_tare_applied(self) -> bool:
        return self._ft_tare_applied
