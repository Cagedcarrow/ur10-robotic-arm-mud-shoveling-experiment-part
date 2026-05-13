from __future__ import annotations

from typing import List

import numpy as np


def _rot_x(t: float) -> np.ndarray:
    c, s = np.cos(t), np.sin(t)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rot_y(t: float) -> np.ndarray:
    c, s = np.cos(t), np.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rot_z(t: float) -> np.ndarray:
    c, s = np.cos(t), np.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _homogeneous(R: np.ndarray, p: List[float]) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p
    return T


class UR10Kinematics:
    """UR10 kinematic chain using URDF-origin transforms.

    For each revolute joint i:
        T_i = Trans(xyz_i) * Rot(rpy_i) * Rot(axis_i, q_i)
    """

    def __init__(self) -> None:
        data = [
            ([0, 0, 0.1273],      [0, 0, 0],        _rot_z, np.array([0, 0, 1])),
            ([0, 0.220941, 0],    [0, np.pi/2, 0],  _rot_y, np.array([0, 1, 0])),
            ([-0.0000039, -0.1719, 0.612], [0, 0, 0], _rot_y, np.array([0, 1, 0])),
            ([0, 0, 0.5723],      [0, np.pi/2, 0],  _rot_y, np.array([0, 1, 0])),
            ([0, 0.1149, 0],      [0, 0, 0],        _rot_z, np.array([0, 0, 1])),
            ([0, 0, 0.1157],      [0, 0, 0],        _rot_y, np.array([0, 1, 0])),
        ]
        self._joints = []
        for xyz, rpy, rot_fn, a_local in data:
            R_rpy = (_rot_z(rpy[2]) @ _rot_y(rpy[1]) @ _rot_x(rpy[0])).copy()
            a_parent = R_rpy @ a_local
            self._joints.append((xyz, rpy, rot_fn, a_local, R_rpy, a_parent))
        self.n = 6

        # FT300 mounting: ur10-sensor_shovel (fixed joint)
        # From assembly_xacro: origin xyz="0 0.09 0" rpy="-1.5708 0 0"
        self._ft_xyz = [0, 0.09, 0]
        self._ft_rpy = [-np.pi/2, 0, 0]

        # TCP offset: sensor_shovel → sensor_shovel_tcp (the UR tool point)
        # From assembly_xacro: origin rpy="-1.5708 1.5708 -0.61087"
        self._tcp_rpy = [-np.pi/2, np.pi/2, -0.61087]

    def _joint_mat(self, i: int, q: float) -> np.ndarray:
        _, _, rot_fn, _, R_rpy, _ = self._joints[i]
        return _homogeneous(R_rpy @ rot_fn(q), self._joints[i][0])

    def _ft_mat(self) -> np.ndarray:
        rpy = self._ft_rpy
        R = _rot_z(rpy[2]) @ _rot_y(rpy[1]) @ _rot_x(rpy[0])
        return _homogeneous(R, self._ft_xyz)

    def forward_kinematics(self, q: List[float]) -> np.ndarray:
        """Return 4x4 TCP transform in base frame."""
        T = np.eye(4)
        for i in range(self.n):
            T = T @ self._joint_mat(i, q[i])
        return T @ self._ft_mat()

    def compute_jacobian(self, q: List[float]) -> np.ndarray:
        """Geometric Jacobian (6x6) at TCP in base frame."""
        frames = [np.eye(4)]
        for i in range(self.n):
            frames.append(frames[-1] @ self._joint_mat(i, q[i]))

        T_tcp = frames[-1] @ self._ft_mat()
        p_tcp = T_tcp[:3, 3]

        J = np.zeros((6, self.n))
        for i in range(self.n):
            R_i = frames[i][:3, :3]
            xyz_i = self._joints[i][0]
            p_i = R_i @ np.array(xyz_i, dtype=float) + frames[i][:3, 3]
            _, _, _, _, _, a_parent = self._joints[i]
            a_base = R_i @ a_parent

            J[:3, i] = np.cross(a_base, p_tcp - p_i)
            J[3:, i] = a_base

        return J

    def compute_ft_joint_torques(
        self, q: List[float], force: List[float], torque: List[float],
    ) -> np.ndarray:
        """tau_ft = J(q)^T * Adj_{tcp->base} * wrench_tcp"""
        J_base = self.compute_jacobian(q)
        R = self.forward_kinematics(q)[:3, :3]

        F = R @ np.array(force, dtype=float)
        M = R @ np.array(torque, dtype=float)

        return J_base.T @ np.concatenate([F, M])

    def get_tcp_to_sensor_rotation(self) -> np.ndarray:
        """Return 3x3 rotation from TCP (sensor_shovel_tcp) to FT300 sensor (sensor_shovel).

        The UR reports TCP pose at sensor_shovel_tcp. FT300 measures forces in
        the sensor_shovel frame. This rotation converts between them:
            F_sensor_frame = R_tcp_to_sensor @ F_tcp_frame
        """
        rpy = self._tcp_rpy
        R_sensor_to_tcp = _rot_z(rpy[2]) @ _rot_y(rpy[1]) @ _rot_x(rpy[0])
        return R_sensor_to_tcp.T

    def set_sensor_rpy(self, rpy: List[float]) -> None:
        """Update FT300 sensor mounting RPY offset relative to wrist_3."""
        self._ft_rpy = list(rpy)

    def set_tcp_rpy(self, rpy: List[float]) -> None:
        """Update TCP mounting RPY offset (sensor_shovel → sensor_shovel_tcp)."""
        self._tcp_rpy = list(rpy)
