#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import rclpy
from ament_index_python.packages import get_package_share_directory
from moveit_msgs.srv import QueryPlannerInterfaces
from PyQt5 import QtCore, QtWidgets
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from visualization_msgs.msg import MarkerArray

from ur10_trajectory_planner.action import ExecuteShovelTask
from ur10_trajectory_planner.msg import PlanInfo, TargetPoseSeq
from ur10_trajectory_planner.srv import GenerateTrajectory


UR10_HOME = {
    "ur10_shoulder_pan": 0.0,
    "ur10_shoulder_lift": -1.57,
    "ur10_elbow": 1.57,
    "ur10_wrist_1_joint": -1.57,
    "ur10_wrist_2_joint": -1.57,
    "ur10_wrist_3_joint": 0.0,
}

UR10_RANGE = {
    "ur10_shoulder_pan": (-math.pi, math.pi),
    "ur10_shoulder_lift": (-math.pi, math.pi),
    "ur10_elbow": (-math.pi, math.pi),
    "ur10_wrist_1_joint": (-math.pi, math.pi),
    "ur10_wrist_2_joint": (-math.pi, math.pi),
    "ur10_wrist_3_joint": (-math.pi, math.pi),
}

GANTRY_DEFAULT = {
    "initial": {"x": 0.0, "y": 0.0, "z": -0.6},
    "limits": {
        "x": {"min": -1.0, "max": 1.0},
        "y": {"min": -0.8, "max": 0.8},
        "z": {"min": -1.0, "max": 0.0},
    },
}

GANTRY_JOINTS = ["gantry_x_joint", "gantry_y_joint", "gantry_z_joint"]
UR10_JOINTS = [
    "ur10_shoulder_pan",
    "ur10_shoulder_lift",
    "ur10_elbow",
    "ur10_wrist_1_joint",
    "ur10_wrist_2_joint",
    "ur10_wrist_3_joint",
]


def _load_gantry_config() -> dict:
    cfg = GANTRY_DEFAULT
    try:
        pkg = get_package_share_directory("my_robot")
        path = Path(pkg) / "config" / "gantry_config.json"
        if path.is_file():
            with path.open("r", encoding="utf-8") as fp:
                loaded = json.load(fp)
            cfg = loaded
    except Exception:
        pass
    return cfg


def _build_joint_map() -> List[tuple]:
    cfg = _load_gantry_config()
    ix = float(cfg["initial"]["x"])
    iy = float(cfg["initial"]["y"])
    iz = float(cfg["initial"]["z"])

    x_min = float(cfg["limits"]["x"]["min"])
    x_max = float(cfg["limits"]["x"]["max"])
    y_min = float(cfg["limits"]["y"]["min"])
    y_max = float(cfg["limits"]["y"]["max"])
    z_min = float(cfg["limits"]["z"]["min"])
    z_max = float(cfg["limits"]["z"]["max"])

    return [
        ("龙门架 X 轴", "gantry_x_joint", x_min, x_max, ix, "gantry"),
        ("龙门架 Y 轴", "gantry_y_joint", y_min, y_max, iy, "gantry"),
        ("龙门架 Z 轴", "gantry_z_joint", z_min, z_max, iz, "gantry"),
        ("基座关节", "ur10_shoulder_pan", UR10_RANGE["ur10_shoulder_pan"][0], UR10_RANGE["ur10_shoulder_pan"][1], UR10_HOME["ur10_shoulder_pan"], "ur10"),
        ("肩部关节", "ur10_shoulder_lift", UR10_RANGE["ur10_shoulder_lift"][0], UR10_RANGE["ur10_shoulder_lift"][1], UR10_HOME["ur10_shoulder_lift"], "ur10"),
        ("肘部关节", "ur10_elbow", UR10_RANGE["ur10_elbow"][0], UR10_RANGE["ur10_elbow"][1], UR10_HOME["ur10_elbow"], "ur10"),
        ("腕部1关节", "ur10_wrist_1_joint", UR10_RANGE["ur10_wrist_1_joint"][0], UR10_RANGE["ur10_wrist_1_joint"][1], UR10_HOME["ur10_wrist_1_joint"], "ur10"),
        ("腕部2关节", "ur10_wrist_2_joint", UR10_RANGE["ur10_wrist_2_joint"][0], UR10_RANGE["ur10_wrist_2_joint"][1], UR10_HOME["ur10_wrist_2_joint"], "ur10"),
        ("腕部3关节", "ur10_wrist_3_joint", UR10_RANGE["ur10_wrist_3_joint"][0], UR10_RANGE["ur10_wrist_3_joint"][1], UR10_HOME["ur10_wrist_3_joint"], "ur10"),
    ]


JOINT_LABEL_MAP = _build_joint_map()
GANTRY_HOME = {row[1]: float(row[4]) for row in JOINT_LABEL_MAP if row[5] == "gantry"}


class RosBridgeNode(Node):
    def __init__(self, worker: "RosWorker"):
        super().__init__("ur10_unified_gui_bridge")
        self.worker = worker

        self.generate_client = self.create_client(GenerateTrajectory, "/trajectory/generate")
        self.execute_client = ActionClient(self, ExecuteShovelTask, "/execution/execute_shovel_task")
        self.executor_param_client = self.create_client(SetParameters, "/executor_node/set_parameters")
        self.ompl_query_client = self.create_client(QueryPlannerInterfaces, "/query_planner_interface")

        self.arm_pub = self.create_publisher(JointTrajectory, "/joint_trajectory_controller/joint_trajectory", 10)
        self.gantry_pub = self.create_publisher(JointTrajectory, "/gantry_trajectory_controller/joint_trajectory", 10)

        self.create_subscription(JointState, "/joint_states", self._on_joint_states, 10)
        self.create_subscription(PlanInfo, "/planning/status", self._on_plan_status, 10)
        self.create_subscription(String, "/execution/status", self._on_execution_status, 10)
        self.create_subscription(MarkerArray, "/planning/markers", self._on_markers, 10)
        self.create_subscription(TargetPoseSeq, "/trajectory/target_poses", self._on_target_seq, 10)

        self.status_timer = self.create_timer(1.0, self._publish_status_snapshot)

        self.latest_joint_stamp = 0.0
        self.latest_marker_stamp = 0.0
        self.latest_plan_status = "idle"
        self.latest_execution_status = "idle"
        self.latest_target_seq: Optional[TargetPoseSeq] = None
        self.active_goal_handle = None

    def _now_sec(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_joint_states(self, msg: JointState):
        self.latest_joint_stamp = self._now_sec()
        current = {name: pos for name, pos in zip(msg.name, msg.position)}
        self.worker.joints_signal.emit(current)

    def _on_plan_status(self, msg: PlanInfo):
        self.latest_plan_status = f"{msg.algorithm}: {'ok' if msg.success else 'fail'} nodes={msg.num_nodes}"
        self.worker.plan_signal.emit(msg.success, self.latest_plan_status)

    def _on_execution_status(self, msg: String):
        self.latest_execution_status = msg.data
        self.worker.log_signal.emit(f"[execution] {msg.data}")

    def _on_markers(self, _msg: MarkerArray):
        self.latest_marker_stamp = self._now_sec()

    def _on_target_seq(self, msg: TargetPoseSeq):
        self.latest_target_seq = msg

    def _publish_status_snapshot(self):
        now_sec = self._now_sec()
        names = [name for name, _ns in self.get_node_names_and_namespaces()]
        moveit_ok = "move_group" in names
        gazebo_ok = "gazebo" in names or "gzserver" in names
        controller_ok = self.execute_client.server_is_ready()
        joint_ok = (now_sec - self.latest_joint_stamp) < 2.0
        marker_ok = (now_sec - self.latest_marker_stamp) < 3.0
        payload = {
            "gazebo": "OK" if gazebo_ok else "DOWN",
            "moveit": "OK" if moveit_ok else "DOWN",
            "controller": "OK" if controller_ok else "DOWN",
            "joint_states": "OK" if joint_ok else "NO DATA",
            "markers": "OK" if marker_ok else "NO DATA",
            "planning": self.latest_plan_status,
            "execution": self.latest_execution_status,
        }
        self.worker.system_signal.emit(payload)

    def _publish_joint_traj(self, topic: str, joint_names: List[str], values: Dict[str, float], duration_sec: float):
        traj = JointTrajectory()
        traj.header.stamp = self.get_clock().now().to_msg()
        traj.joint_names = joint_names

        pt = JointTrajectoryPoint()
        pt.positions = [float(values[name]) for name in joint_names]
        pt.time_from_start.sec = int(duration_sec)
        pt.time_from_start.nanosec = int((duration_sec - int(duration_sec)) * 1e9)
        traj.points = [pt]

        if topic == "gantry":
            self.gantry_pub.publish(traj)
        else:
            self.arm_pub.publish(traj)

    def publish_gantry_targets(self, joint_values: Dict[str, float], duration_sec: float = 2.0):
        self._publish_joint_traj("gantry", GANTRY_JOINTS, joint_values, duration_sec)
        self.worker.log_signal.emit("[control] 已发送龙门架目标")

    def publish_arm_targets(self, joint_values: Dict[str, float], duration_sec: float = 2.0):
        self._publish_joint_traj("arm", UR10_JOINTS, joint_values, duration_sec)
        self.worker.log_signal.emit("[control] 已发送机械臂目标")

    def request_plan(self, params: Dict[str, float]):
        if not self.generate_client.wait_for_service(timeout_sec=2.0):
            self.worker.plan_signal.emit(False, "/trajectory/generate 不可用")
            return

        req = GenerateTrajectory.Request()
        req.features.header.frame_id = "world"
        req.features.top_point.x = float(params["bucket_center_x"])
        req.features.top_point.y = float(params["bucket_center_y"])
        req.features.top_point.z = float(params["bucket_center_z"]) + float(params["bucket_height"])
        req.features.top_radius = float(params["bucket_radius"])
        req.features.bottom_radius = float(params["bucket_radius"])
        req.features.depth = float(params["bucket_height"])
        req.features.max_radius = float(params["bucket_radius"])
        req.features.dig_direction.x = -1.0
        req.features.dig_direction.y = 0.0
        req.features.dig_direction.z = 0.0

        req.entry_span_factor = 1.0
        req.mid_span_factor = 0.35
        req.exit_span_factor = 1.0
        req.entry_depth_ratio = 0.20
        req.target_deep_depth_ratio = 0.15
        req.max_cut_angle_deg = 30.0
        req.top_outer_offset_ratio = 0.125
        req.start_finish_lift_ratio = 0.25
        req.attack_deg = -12.0
        req.assembly_deg = 0.0
        req.flip_tool_z = False
        req.exec_first_mode = True
        req.force_base_x_dir = True
        req.reverse_fit_z_axis = False
        req.n_pts = int(params.get("n_pts", 90))

        future = self.generate_client.call_async(req)

        def done_cb(f):
            try:
                res = f.result()
                if res is None:
                    self.worker.plan_signal.emit(False, "规划服务返回空")
                    return
                self.latest_target_seq = res.target_pose_seq
                self.worker.plan_signal.emit(res.success, res.message)
            except Exception as exc:
                self.worker.plan_signal.emit(False, f"规划调用失败: {exc}")

        future.add_done_callback(done_cb)

    def query_ompl_planner_ids(self):
        if not self.ompl_query_client.wait_for_service(timeout_sec=1.0):
            self.worker.log_signal.emit("[moveit] /query_planner_interface 不可用（MoveIt 可能未启动）")
            return
        future = self.ompl_query_client.call_async(QueryPlannerInterfaces.Request())

        def done_cb(f):
            try:
                res = f.result()
                if res is None:
                    self.worker.log_signal.emit("[moveit] 未获取到 planner 接口")
                    return
                lines = []
                for iface in res.planner_interfaces:
                    ids = ", ".join(iface.planner_ids)
                    lines.append(f"{iface.pipeline_id}/{iface.name}: {ids}")
                if lines:
                    self.worker.log_signal.emit("[moveit] 已发现 OMPL planner_ids:\n" + "\n".join(lines))
                else:
                    self.worker.log_signal.emit("[moveit] 未返回 planner_ids")
            except Exception as exc:
                self.worker.log_signal.emit(f"[moveit] 查询 planner_ids 失败: {exc}")

        future.add_done_callback(done_cb)

    def _set_executor_mode(self, mode: str):
        if not self.executor_param_client.wait_for_service(timeout_sec=1.5):
            self.worker.log_signal.emit("[execution] executor 参数服务不可用，沿用现有模式")
            return
        req = SetParameters.Request()
        param = Parameter()
        param.name = "execution_mode"
        param.value = ParameterValue(type=ParameterType.PARAMETER_STRING, string_value=mode)
        req.parameters = [param]
        self.executor_param_client.call_async(req)

    def execute_task(self, execution_mode: str):
        self._set_executor_mode(execution_mode)
        if not self.execute_client.wait_for_server(timeout_sec=2.0):
            self.worker.exec_signal.emit(False, "执行 action 不可用")
            return

        goal = ExecuteShovelTask.Goal()
        if self.latest_target_seq is not None and self.latest_target_seq.poses:
            goal.target_pose_seq = self.latest_target_seq
        goal.local_rrt_enabled = False
        goal.local_rrt_max_iter = 0

        send_future = self.execute_client.send_goal_async(goal, feedback_callback=self._on_execute_feedback)

        def goal_cb(f):
            try:
                goal_handle = f.result()
            except Exception as exc:
                self.worker.exec_signal.emit(False, f"执行目标发送失败: {exc}")
                return
            if not goal_handle or not goal_handle.accepted:
                self.worker.exec_signal.emit(False, "执行目标被拒绝")
                return

            self.active_goal_handle = goal_handle
            self.worker.log_signal.emit("[execution] 目标已接受，开始执行")
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(self._on_execute_result)

        send_future.add_done_callback(goal_cb)

    def _on_execute_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        self.worker.progress_signal.emit(int(fb.current_index), int(fb.total_index))

    def _on_execute_result(self, f):
        try:
            wrapped = f.result()
            if wrapped is None or wrapped.result is None:
                self.worker.exec_signal.emit(False, "执行结果为空")
                return
            result = wrapped.result
            self.worker.exec_signal.emit(bool(result.success), result.message)
        except Exception as exc:
            self.worker.exec_signal.emit(False, f"执行结果异常: {exc}")

    def cancel_execute(self):
        if self.active_goal_handle is None:
            self.worker.log_signal.emit("[execution] 当前无可取消目标")
            return
        future = self.active_goal_handle.cancel_goal_async()

        def done_cb(_f):
            self.worker.log_signal.emit("[execution] 已请求停止")

        future.add_done_callback(done_cb)


class RosWorker(QtCore.QObject):
    log_signal = QtCore.pyqtSignal(str)
    system_signal = QtCore.pyqtSignal(dict)
    plan_signal = QtCore.pyqtSignal(bool, str)
    exec_signal = QtCore.pyqtSignal(bool, str)
    progress_signal = QtCore.pyqtSignal(int, int)
    joints_signal = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._node: Optional[RosBridgeNode] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        rclpy.init(args=None)
        self._node = RosBridgeNode(self)
        self._running = True
        self._thread = threading.Thread(target=self._spin_loop, daemon=True)
        self._thread.start()
        self.log_signal.emit("[system] ROS 后台线程已启动")

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        if rclpy.ok():
            rclpy.shutdown()

    def _spin_loop(self):
        while self._running and self._node is not None and rclpy.ok():
            try:
                rclpy.spin_once(self._node, timeout_sec=0.1)
            except Exception as exc:
                self.log_signal.emit(f"[error] ROS spin 异常: {exc}")
                time.sleep(0.2)

    def publish_gantry_targets(self, joint_values: Dict[str, float], duration_sec: float):
        with self._lock:
            if self._node is not None:
                self._node.publish_gantry_targets(joint_values, duration_sec)

    def publish_arm_targets(self, joint_values: Dict[str, float], duration_sec: float):
        with self._lock:
            if self._node is not None:
                self._node.publish_arm_targets(joint_values, duration_sec)

    def request_plan(self, params: Dict[str, float]):
        with self._lock:
            if self._node is not None:
                self._node.request_plan(params)

    def query_ompl_planner_ids(self):
        with self._lock:
            if self._node is not None:
                self._node.query_ompl_planner_ids()

    def execute_task(self, execution_mode: str):
        with self._lock:
            if self._node is not None:
                self._node.execute_task(execution_mode)

    def cancel_task(self):
        with self._lock:
            if self._node is not None:
                self._node.cancel_execute()


@dataclass
class JointRowWidgets:
    name: str
    group: str
    slider: QtWidgets.QSlider
    spin: QtWidgets.QDoubleSpinBox


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, worker: RosWorker):
        super().__init__()
        self.worker = worker
        self.setWindowTitle("UR10 一体化控制系统")
        self.resize(1280, 860)

        self.joint_rows: List[JointRowWidgets] = []
        self.status_labels: Dict[str, QtWidgets.QLabel] = {}
        self.moveit_proc: Optional[subprocess.Popen] = None
        self._user_edit_hold_sec = 1.2
        self._last_user_edit_time: Dict[str, float] = {}
        self._manual_lock_enabled = False
        self._gantry_auto_send_timer = QtCore.QTimer(self)
        self._gantry_auto_send_timer.setSingleShot(True)
        self._gantry_auto_send_timer.setInterval(180)
        self._gantry_auto_send_timer.timeout.connect(self._auto_send_gantry_targets)

        self.worker.log_signal.connect(self.append_log)
        self.worker.system_signal.connect(self.update_system_status)
        self.worker.plan_signal.connect(self.on_plan_result)
        self.worker.exec_signal.connect(self.on_exec_result)
        self.worker.progress_signal.connect(self.on_exec_progress)
        self.worker.joints_signal.connect(self.update_joint_from_state)

        self._build_ui()

    def _build_ui(self):
        tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(tabs)

        tabs.addTab(self._build_joint_tab(), "关节控制")
        tabs.addTab(self._build_plan_tab(), "轨迹规划")
        tabs.addTab(self._build_status_tab(), "系统状态")
        tabs.addTab(self._build_log_tab(), "日志")

    def _build_joint_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("关节"), 0, 0)
        grid.addWidget(QtWidgets.QLabel("滑块"), 0, 1)
        grid.addWidget(QtWidgets.QLabel("数值"), 0, 2)

        for i, (label_cn, name, vmin, vmax, vdef, group) in enumerate(JOINT_LABEL_MAP, start=1):
            label = QtWidgets.QLabel(label_cn)
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(1000)
            spin = QtWidgets.QDoubleSpinBox()
            spin.setDecimals(4)
            spin.setRange(vmin, vmax)
            spin.setSingleStep(0.01)
            spin.setValue(vdef)

            def _spin_to_slider(val, s=slider, lo=vmin, hi=vmax):
                if hi - lo < 1e-9:
                    return
                ratio = (val - lo) / (hi - lo)
                s.blockSignals(True)
                s.setValue(int(max(0, min(1000, round(ratio * 1000)))))
                s.blockSignals(False)
                self._mark_user_edit(name)

            def _slider_to_spin(raw, sp=spin, lo=vmin, hi=vmax):
                ratio = raw / 1000.0
                val = lo + ratio * (hi - lo)
                sp.blockSignals(True)
                sp.setValue(val)
                sp.blockSignals(False)
                self._mark_user_edit(name)

            spin.valueChanged.connect(_spin_to_slider)
            slider.valueChanged.connect(_slider_to_spin)
            _spin_to_slider(vdef)

            grid.addWidget(label, i, 0)
            grid.addWidget(slider, i, 1)
            grid.addWidget(spin, i, 2)
            self.joint_rows.append(JointRowWidgets(name=name, group=group, slider=slider, spin=spin))
            if group == "gantry":
                spin.valueChanged.connect(self._schedule_gantry_send)

        layout.addLayout(grid)

        btn_row = QtWidgets.QHBoxLayout()
        self.duration_spin = QtWidgets.QDoubleSpinBox()
        self.duration_spin.setRange(0.2, 20.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(2.0)
        btn_row.addWidget(QtWidgets.QLabel("执行时长(s)"))
        btn_row.addWidget(self.duration_spin)
        self.manual_lock_checkbox = QtWidgets.QCheckBox("手动模式锁定（禁止状态回写）")
        self.manual_lock_checkbox.setChecked(False)
        self.manual_lock_checkbox.toggled.connect(self.on_manual_lock_toggled)
        btn_row.addWidget(self.manual_lock_checkbox)

        send_gantry_btn = QtWidgets.QPushButton("发送龙门架目标")
        send_arm_btn = QtWidgets.QPushButton("发送机械臂目标")
        home_gantry_btn = QtWidgets.QPushButton("龙门架回初始")
        home_arm_btn = QtWidgets.QPushButton("机械臂回初始")

        send_gantry_btn.clicked.connect(self.send_gantry_targets)
        send_arm_btn.clicked.connect(self.send_arm_targets)
        home_gantry_btn.clicked.connect(self.home_gantry)
        home_arm_btn.clicked.connect(self.home_arm)

        btn_row.addWidget(send_gantry_btn)
        btn_row.addWidget(send_arm_btn)
        btn_row.addWidget(home_gantry_btn)
        btn_row.addWidget(home_arm_btn)
        btn_row.addStretch(1)

        layout.addLayout(btn_row)
        return widget

    def _build_plan_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        form = QtWidgets.QFormLayout()
        self.bucket_cx = QtWidgets.QDoubleSpinBox(); self.bucket_cx.setRange(-3.0, 3.0); self.bucket_cx.setValue(0.8)
        self.bucket_cy = QtWidgets.QDoubleSpinBox(); self.bucket_cy.setRange(-3.0, 3.0); self.bucket_cy.setValue(0.0)
        self.bucket_cz = QtWidgets.QDoubleSpinBox(); self.bucket_cz.setRange(-1.0, 3.0); self.bucket_cz.setValue(0.0)
        self.bucket_r = QtWidgets.QDoubleSpinBox(); self.bucket_r.setRange(0.05, 1.0); self.bucket_r.setValue(0.18)
        self.bucket_h = QtWidgets.QDoubleSpinBox(); self.bucket_h.setRange(0.05, 1.5); self.bucket_h.setValue(0.30)
        self.bucket_t = QtWidgets.QDoubleSpinBox(); self.bucket_t.setRange(0.001, 0.05); self.bucket_t.setValue(0.005)
        self.safe_m = QtWidgets.QDoubleSpinBox(); self.safe_m.setRange(0.001, 0.2); self.safe_m.setValue(0.03)
        self.n_pts = QtWidgets.QSpinBox(); self.n_pts.setRange(20, 500); self.n_pts.setValue(90)

        self.execution_mode = QtWidgets.QComboBox(); self.execution_mode.addItems(["demo", "moveit"])

        form.addRow("桶中心 X", self.bucket_cx)
        form.addRow("桶中心 Y", self.bucket_cy)
        form.addRow("桶中心 Z", self.bucket_cz)
        form.addRow("桶半径", self.bucket_r)
        form.addRow("桶高度", self.bucket_h)
        form.addRow("桶壁厚", self.bucket_t)
        form.addRow("安全裕量", self.safe_m)
        form.addRow("轨迹采样点", self.n_pts)
        form.addRow("自定义规划器", QtWidgets.QLabel("dp_rrt"))
        form.addRow("execution_mode", self.execution_mode)
        layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        moveit_btn = QtWidgets.QPushButton("启动 MoveIt 规划")
        query_ompl_btn = QtWidgets.QPushButton("查询 OMPL 算法列表")
        plan_btn = QtWidgets.QPushButton("开始规划轨迹")
        show_btn = QtWidgets.QPushButton("显示规划结果")
        exec_btn = QtWidgets.QPushButton("执行轨迹")
        stop_btn = QtWidgets.QPushButton("停止执行")

        moveit_btn.clicked.connect(self.start_moveit_stage)
        query_ompl_btn.clicked.connect(self.query_ompl_ids)
        plan_btn.clicked.connect(self.start_plan)
        show_btn.clicked.connect(self.show_result_hint)
        exec_btn.clicked.connect(self.execute_trajectory)
        stop_btn.clicked.connect(self.stop_execution)

        btn_row.addWidget(moveit_btn)
        btn_row.addWidget(query_ompl_btn)
        btn_row.addWidget(plan_btn)
        btn_row.addWidget(show_btn)
        btn_row.addWidget(exec_btn)
        btn_row.addWidget(stop_btn)
        layout.addLayout(btn_row)

        self.plan_status_label = QtWidgets.QLabel("规划状态: idle")
        self.exec_status_label = QtWidgets.QLabel("执行状态: idle")
        self.exec_progress_label = QtWidgets.QLabel("执行进度: 0/0")
        layout.addWidget(self.plan_status_label)
        layout.addWidget(self.exec_status_label)
        layout.addWidget(self.exec_progress_label)

        return widget

    def _build_status_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)

        for key in ["gazebo", "moveit", "controller", "joint_states", "markers", "planning", "execution"]:
            label = QtWidgets.QLabel("UNKNOWN")
            self.status_labels[key] = label
            layout.addRow(key, label)

        return widget

    def _build_log_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        return widget

    def collect_joint_values(self) -> Dict[str, float]:
        return {row.name: float(row.spin.value()) for row in self.joint_rows}

    def _collect_group_values(self, group: str) -> Dict[str, float]:
        return {row.name: float(row.spin.value()) for row in self.joint_rows if row.group == group}

    def _mark_user_edit(self, joint_name: str):
        self._last_user_edit_time[joint_name] = time.monotonic()

    def _is_user_edit_protected(self, joint_name: str) -> bool:
        t = self._last_user_edit_time.get(joint_name)
        if t is None:
            return False
        return (time.monotonic() - t) < self._user_edit_hold_sec

    def on_manual_lock_toggled(self, checked: bool):
        self._manual_lock_enabled = bool(checked)
        if self._manual_lock_enabled:
            self.append_log("[control] 已开启手动模式锁定：忽略 /joint_states 回写")
        else:
            self.append_log("[control] 已关闭手动模式锁定：恢复状态回写")

    def _schedule_gantry_send(self, _val: float):
        self._gantry_auto_send_timer.start()

    def _auto_send_gantry_targets(self):
        values = self._collect_group_values("gantry")
        self.worker.publish_gantry_targets(values, max(0.3, float(self.duration_spin.value())))

    def send_gantry_targets(self):
        values = self._collect_group_values("gantry")
        self.worker.publish_gantry_targets(values, float(self.duration_spin.value()))

    def send_arm_targets(self):
        values = self._collect_group_values("ur10")
        self.worker.publish_arm_targets(values, float(self.duration_spin.value()))

    def home_gantry(self):
        for row in self.joint_rows:
            if row.group == "gantry":
                row.spin.setValue(float(GANTRY_HOME[row.name]))
        self.worker.publish_gantry_targets(GANTRY_HOME, 2.5)

    def home_arm(self):
        for row in self.joint_rows:
            if row.group == "ur10":
                row.spin.setValue(float(UR10_HOME[row.name]))
        self.worker.publish_arm_targets(UR10_HOME, 3.0)

    def _read_proc_log(self, proc: subprocess.Popen):
        if proc.stdout is None:
            return
        for line in proc.stdout:
            self.append_log(f"[moveit-launch] {line.rstrip()}")

    def start_moveit_stage(self):
        if self.moveit_proc is not None and self.moveit_proc.poll() is None:
            self.append_log("[moveit] moveit_only 已在运行")
            return

        cmd = (
            "source /opt/ros/humble/setup.bash && "
            "source /root/ur10_ws/install/setup.bash && "
            "ros2 launch ur10_bringup moveit_only.launch.py start_rviz:=false"
        )
        self.moveit_proc = subprocess.Popen(
            ["bash", "-lc", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
        )
        threading.Thread(target=self._read_proc_log, args=(self.moveit_proc,), daemon=True).start()
        self.append_log("[moveit] 已启动 moveit_only.launch.py")
        QtCore.QTimer.singleShot(5000, self.query_ompl_ids)

    def query_ompl_ids(self):
        self.worker.query_ompl_planner_ids()

    def start_plan(self):
        params = {
            "bucket_center_x": float(self.bucket_cx.value()),
            "bucket_center_y": float(self.bucket_cy.value()),
            "bucket_center_z": float(self.bucket_cz.value()),
            "bucket_radius": float(self.bucket_r.value()),
            "bucket_height": float(self.bucket_h.value()),
            "bucket_wall_thickness": float(self.bucket_t.value()),
            "safe_margin": float(self.safe_m.value()),
            "n_pts": int(self.n_pts.value()),
        }
        self.append_log("[plan] 请求规划 planner_mode=dp_rrt")
        self.worker.request_plan(params)

    def show_result_hint(self):
        self.append_log("[plan] 规划结果请在 RViz2 查看 /planning/path 与 Marker")

    def execute_trajectory(self):
        self.append_log(f"[execution] 请求执行 execution_mode={self.execution_mode.currentText()}")
        self.worker.execute_task(self.execution_mode.currentText())

    def stop_execution(self):
        self.worker.cancel_task()

    def append_log(self, text: str):
        self.log_text.appendPlainText(text)

    def update_system_status(self, data: dict):
        for key, value in data.items():
            if key in self.status_labels:
                self.status_labels[key].setText(str(value))

    def on_plan_result(self, success: bool, message: str):
        self.plan_status_label.setText(f"规划状态: {'成功' if success else '失败'} | {message}")
        self.append_log(f"[plan] {message}")

    def on_exec_result(self, success: bool, message: str):
        self.exec_status_label.setText(f"执行状态: {'成功' if success else '失败'} | {message}")
        self.append_log(f"[execution] {message}")

    def on_exec_progress(self, cur: int, total: int):
        self.exec_progress_label.setText(f"执行进度: {cur}/{total}")

    def update_joint_from_state(self, current: dict):
        if self._manual_lock_enabled:
            return
        for row in self.joint_rows:
            if row.name in current:
                # Do not overwrite user edits while dragging/typing.
                if row.slider.isSliderDown() or row.spin.hasFocus() or self._is_user_edit_protected(row.name):
                    continue
                row.spin.blockSignals(True)
                row.spin.setValue(float(current[row.name]))
                row.spin.blockSignals(False)

    def closeEvent(self, event):  # type: ignore[override]
        if self.moveit_proc is not None and self.moveit_proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.moveit_proc.pid), signal.SIGTERM)
            except Exception:
                pass
        super().closeEvent(event)


class GuiApp:
    def __init__(self):
        self.qt_app = QtWidgets.QApplication(sys.argv)
        self.worker = RosWorker()
        self.window = MainWindow(self.worker)

    def run(self):
        self.worker.start()
        self.window.show()
        rc = self.qt_app.exec_()
        self.worker.stop()
        return rc


def main():
    app = GuiApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
