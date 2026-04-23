#!/usr/bin/env python3
import math
import tkinter as tk
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


@dataclass
class JointDef:
    name: str
    xyz: tuple
    rpy: tuple
    axis: tuple


def rpy_to_rot(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    return rz @ ry @ rx


def axis_angle_to_rot(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    v = 1.0 - c
    return np.array(
        [
            [x * x * v + c, x * y * v - z * s, x * z * v + y * s],
            [y * x * v + z * s, y * y * v + c, y * z * v - x * s],
            [z * x * v - y * s, z * y * v + x * s, z * z * v + c],
        ]
    )


def make_transform(xyz: tuple, rpy: tuple) -> np.ndarray:
    t = np.eye(4)
    t[:3, :3] = rpy_to_rot(*rpy)
    t[:3, 3] = np.array(xyz, dtype=float)
    return t


def rotation_error(current_r: np.ndarray, target_r: np.ndarray) -> np.ndarray:
    # Error rotation that maps current -> target
    r_err = current_r.T @ target_r
    trace = np.clip((np.trace(r_err) - 1.0) * 0.5, -1.0, 1.0)
    angle = math.acos(trace)
    if abs(angle) < 1e-9:
        return np.zeros(3)
    denom = 2.0 * math.sin(angle)
    axis = np.array(
        [
            (r_err[2, 1] - r_err[1, 2]) / denom,
            (r_err[0, 2] - r_err[2, 0]) / denom,
            (r_err[1, 0] - r_err[0, 1]) / denom,
        ]
    )
    return axis * angle


class UR10TcpSlider(Node):
    def __init__(self) -> None:
        super().__init__("shovel_tcp_slider")
        self.pub = self.create_publisher(JointState, "/joint_states", 10)

        self.joints = [
            JointDef("ur10_shoulder_pan", (0.0, 0.0, 0.1273), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            JointDef("ur10_shoulder_lift", (0.0, 0.220941, 0.0), (0.0, 1.57079, 0.0), (0.0, 1.0, 0.0)),
            JointDef("ur10_elbow", (-0.0000039, -0.1719, 0.612), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            JointDef("ur10_wrist_1_joint", (-0.0000036, 0.0, 0.5723), (0.0, 1.5707895, 0.0000027), (0.0, 1.0, 0.0)),
            JointDef("ur10_wrist_2_joint", (0.0000003, 0.1149, 0.0000003), (0.0, 0.0, 0.0), (0.0, 0.0, -1.0)),
            JointDef("ur10_wrist_3_joint", (0.0, -0.0000003, 0.1157), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ]

        self.t_wrist3_to_shovel = make_transform(
            (0.0, 0.105, 0.0),
            (1.5707963, 0.0, -1.5707963),
        )
        self.t_shovel_to_tip = make_transform(
            (-0.047680, 0.477360, 0.003180),
            (0.433015, 1.482013, 0.786385),
        )

        self.q = np.zeros(6)
        fk0 = self.fk(self.q)
        self.ref_pos = fk0[:3, 3].copy()
        self.ref_rot = fk0[:3, :3].copy()
        self.target_pose = np.array([self.ref_pos[0], self.ref_pos[1], self.ref_pos[2], 0.0, 0.0, 0.0], dtype=float)
        self.target_dirty = True

        self.slider_vars: dict[str, tk.DoubleVar] = {}
        self.root = tk.Tk()
        self.root.title("Shovel TCP 6-DoF Slider")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Sliders are LOCAL offsets in shovel_tip frame (not world frame).
        self._add_slider("x", -0.6, 0.6, 0.0, 0.001)
        self._add_slider("y", -0.6, 0.6, 0.0, 0.001)
        self._add_slider("z", -0.6, 0.6, 0.0, 0.001)
        self._add_slider("roll", -180.0, 180.0, 0.0, 0.1)
        self._add_slider("pitch", -180.0, 180.0, 0.0, 0.1)
        self._add_slider("yaw", -180.0, 180.0, 0.0, 0.1)

        set_ref_btn = tk.Button(self.root, text="Set Current Pose As Local Frame", command=self._set_current_as_ref)
        set_ref_btn.pack(fill="x", padx=6, pady=4)
        publish_btn = tk.Button(self.root, text="Solve IK + Publish", command=self._refresh_target)
        publish_btn.pack(fill="x", padx=6, pady=6)

        self.timer = self.create_timer(0.05, self._on_timer)

    def _add_slider(self, name: str, lo: float, hi: float, init: float, res: float) -> None:
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=6, pady=2)
        label = tk.Label(frame, text=name, width=7, anchor="w")
        label.pack(side="left")
        var = tk.DoubleVar(value=init)
        scale = tk.Scale(
            frame,
            variable=var,
            from_=lo,
            to=hi,
            orient="horizontal",
            resolution=res,
            command=lambda _value: self._refresh_target(),
            length=420,
        )
        scale.pack(side="left", fill="x", expand=True)
        self.slider_vars[name] = var

    def _refresh_target(self) -> None:
        dx_local = self.slider_vars["x"].get()
        dy_local = self.slider_vars["y"].get()
        dz_local = self.slider_vars["z"].get()
        droll = math.radians(self.slider_vars["roll"].get())
        dpitch = math.radians(self.slider_vars["pitch"].get())
        dyaw = math.radians(self.slider_vars["yaw"].get())

        r_delta = rpy_to_rot(droll, dpitch, dyaw)
        target_rot = self.ref_rot @ r_delta
        local_delta = np.array([dx_local, dy_local, dz_local], dtype=float)
        target_pos = self.ref_pos + target_rot @ local_delta

        roll, pitch, yaw = self.rot_to_rpy(target_rot)
        self.target_pose = np.array([target_pos[0], target_pos[1], target_pos[2], roll, pitch, yaw], dtype=float)
        self.target_dirty = True

    def _set_current_as_ref(self) -> None:
        tf = self.fk(self.q)
        self.ref_pos = tf[:3, 3].copy()
        self.ref_rot = tf[:3, :3].copy()
        for key in ("x", "y", "z", "roll", "pitch", "yaw"):
            self.slider_vars[key].set(0.0)
        self._refresh_target()
        self.get_logger().info("Updated local frame to current shovel_tip pose.")

    def _on_close(self) -> None:
        self.get_logger().info("TCP slider window closed.")
        self.destroy_node()
        rclpy.shutdown()
        self.root.destroy()

    def fk(self, q: np.ndarray) -> np.ndarray:
        t = np.eye(4)
        for idx, joint in enumerate(self.joints):
            t = t @ make_transform(joint.xyz, joint.rpy)
            t_joint = np.eye(4)
            t_joint[:3, :3] = axis_angle_to_rot(np.array(joint.axis, dtype=float), float(q[idx]))
            t = t @ t_joint
        t = t @ self.t_wrist3_to_shovel @ self.t_shovel_to_tip
        return t

    @staticmethod
    def rot_to_rpy(r: np.ndarray) -> tuple:
        # XYZ fixed-axis extraction
        pitch = math.asin(-np.clip(r[2, 0], -1.0, 1.0))
        if abs(abs(pitch) - math.pi / 2.0) < 1e-6:
            roll = 0.0
            yaw = math.atan2(-r[0, 1], r[1, 1])
        else:
            roll = math.atan2(r[2, 1], r[2, 2])
            yaw = math.atan2(r[1, 0], r[0, 0])
        return roll, pitch, yaw

    def ik(self, target: np.ndarray, q_seed: np.ndarray) -> np.ndarray:
        p_t = target[:3]
        r_t = rpy_to_rot(target[3], target[4], target[5])

        def residual(qv: np.ndarray) -> np.ndarray:
            tf = self.fk(qv)
            p_c = tf[:3, 3]
            r_c = tf[:3, :3]
            pos_err = p_c - p_t
            rot_err = rotation_error(r_c, r_t)
            return np.concatenate([2.0 * pos_err, rot_err])

        res = least_squares(
            residual,
            q_seed,
            bounds=(-2.0 * math.pi, 2.0 * math.pi),
            max_nfev=80,
            ftol=1e-5,
            xtol=1e-5,
            gtol=1e-5,
        )
        if not res.success:
            self.get_logger().warn(f"IK did not fully converge: {res.message}")
        return res.x

    def _publish_joint_state(self) -> None:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = [j.name for j in self.joints]
        msg.position = [float(v) for v in self.q]
        self.pub.publish(msg)

    def _on_timer(self) -> None:
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            return

        if self.target_dirty:
            self.q = self.ik(self.target_pose, self.q)
            self.target_dirty = False

        self._publish_joint_state()


def main() -> None:
    rclpy.init()
    node = UR10TcpSlider()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
