from __future__ import annotations

import os
import sys
from collections import deque
from pathlib import Path

# WSLg 使用 Weston (Wayland 合成器)，直接使用 Wayland 后端可避免
# XWayland 窗口管理器长期运行后无法映射新 X11 窗口的问题。
# 如果 Wayland 不可用则自动回退到 xcb。
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")

# WSLg 的 Wayland socket 路径
_wslg_runtime = "/mnt/wslg/runtime-dir"
if os.path.isdir(_wslg_runtime) and os.path.exists(os.path.join(_wslg_runtime, "wayland-0")):
    os.environ.setdefault("XDG_RUNTIME_DIR", _wslg_runtime)

import pyqtgraph as pg
import rclpy
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from ..core.config import MeasurementConfig
    from ..core.data_recorder import DataRecorder
    from ..core.robot_data_listener import RobotDataListener
except ImportError:
    package_root = Path(__file__).resolve().parents[2]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from ur10_dynamics_measurement.core.config import MeasurementConfig
    from ur10_dynamics_measurement.core.data_recorder import DataRecorder
    from ur10_dynamics_measurement.core.robot_data_listener import RobotDataListener


class MainWindow(QMainWindow):
    def __init__(self, ros_node: RobotDataListener, config: MeasurementConfig) -> None:
        super().__init__()
        self.setWindowTitle("UR10 动力学测量 GUI")
        self.resize(1200, 800)

        self.ros_node = ros_node
        self.cfg = config
        self.recorder = DataRecorder(config)

        # Rolling plot buffers
        self.plot_window = config.plot_window
        self.plot_buffers: dict = {}
        self.curves: dict = {}
        self._init_buffers()

        self._build_ui()

        # ROS spin timer (50 Hz)
        self.ros_timer = QTimer(self)
        self.ros_timer.timeout.connect(self._spin_ros)
        self.ros_timer.start(config.ros_spin_interval_ms)

        # Plot refresh timer (20 Hz)
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self._refresh_plots)
        self.plot_timer.start(config.plot_refresh_interval_ms)

        # Status update timer (4 Hz)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_status)
        self.status_timer.start(250)

        # Latest data snapshot for plot/record
        self._latest_data = None

    def _init_buffers(self) -> None:
        names = (
            [f"q_{i}" for i in range(6)]
            + [f"dq_{i}" for i in range(6)]
            + [f"I_{i}" for i in range(6)]
            + [f"tau_est_{i}" for i in range(6)]
            + ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
            + [f"tau_ft_{i}" for i in range(6)]
        )
        for name in names:
            self.plot_buffers[name] = deque(maxlen=self.plot_window)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Connection Config ---
        cfg_box = QGroupBox("ROS2 连接配置")
        cfg_grid = QGridLayout(cfg_box)

        cfg_grid.addWidget(QLabel("Joint States Topic"), 0, 0)
        self.topic_joint = QLineEdit(self.cfg.topic_joint_states)
        cfg_grid.addWidget(self.topic_joint, 0, 1)

        cfg_grid.addWidget(QLabel("FT Data Topic"), 0, 2)
        self.topic_ft = QLineEdit(self.cfg.topic_ft_data)
        cfg_grid.addWidget(self.topic_ft, 0, 3)

        cfg_grid.addWidget(QLabel("数据保存目录"), 1, 0)
        self.data_root_edit = QLineEdit(str(self.cfg.data_root))
        cfg_grid.addWidget(self.data_root_edit, 1, 1, 1, 3)

        root.addWidget(cfg_box)

        # --- Controls ---
        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("开始记录")
        self.btn_stop = QPushButton("停止记录")
        self.btn_tare = QPushButton("力传感器清零")
        self.btn_stop.setEnabled(False)
        self.btn_tare.setEnabled(False)

        self.status_label = QLabel("状态: 空闲")
        self.sample_label = QLabel("样本数: 0")

        self.btn_start.clicked.connect(self._start_recording)
        self.btn_stop.clicked.connect(self._stop_recording)
        self.btn_tare.clicked.connect(self._tare_ft)

        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.btn_tare)
        ctrl.addStretch()
        ctrl.addWidget(self.status_label)
        ctrl.addWidget(self.sample_label)
        root.addLayout(ctrl)

        # --- Session path display ---
        self.path_label = QLabel("会话目录: -")
        root.addWidget(self.path_label)

        # --- Plots: 3 rows x 2 cols ---
        plot_box = QGroupBox("UR10 + FT300 动力学实时曲线")
        plot_grid = QGridLayout(plot_box)
        root.addWidget(plot_box)

        groups = [
            ("关节角度", [f"q_{i}" for i in range(6)]),
            ("关节速度", [f"dq_{i}" for i in range(6)]),
            ("电机电流", [f"I_{i}" for i in range(6)]),
            ("估算扭矩 (K*I)", [f"tau_est_{i}" for i in range(6)]),
            ("FT300 力/力矩", ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]),
            ("FT映射扭矩 (J^T*F)", [f"tau_ft_{i}" for i in range(6)]),
        ]
        colors = ["#ff4d4f", "#40a9ff", "#73d13d", "#faad14", "#9254de", "#13c2c2"]

        for i, (title, names) in enumerate(groups):
            r, c = divmod(i, 2)
            pw = pg.PlotWidget(title=title)
            pw.showGrid(x=True, y=True, alpha=0.25)
            pw.addLegend()
            self.curves[title] = []
            for j, name in enumerate(names):
                pen = pg.mkPen(colors[j % len(colors)], width=1.6)
                cv = pw.plot([], [], pen=pen, name=name)
                self.curves[title].append((name, cv))
            plot_grid.addWidget(pw, r, c)

        # --- Log console ---
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        root.addWidget(self.log_box)

    def _spin_ros(self) -> None:
        if not rclpy.ok():
            return
        rclpy.spin_once(self.ros_node, timeout_sec=0.0)
        data = self.ros_node.get_latest_data()
        if data.get("_fresh"):
            self._latest_data = data
            # Update plot buffers
            for k in self.plot_buffers:
                if k.startswith("q_") and data.get("q"):
                    idx = int(k.split("_")[1])
                    self.plot_buffers[k].append(data["q"][idx])
                elif k.startswith("dq_") and data.get("dq"):
                    idx = int(k.split("_")[1])
                    self.plot_buffers[k].append(data["dq"][idx])
                elif k.startswith("I_") and data.get("current"):
                    idx = int(k.split("_")[1])
                    self.plot_buffers[k].append(data["current"][idx])
                elif k.startswith("tau_est_") and data.get("tau_estimated"):
                    idx = int(k.split("_")[2])
                    self.plot_buffers[k].append(data["tau_estimated"][idx])
                elif k.startswith("tau_ft_") and data.get("tau_ft"):
                    idx = int(k.split("_")[2])
                    self.plot_buffers[k].append(data["tau_ft"][idx])
                elif k in ("Fx", "Fy", "Fz") and data.get("force"):
                    idx = ["Fx", "Fy", "Fz"].index(k)
                    self.plot_buffers[k].append(data["force"][idx])
                elif k in ("Mx", "My", "Mz") and data.get("torque"):
                    idx = ["Mx", "My", "Mz"].index(k)
                    self.plot_buffers[k].append(data["torque"][idx])

            # Write to CSV if recording
            if self.recorder.is_recording:
                data["ft_tare_applied"] = self.ros_node.is_tare_applied()
                data["label"] = 0
                self.recorder.write_row(data)

    def _refresh_plots(self) -> None:
        for pairs in self.curves.values():
            for name, cv in pairs:
                y = list(self.plot_buffers[name])
                x = list(range(len(y)))
                cv.setData(x, y)

    def _refresh_status(self) -> None:
        stats = self.recorder.get_stats()
        self.sample_label.setText(f"样本数: {stats.get('sample_count', 0)}")
        if stats.get("session_dir"):
            self.path_label.setText(f"会话目录: {stats['session_dir']}")

    def _start_recording(self) -> None:
        """Start a new measurement session."""
        # Update config from UI fields
        self.cfg.topic_joint_states = self.topic_joint.text().strip()
        self.cfg.topic_ft_data = self.topic_ft.text().strip()
        self.cfg.data_root = Path(self.data_root_edit.text().strip())

        try:
            session_dir = self.recorder.start_session(
                tare_offsets=self.ros_node.get_tare_offsets(),
                motor_gains=self.cfg.motor_gains,
            )
        except Exception as exc:
            QMessageBox.critical(self, "启动失败", str(exc))
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_tare.setEnabled(True)
        self.path_label.setText(f"会话目录: {session_dir}")
        self._log(f"[session] started: {session_dir}")

    def _stop_recording(self) -> None:
        self.recorder.stop_session(normal_stop=True)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_tare.setEnabled(False)
        self._log("[session] stopped")

    def _tare_ft(self) -> None:
        self.ros_node.start_tare()
        self._log("[ft300] tare started, collecting samples...")

    def _log(self, msg: str) -> None:
        self.log_box.append(msg)

    def closeEvent(self, event) -> None:
        if self.recorder.is_recording:
            self.recorder.stop_session(normal_stop=False)
        self.ros_timer.stop()
        self.plot_timer.stop()
        self.status_timer.stop()
        super().closeEvent(event)


def main() -> int:
    rclpy.init()

    config = MeasurementConfig()
    ros_node = RobotDataListener(config)

    app = QApplication(sys.argv)
    window = MainWindow(ros_node, config)
    window.show()

    try:
        exit_code = app.exec_()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        window.close()
        ros_node.destroy_node()
        rclpy.shutdown()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
