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
    """Build 4x4 homogeneous transform from 3x3 rotation and 3-element position."""
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p
    return T


class UR10Kinematics:
    """UR10 kinematic chain using URDF-origin transforms.

    For each revolute joint i:
        T_i = Trans(xyz_i) * Rot(rpy_i) * Rot(axis_i, q_i)

    The transform is applied as: parent_frame -> Trans*R(rpy) -> axis_rotation -> child_frame
    """

    def __init__(self) -> None:
        # Raw URDF joint data from assembly_real.urdf.xacro
        # Each entry: (xyz, rpy, rot_fn, axis_local, R_rpy)
        #   rot_fn: rotation matrix generator R(q) for the joint type
        #   axis_local: unit rotation axis in the child frame (after origin RPY)
        #   R_rpy: pre-computed rotation from origin rpy
        self._joints = []
        data = [
            ([0, 0, 0.1273],      [0, 0, 0],        _rot_z, np.array([0, 0, 1])),
            ([0, 0.220941, 0],    [0, np.pi/2, 0],  _rot_y, np.array([0, 1, 0])),
            ([-0.0000039, -0.1719, 0.612], [0, 0, 0], _rot_y, np.array([0, 1, 0])),
            ([0, 0, 0.5723],      [0, np.pi/2, 0],  _rot_y, np.array([0, 1, 0])),
            ([0, 0.1149, 0],      [0, 0, 0],        _rot_z, np.array([0, 0, 1])),
            ([0, 0, 0.1157],      [0, 0, 0],        _rot_y, np.array([0, 1, 0])),
        ]
        for xyz, rpy, rot_fn, a_local in data:
            R_rpy = (_rot_z(rpy[2]) @ _rot_y(rpy[1]) @ _rot_x(rpy[0])).copy()
            a_parent = R_rpy @ a_local  # axis in parent frame → used in Jacobian
            self._joints.append((xyz, rpy, rot_fn, a_local, R_rpy, a_parent))
        self.n = 6

        # FT300 mounting: ur10-sensor_shovel (fixed)
        self._ft_xyz = [0, 0.09, 0]
        self._ft_rpy = [-np.pi/2, 0, 0]

    def _joint_mat(self, i: int, q: float) -> np.ndarray:
        """4x4 transform for joint i at angle q."""
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
        """Geometric Jacobian (6×6) at TCP in base frame.

        For each revolute joint i with local axis a_i:
            J[:,i] = [R_i * a_i × (p_tcp − p_i);  R_i * a_i]
        where (R_i, p_i) = rotation + origin of the frame before joint i.
        """
        # Cumulative transforms up to each joint (after joint i → frame i)
        frames = [np.eye(4)]
        for i in range(self.n):
            frames.append(frames[-1] @ self._joint_mat(i, q[i]))

        T_tcp = frames[-1] @ self._ft_mat()
        p_tcp = T_tcp[:3, 3]

        J = np.zeros((6, self.n))
        for i in range(self.n):
            # R_i and p_i are the rotation and origin of the frame BEFORE joint i
            R_i = frames[i][:3, :3]
            # p_i = axis origin in base frame = R_i * xyz_local + t_i
            xyz_i = self._joints[i][0]
            p_i = R_i @ np.array(xyz_i, dtype=float) + frames[i][:3, 3]

            # Axis in base frame: a_base = R_i * a_parent
            # where a_parent = R_rpy * a_local (axis in parent frame, before joint acts)
            _, _, _, _, _, a_parent = self._joints[i]
            a_base = R_i @ a_parent

            J[:3, i] = np.cross(a_base, p_tcp - p_i)
            J[3:, i] = a_base

        return J

    def compute_ft_joint_torques(
        self, q: List[float], force: List[float], torque: List[float],
    ) -> np.ndarray:
        """tau_ft = J(q)^T * Adj_{tcp→base} * wrench_tcp"""
        J_base = self.compute_jacobian(q)
        R = self.forward_kinematics(q)[:3, :3]

        F = R @ np.array(force, dtype=float)
        M = R @ np.array(torque, dtype=float)

        return J_base.T @ np.concatenate([F, M])
