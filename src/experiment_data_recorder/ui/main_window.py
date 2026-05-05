from __future__ import annotations

from pathlib import Path
from collections import deque

import cv2
import pyqtgraph as pg
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import RecorderConfig
from core.session_manager import SessionManager


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("实验数据一体化记录器")
        self.resize(1100, 760)

        self.manager = SessionManager()
        self.manager.configure_callbacks(status_cb=self._on_status, error_cb=self._on_error)
        self.plot_points = 180
        self.curves = {}
        self.plot_buffers = {}

        self._build_ui()

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._refresh_preview)
        self.preview_timer.start(50)

        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._refresh_runtime_state)
        self.state_timer.start(300)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        cfg_box = QGroupBox("连接与参数")
        cfg_grid = QGridLayout(cfg_box)

        self.ur_ip = QLineEdit("10.160.9.21")
        self.ur_port = QLineEdit("30003")
        self.ft_port = QLineEdit("/dev/ttyUSB0")
        self.ft_baud = QLineEdit("19200")
        self.ft_slave = QLineEdit("9")
        self.rs_width = QLineEdit("640")
        self.rs_height = QLineEdit("480")
        self.rs_fps = QLineEdit("30")

        cfg_grid.addWidget(QLabel("UR IP"), 0, 0)
        cfg_grid.addWidget(self.ur_ip, 0, 1)
        cfg_grid.addWidget(QLabel("UR Port"), 0, 2)
        cfg_grid.addWidget(self.ur_port, 0, 3)

        cfg_grid.addWidget(QLabel("FT Port"), 1, 0)
        cfg_grid.addWidget(self.ft_port, 1, 1)
        cfg_grid.addWidget(QLabel("Baud"), 1, 2)
        cfg_grid.addWidget(self.ft_baud, 1, 3)

        cfg_grid.addWidget(QLabel("Slave"), 2, 0)
        cfg_grid.addWidget(self.ft_slave, 2, 1)
        cfg_grid.addWidget(QLabel("Width x Height"), 2, 2)

        wh = QHBoxLayout()
        wh.addWidget(self.rs_width)
        wh.addWidget(QLabel("x"))
        wh.addWidget(self.rs_height)
        wh_widget = QWidget()
        wh_widget.setLayout(wh)
        cfg_grid.addWidget(wh_widget, 2, 3)

        cfg_grid.addWidget(QLabel("FPS"), 3, 2)
        cfg_grid.addWidget(self.rs_fps, 3, 3)

        root.addWidget(cfg_box)

        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("开始记录")
        self.btn_stop = QPushButton("停止记录")
        self.btn_stop.setEnabled(False)
        self.status_label = QLabel("状态: 空闲")
        self.path_label = QLabel("会话目录: -")

        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)

        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.status_label)
        root.addLayout(ctrl)
        root.addWidget(self.path_label)

        previews = QHBoxLayout()
        self.rgb_label = QLabel("RGB 预览")
        self.depth_label = QLabel("Depth 预览")
        self.rgb_label.setFixedSize(580, 360)
        self.depth_label.setFixedSize(580, 360)
        self.rgb_label.setAlignment(Qt.AlignCenter)
        self.depth_label.setAlignment(Qt.AlignCenter)
        self.rgb_label.setStyleSheet("background-color: black; color: white;")
        self.depth_label.setStyleSheet("background-color: black; color: white;")
        previews.addWidget(self.rgb_label)
        previews.addWidget(self.depth_label)
        root.addLayout(previews)

        # --- 深度着色调节 ---
        depth_box = QGroupBox("深度着色调节 (实时生效)")
        depth_row = QHBoxLayout(depth_box)

        depth_row.addWidget(QLabel("最近距离 (m)"))
        self.depth_min_spin = QDoubleSpinBox()
        self.depth_min_spin.setRange(0.01, 10.0)
        self.depth_min_spin.setSingleStep(0.01)
        self.depth_min_spin.setDecimals(3)
        self.depth_min_spin.setValue(1.25)
        self.depth_min_spin.valueChanged.connect(self._on_depth_param_changed)
        depth_row.addWidget(self.depth_min_spin)

        depth_row.addWidget(QLabel("最远距离 (m)"))
        self.depth_max_spin = QDoubleSpinBox()
        self.depth_max_spin.setRange(0.02, 10.0)
        self.depth_max_spin.setSingleStep(0.01)
        self.depth_max_spin.setDecimals(3)
        self.depth_max_spin.setValue(1.35)
        self.depth_max_spin.valueChanged.connect(self._on_depth_param_changed)
        depth_row.addWidget(self.depth_max_spin)

        depth_row.addWidget(QLabel("色图"))
        self.depth_cmap_combo = QComboBox()
        self.depth_cmap_combo.addItems(["Jet", "Gray(近黑远白)", "Gray(近白远黑)", "Bio", "Cold", "Warm", "Quantized", "Pattern"])
        self.depth_cmap_combo.currentIndexChanged.connect(self._on_depth_param_changed)
        depth_row.addWidget(self.depth_cmap_combo)

        self.depth_histeq_cb = QCheckBox("直方图均衡")
        self.depth_histeq_cb.setChecked(True)
        self.depth_histeq_cb.toggled.connect(self._on_depth_param_changed)
        depth_row.addWidget(self.depth_histeq_cb)

        root.addWidget(depth_box)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        root.addWidget(self.log_box)

        plot_box = QGroupBox("UR10 + FT300 实时曲线")
        plot_grid = QGridLayout(plot_box)
        root.addWidget(plot_box)

        groups = [
            ("UR关节角", [f"Act_q{i}" for i in range(6)]),
            ("UR关节速度", [f"Act_qd{i}" for i in range(6)]),
            ("UR关节电流", [f"Act_I{i}" for i in range(6)]),
            ("FT300力", ["Fx", "Fy", "Fz"]),
            ("FT300力矩", ["Mx", "My", "Mz"]),
            ("TCP位姿", ["Act_X", "Act_Y", "Act_Z", "Act_RX", "Act_RY", "Act_RZ"]),
        ]
        colors = ["#ff4d4f", "#40a9ff", "#73d13d", "#faad14", "#9254de", "#13c2c2"]

        for i, (title, names) in enumerate(groups):
            r, c = divmod(i, 3)
            pw = pg.PlotWidget(title=title)
            pw.showGrid(x=True, y=True, alpha=0.25)
            pw.addLegend()
            self.curves[title] = []
            for j, name in enumerate(names):
                pen = pg.mkPen(colors[j % len(colors)], width=1.6)
                cv = pw.plot([], [], pen=pen, name=name)
                self.curves[title].append((name, cv))
                if name not in self.plot_buffers:
                    self.plot_buffers[name] = deque(maxlen=self.plot_points)
            plot_grid.addWidget(pw, r, c)

    def _build_config(self) -> RecorderConfig:
        return RecorderConfig(
            ur_ip=self.ur_ip.text().strip(),
            ur_port=int(self.ur_port.text().strip()),
            ft_port=self.ft_port.text().strip(),
            ft_baud=int(self.ft_baud.text().strip()),
            ft_slave=int(self.ft_slave.text().strip()),
            rs_width=int(self.rs_width.text().strip()),
            rs_height=int(self.rs_height.text().strip()),
            rs_fps=int(self.rs_fps.text().strip()),
            depth_min=self.depth_min_spin.value(),
            depth_max=self.depth_max_spin.value(),
            depth_color_scheme=self.depth_cmap_combo.currentIndex(),
            depth_histogram_eq=self.depth_histeq_cb.isChecked(),
            data_root=Path(__file__).resolve().parents[1] / "data",
        )

    def _start(self) -> None:
        try:
            cfg = self._build_config()
        except ValueError:
            QMessageBox.warning(self, "参数错误", "请检查端口/波特率/FPS/分辨率是否为数字")
            return

        try:
            session_dir = self.manager.start_session(cfg)
        except Exception as exc:
            QMessageBox.critical(self, "启动失败", str(exc))
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.path_label.setText(f"会话目录: {session_dir}")
        self._append_log(f"[session] started: {session_dir}")
        for dq in self.plot_buffers.values():
            dq.clear()

    def _stop(self) -> None:
        self.manager.stop_session(normal_stop=True)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._append_log("[session] stopped")

    def _on_status(self, msg: str) -> None:
        self.status_label.setText(f"状态: {msg}")
        self._append_log(f"[status] {msg}")

    def _on_error(self, msg: str) -> None:
        self.status_label.setText(f"状态: 错误 - {msg}")
        self._append_log(f"[error] {msg}")

    def _append_log(self, msg: str) -> None:
        self.log_box.append(msg)

    def _refresh_runtime_state(self) -> None:
        stats = self.manager.get_runtime_stats()
        if stats.get("session_dir") and stats["session_dir"] != "-":
            self.path_label.setText(
                f"会话目录: {stats['session_dir']} | 样本数: {stats.get('sample_count', 0)}"
            )

        rs_err = ""
        if self.manager.rs_adapter is not None:
            rs_err = self.manager.rs_adapter.last_error
        if rs_err:
            self._on_error(f"RealSense错误: {rs_err}")
        self._refresh_plots()

    def _refresh_plots(self) -> None:
        adapter = self.manager.urft_adapter
        if adapter is None:
            return

        for k, v in adapter.latest_ur.items():
            if k in self.plot_buffers:
                self.plot_buffers[k].append(v)
        for k, v in adapter.latest_ft.items():
            if k in self.plot_buffers:
                self.plot_buffers[k].append(v)

        for pairs in self.curves.values():
            for name, cv in pairs:
                y = list(self.plot_buffers[name])
                x = list(range(len(y)))
                cv.setData(x, y)

    def _refresh_preview(self) -> None:
        color_bgr, depth_bgr = self.manager.get_preview()
        if color_bgr is not None:
            self.rgb_label.setPixmap(self._to_pixmap(color_bgr))
        if depth_bgr is not None:
            self.depth_label.setPixmap(self._to_pixmap(depth_bgr))

    def _on_depth_param_changed(self) -> None:
        self.manager.update_depth_colorizer(
            min_distance=self.depth_min_spin.value(),
            max_distance=self.depth_max_spin.value(),
            color_scheme=self.depth_cmap_combo.currentIndex(),
            histogram_eq=self.depth_histeq_cb.isChecked(),
        )

    def _to_pixmap(self, bgr_image):
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (580, 360), interpolation=cv2.INTER_AREA)
        h, w, ch = resized.shape
        bytes_per_line = ch * w
        qimage = QImage(resized.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        return QPixmap.fromImage(qimage)

    def closeEvent(self, event) -> None:
        if self.manager.is_recording():
            self.manager.stop_session(normal_stop=False)
        super().closeEvent(event)
