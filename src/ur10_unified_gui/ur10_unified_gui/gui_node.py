#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import Point
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


GANTRY_JOINTS = ["gantry_x_joint", "gantry_y_joint", "gantry_z_joint"]
UR10_JOINTS = [
    "ur10_shoulder_pan",
    "ur10_shoulder_lift",
    "ur10_elbow",
    "ur10_wrist_1_joint",
    "ur10_wrist_2_joint",
    "ur10_wrist_3_joint",
]

JOINT_LABEL_MAP = [
    ("龙门架 X 轴", "gantry_x_joint", -1.2, 1.2, 0.0),
    ("龙门架 Y 轴", "gantry_y_joint", -1.2, 1.2, 0.0),
    ("龙门架 Z 轴", "gantry_z_joint", 0.0, 1.2, 0.40),
    ("基座关节", "ur10_shoulder_pan", -math.pi, math.pi, 0.0),
    ("肩部关节", "ur10_shoulder_lift", -math.pi, math.pi, -1.57),
    ("肘部关节", "ur10_elbow", -math.pi, math.pi, 1.57),
    ("腕部1关节", "ur10_wrist_1_joint", -math.pi, math.pi, -1.57),
    ("腕部2关节", "ur10_wrist_2_joint", -math.pi, math.pi, -1.57),
    ("腕部3关节", "ur10_wrist_3_joint", -math.pi, math.pi, 0.0),
]


class RosBridgeNode(Node):
    def __init__(self, worker: "RosWorker"):
        super().__init__("ur10_unified_gui_bridge")
        self.worker = worker

        self.generate_client = self.create_client(GenerateTrajectory, "/trajectory/generate")
        self.execute_client = ActionClient(self, ExecuteShovelTask, "/execution/execute_shovel_task")
        self.executor_param_client = self.create_client(SetParameters, "/executor_node/set_parameters")

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

    def publish_joint_targets(self, joint_values: Dict[str, float], duration_sec: float = 2.0):
        now_msg = self.get_clock().now().to_msg()

        gantry_msg = JointTrajectory()
        gantry_msg.header.stamp = now_msg
        gantry_msg.joint_names = GANTRY_JOINTS
        gantry_pt = JointTrajectoryPoint()
        gantry_pt.positions = [joint_values[name] for name in GANTRY_JOINTS]
        gantry_pt.time_from_start.sec = int(duration_sec)
        gantry_pt.time_from_start.nanosec = int((duration_sec - int(duration_sec)) * 1e9)
        gantry_msg.points = [gantry_pt]

        arm_msg = JointTrajectory()
        arm_msg.header.stamp = now_msg
        arm_msg.joint_names = UR10_JOINTS
        arm_pt = JointTrajectoryPoint()
        arm_pt.positions = [joint_values[name] for name in UR10_JOINTS]
        arm_pt.time_from_start.sec = int(duration_sec)
        arm_pt.time_from_start.nanosec = int((duration_sec - int(duration_sec)) * 1e9)
        arm_msg.points = [arm_pt]

        self.gantry_pub.publish(gantry_msg)
        self.arm_pub.publish(arm_msg)
        self.worker.log_signal.emit("[control] 已发送 3+6 轴目标")

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

    def publish_joint_targets(self, joint_values: Dict[str, float], duration_sec: float):
        with self._lock:
            if self._node is not None:
                self._node.publish_joint_targets(joint_values, duration_sec)

    def request_plan(self, params: Dict[str, float]):
        with self._lock:
            if self._node is not None:
                self._node.request_plan(params)

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

        for i, (label_cn, name, vmin, vmax, vdef) in enumerate(JOINT_LABEL_MAP, start=1):
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

            def _slider_to_spin(raw, sp=spin, lo=vmin, hi=vmax):
                ratio = raw / 1000.0
                val = lo + ratio * (hi - lo)
                sp.blockSignals(True)
                sp.setValue(val)
                sp.blockSignals(False)

            spin.valueChanged.connect(_spin_to_slider)
            slider.valueChanged.connect(_slider_to_spin)
            _spin_to_slider(vdef)

            grid.addWidget(label, i, 0)
            grid.addWidget(slider, i, 1)
            grid.addWidget(spin, i, 2)
            self.joint_rows.append(JointRowWidgets(name=name, slider=slider, spin=spin))

        layout.addLayout(grid)

        btn_row = QtWidgets.QHBoxLayout()
        self.duration_spin = QtWidgets.QDoubleSpinBox()
        self.duration_spin.setRange(0.2, 20.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(2.0)
        btn_row.addWidget(QtWidgets.QLabel("执行时长(s)"))
        btn_row.addWidget(self.duration_spin)

        send_btn = QtWidgets.QPushButton("发送关节目标")
        home_btn = QtWidgets.QPushButton("回零")
        send_btn.clicked.connect(self.send_joint_targets)
        home_btn.clicked.connect(self.go_home)
        btn_row.addWidget(send_btn)
        btn_row.addWidget(home_btn)
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

        self.planner_mode = QtWidgets.QComboBox(); self.planner_mode.addItems(["dp_rrt", "ompl"])
        self.execution_mode = QtWidgets.QComboBox(); self.execution_mode.addItems(["demo", "moveit"])

        form.addRow("桶中心 X", self.bucket_cx)
        form.addRow("桶中心 Y", self.bucket_cy)
        form.addRow("桶中心 Z", self.bucket_cz)
        form.addRow("桶半径", self.bucket_r)
        form.addRow("桶高度", self.bucket_h)
        form.addRow("桶壁厚", self.bucket_t)
        form.addRow("安全裕量", self.safe_m)
        form.addRow("轨迹采样点", self.n_pts)
        form.addRow("planner_mode", self.planner_mode)
        form.addRow("execution_mode", self.execution_mode)
        layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        plan_btn = QtWidgets.QPushButton("开始规划轨迹")
        show_btn = QtWidgets.QPushButton("显示规划结果")
        exec_btn = QtWidgets.QPushButton("执行轨迹")
        stop_btn = QtWidgets.QPushButton("停止执行")
        home_btn = QtWidgets.QPushButton("回初始位姿")

        plan_btn.clicked.connect(self.start_plan)
        show_btn.clicked.connect(self.show_result_hint)
        exec_btn.clicked.connect(self.execute_trajectory)
        stop_btn.clicked.connect(self.stop_execution)
        home_btn.clicked.connect(self.go_home)

        btn_row.addWidget(plan_btn)
        btn_row.addWidget(show_btn)
        btn_row.addWidget(exec_btn)
        btn_row.addWidget(stop_btn)
        btn_row.addWidget(home_btn)
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

    def send_joint_targets(self):
        values = self.collect_joint_values()
        self.worker.publish_joint_targets(values, float(self.duration_spin.value()))

    def go_home(self):
        home = {name: default for _cn, name, _minv, _maxv, default in JOINT_LABEL_MAP}
        for row in self.joint_rows:
            row.spin.setValue(home[row.name])
        self.worker.publish_joint_targets(home, 2.5)

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
        self.append_log(f"[plan] 请求规划 planner_mode={self.planner_mode.currentText()}")
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
        for row in self.joint_rows:
            if row.name in current:
                row.spin.blockSignals(True)
                row.spin.setValue(float(current[row.name]))
                row.spin.blockSignals(False)


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
