from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import cv2
import pyqtgraph as pg
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QImage, QPixmap
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

# --- Import from local package ---
_PKG = Path(__file__).resolve().parents[1]
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from core.config import MudRecorderConfig
from core.session_manager import SessionManager


class MainWindow(QMainWindow):
    """Mud Experiment Recorder — unified data recording GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("泥浆实验数据一体化记录器")
        self.resize(1400, 920)

        self.config = MudRecorderConfig()
        self.manager = SessionManager()
        self.manager.configure_callbacks(
            status_cb=self._on_status, error_cb=self._on_error
        )

        self.plot_buffers: dict[str, deque] = {}
        self.curves: dict[str, list] = {}

        self._build_ui()

        # Timers
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self._refresh_plots)
        self.plot_timer.start(self.config.plot_refresh_ms)

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._refresh_preview)
        self.preview_timer.start(self.config.preview_refresh_ms)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_status)
        self.status_timer.start(self.config.status_refresh_ms)

    # ============================================================
    #  UI Construction
    # ============================================================

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)

        self._build_connection_config(root)
        self._build_control_bar(root)
        self._build_plots(root)
        self._build_weight_and_camera(root)
        self._build_depth_controls(root)
        self._build_log(root)

    def _build_connection_config(self, root: QVBoxLayout) -> None:
        box = QGroupBox("连接配置")
        grid = QGridLayout(box)

        self.ur_ip = QLineEdit(self.config.ur_ip)
        self.ur_port = QLineEdit(str(self.config.ur_port))
        self.ft_port = QLineEdit(self.config.ft_port)
        self.ft_baud = QLineEdit(str(self.config.ft_baud))
        self.ft_slave = QLineEdit(str(self.config.ft_slave))
        self.rs_width = QLineEdit(str(self.config.rs_width))
        self.rs_height = QLineEdit(str(self.config.rs_height))
        self.rs_fps = QLineEdit(str(self.config.rs_fps))

        grid.addWidget(QLabel("UR IP"), 0, 0)
        grid.addWidget(self.ur_ip, 0, 1)
        grid.addWidget(QLabel("Port"), 0, 2)
        grid.addWidget(self.ur_port, 0, 3)

        grid.addWidget(QLabel("FT Port"), 1, 0)
        grid.addWidget(self.ft_port, 1, 1)
        grid.addWidget(QLabel("Baud"), 1, 2)
        grid.addWidget(self.ft_baud, 1, 3)

        grid.addWidget(QLabel("Slave"), 2, 0)
        grid.addWidget(self.ft_slave, 2, 1)
        grid.addWidget(QLabel("RS 分辨率"), 2, 2)
        wh = QHBoxLayout()
        wh.addWidget(self.rs_width)
        wh.addWidget(QLabel("x"))
        wh.addWidget(self.rs_height)
        wh.addWidget(QLabel("FPS"))
        wh.addWidget(self.rs_fps)
        wh_w = QWidget()
        wh_w.setLayout(wh)
        grid.addWidget(wh_w, 2, 3)

        root.addWidget(box)

    def _build_control_bar(self, root: QVBoxLayout) -> None:
        ctrl = QHBoxLayout()

        self.btn_start = QPushButton("开始接收数据")
        self.btn_stop = QPushButton("停止记录")
        self.btn_zero_tare = QPushButton("清零去皮重")
        self.btn_start_csv = QPushButton("开始记录数据")
        self.btn_record_weight = QPushButton("记录重量")

        self.btn_stop.setEnabled(False)
        self.btn_zero_tare.setEnabled(False)
        self.btn_start_csv.setEnabled(False)
        self.btn_record_weight.setEnabled(False)

        self.btn_start.clicked.connect(self._start_receiving)
        self.btn_stop.clicked.connect(self._stop_recording)
        self.btn_zero_tare.clicked.connect(self._zero_and_tare)
        self.btn_start_csv.clicked.connect(self._start_csv_recording)
        self.btn_record_weight.clicked.connect(self._record_weight)

        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_zero_tare)
        ctrl.addWidget(self.btn_start_csv)
        ctrl.addWidget(self.btn_record_weight)
        ctrl.addWidget(self.btn_stop)
        ctrl.addStretch()

        self.status_label = QLabel("状态: 空闲")
        ctrl.addWidget(self.status_label)

        root.addLayout(ctrl)

        self.path_label = QLabel("会话目录: - | 样本数: 0")
        root.addWidget(self.path_label)

    def _build_plots(self, root: QVBoxLayout) -> None:
        box = QGroupBox("UR10 + FT300 动力学实时曲线")
        grid = QGridLayout(box)
        root.addWidget(box)

        groups = [
            # Row 1
            ("关节角度", [f"Act_q{i}" for i in range(6)]),
            ("关节速度", [f"Act_qd{i}" for i in range(6)]),
            ("电机电流", [f"Act_I{i}" for i in range(6)]),
            # Row 2
            ("估算扭矩 K*I", [f"tau_estimated_{i}" for i in range(6)]),
            ("FT300 力", ["Fx", "Fy", "Fz"]),
            ("FT300 力矩", ["Mx", "My", "Mz"]),
            # Row 3
            ("FT映射扭矩 J^T*F", [f"tau_ft_{i}" for i in range(6)]),
            ("TCP 位置", ["Act_X", "Act_Y", "Act_Z"]),
            ("TCP 姿态", ["Act_RX", "Act_RY", "Act_RZ"]),
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
                    self.plot_buffers[name] = deque(maxlen=self.config.plot_window)
            grid.addWidget(pw, r, c)

    def _build_weight_and_camera(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()

        # --- Weight Panel (left, ~1/3 width) ---
        wbox = QGroupBox("铲泥重量 (世界坐标Z轴投影)")
        wlay = QVBoxLayout(wbox)

        self.w_tare_label = QLabel("空铲皮重: -- N")
        self.w_fz_label = QLabel("当前 Fz (世界): -- N")
        self.w_weight_label = QLabel("泥重: -- g")
        font_big = QFont()
        font_big.setPointSize(18)
        font_big.setBold(True)
        self.w_weight_label.setFont(font_big)
        self.w_weight_label.setStyleSheet("color: #40a9ff;")
        self.w_stable_label = QLabel("状态: --")
        self.w_last_label = QLabel("最近记录: --")

        wlay.addWidget(self.w_tare_label)
        wlay.addWidget(self.w_fz_label)
        wlay.addWidget(self.w_weight_label)
        wlay.addWidget(self.w_stable_label)
        wlay.addWidget(self.w_last_label)
        wlay.addStretch()

        row.addWidget(wbox, stretch=1)

        # --- Camera Preview (right, ~2/3 width) ---
        cbox = QGroupBox("RealSense 相机预览")
        clay = QHBoxLayout(cbox)

        self.rgb_label = QLabel("RGB")
        self.depth_label = QLabel("Depth")
        for lbl in (self.rgb_label, self.depth_label):
            lbl.setFixedSize(420, 280)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background-color: black; color: white;")

        clay.addWidget(self.rgb_label)
        clay.addWidget(self.depth_label)

        row.addWidget(cbox, stretch=2)
        root.addLayout(row)

    def _build_depth_controls(self, root: QVBoxLayout) -> None:
        box = QGroupBox("深度着色调节 (实时生效)")
        drow = QHBoxLayout(box)

        drow.addWidget(QLabel("最近 (m)"))
        self.depth_min_spin = QDoubleSpinBox()
        self.depth_min_spin.setRange(0.01, 10.0)
        self.depth_min_spin.setSingleStep(0.01)
        self.depth_min_spin.setDecimals(3)
        self.depth_min_spin.setValue(self.config.depth_min)
        self.depth_min_spin.valueChanged.connect(self._on_depth_changed)
        drow.addWidget(self.depth_min_spin)

        drow.addWidget(QLabel("最远 (m)"))
        self.depth_max_spin = QDoubleSpinBox()
        self.depth_max_spin.setRange(0.02, 10.0)
        self.depth_max_spin.setSingleStep(0.01)
        self.depth_max_spin.setDecimals(3)
        self.depth_max_spin.setValue(self.config.depth_max)
        self.depth_max_spin.valueChanged.connect(self._on_depth_changed)
        drow.addWidget(self.depth_max_spin)

        drow.addWidget(QLabel("色图"))
        self.depth_cmap = QComboBox()
        self.depth_cmap.addItems([
            "Jet", "Gray(近黑远白)", "Gray(近白远黑)",
            "Bio", "Cold", "Warm", "Quantized", "Pattern",
        ])
        self.depth_cmap.currentIndexChanged.connect(self._on_depth_changed)
        drow.addWidget(self.depth_cmap)

        self.depth_histeq = QCheckBox("直方图均衡")
        self.depth_histeq.setChecked(self.config.depth_histogram_eq)
        self.depth_histeq.toggled.connect(self._on_depth_changed)
        drow.addWidget(self.depth_histeq)

        root.addWidget(box)

    def _build_log(self, root: QVBoxLayout) -> None:
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(100)
        root.addWidget(self.log_box)

    # ============================================================
    #  Config extraction
    # ============================================================

    def _build_config(self) -> MudRecorderConfig:
        return MudRecorderConfig(
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
            depth_color_scheme=self.depth_cmap.currentIndex(),
            depth_histogram_eq=self.depth_histeq.isChecked(),
            data_root=Path(__file__).resolve().parents[1] / "data",
            plot_window=self.config.plot_window,
        )

    # ============================================================
    #  Button slots
    # ============================================================

    def _start_receiving(self) -> None:
        """Step 1: Start data reception (UR + FT + Camera), no CSV writing yet."""
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
        self.btn_zero_tare.setEnabled(True)
        self.btn_start_csv.setEnabled(False)
        self.btn_record_weight.setEnabled(False)
        self.path_label.setText(f"会话目录: {session_dir} | 等待清零去皮重")
        self._log(f"[session] 数据接收已启动: {session_dir}")
        for dq in self.plot_buffers.values():
            dq.clear()

    def _stop_recording(self) -> None:
        self.manager.stop_session(normal_stop=True)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_zero_tare.setEnabled(False)
        self.btn_start_csv.setEnabled(False)
        self.btn_record_weight.setEnabled(False)
        self._log("[session] 已停止")

    def _zero_and_tare(self) -> None:
        """Step 2: Zero FT300 sensor + begin shovel tare (no CSV yet)."""
        adapter = self.manager.urft_adapter
        if adapter is None:
            QMessageBox.warning(self, "操作失败", "当前未启动采集。")
            return
        if not adapter.latest_ft_raw:
            QMessageBox.warning(self, "操作失败", "尚未收到FT300数据，请稍后重试。")
            return

        adapter.zero_and_tare()
        self.btn_start_csv.setEnabled(True)
        self.btn_record_weight.setEnabled(True)
        self._log("[zero+tare] FT300清零 + 空铲皮重采集已开始 (80样本)")

    def _start_csv_recording(self) -> None:
        """Step 3: Enable CSV data recording."""
        adapter = self.manager.urft_adapter
        if adapter is None:
            QMessageBox.warning(self, "操作失败", "当前未启动采集。")
            return
        if not adapter.is_tare_in_progress() and adapter.weight_calc.shovel_tare_Fz == 0.0:
            # Tare is not yet done — warn but allow
            resp = QMessageBox.question(
                self, "尚未去皮重",
                "尚未完成清零去皮重，是否直接开始记录数据？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        adapter.enable_csv_writing()
        self.btn_start_csv.setEnabled(False)
        self._log("[csv] 数据记录已开始写入 CSV")

    def _record_weight(self) -> None:
        adapter = self.manager.urft_adapter
        if adapter is None:
            QMessageBox.warning(self, "记录失败", "当前未启动采集。")
            return
        weight = adapter.record_weight()
        ts = adapter.weight_calc.last_recorded_time
        self._log(f"[weight] 泥重已记录: {weight:.1f} g @ {ts}")

    # ============================================================
    #  Callbacks
    # ============================================================

    def _on_status(self, msg: str) -> None:
        self.status_label.setText(f"状态: {msg}")
        self._log(f"[status] {msg}")

    def _on_error(self, msg: str) -> None:
        self.status_label.setText(f"状态: 错误 - {msg}")
        self._log(f"[error] {msg}")

    def _log(self, msg: str) -> None:
        self.log_box.append(msg)

    # ============================================================
    #  Timers
    # ============================================================

    def _refresh_plots(self) -> None:
        adapter = self.manager.urft_adapter
        if adapter is None:
            return

        # UR data
        for k, v in adapter.latest_ur.items():
            if k in self.plot_buffers:
                self.plot_buffers[k].append(v)

        # FT data
        for k, v in adapter.latest_ft.items():
            if k in self.plot_buffers:
                self.plot_buffers[k].append(v)

        # Computed: tau_estimated
        for i in range(6):
            key = f"tau_estimated_{i}"
            if key in self.plot_buffers:
                val = float(adapter.latest_tau_estimated[i])
                self.plot_buffers[key].append(val)

        # Computed: tau_ft
        for i in range(6):
            key = f"tau_ft_{i}"
            if key in self.plot_buffers:
                val = float(adapter.latest_tau_ft[i])
                self.plot_buffers[key].append(val)

        # Update all curves
        for pairs in self.curves.values():
            for name, cv in pairs:
                y = list(self.plot_buffers[name])
                cv.setData(list(range(len(y))), y)

    def _refresh_preview(self) -> None:
        color_bgr, depth_bgr = self.manager.get_preview()
        if color_bgr is not None:
            self.rgb_label.setPixmap(self._to_pixmap(color_bgr))
        if depth_bgr is not None:
            self.depth_label.setPixmap(self._to_pixmap(depth_bgr))

    def _refresh_status(self) -> None:
        stats = self.manager.get_runtime_stats()
        sd = stats.get("session_dir", "-")
        if sd != "-":
            if stats.get("csv_writing_enabled", False):
                csv_state = "CSV记录中"
            elif stats.get("tare_in_progress", False) or stats.get("shovel_tare_Fz", 0.0) != 0.0:
                csv_state = "已清零,等待开始记录"
            else:
                csv_state = "等待清零去皮重"
            self.path_label.setText(
                f"会话目录: {sd} | 样本数: {stats.get('sample_count', 0)} | {csv_state}"
            )

        # Weight panel
        self.w_tare_label.setText(
            f"空铲皮重: {stats.get('shovel_tare_Fz', 0.0):.3f} N"
        )
        self.w_fz_label.setText(
            f"当前 Fz (世界): {stats.get('Fz_world', 0.0):.3f} N"
        )

        # Tare progress
        if stats.get("tare_in_progress", False):
            pct = stats.get("tare_progress", 0.0) * 100
            self.w_weight_label.setText(f"皮重采集中... {pct:.0f}%")
            self.w_weight_label.setStyleSheet("color: #faad14;")
        else:
            self.w_weight_label.setText(
                f"泥重: {stats.get('weight_g', 0.0):.1f} g"
            )
            self.w_weight_label.setStyleSheet("color: #40a9ff;")

        # Stability
        if stats.get("is_stable", False):
            self.w_stable_label.setText("状态: ✓ 稳定 (可记录)")
            self.w_stable_label.setStyleSheet("color: #73d13d;")
        else:
            self.w_stable_label.setText("状态: ~ 波动中")
            self.w_stable_label.setStyleSheet("color: #ff4d4f;")

        last_w = stats.get("last_recorded_weight_g", 0.0)
        last_t = stats.get("last_recorded_time", "")
        if last_t:
            self.w_last_label.setText(f"最近记录: {last_w:.1f} g @ {last_t}")
        else:
            self.w_last_label.setText("最近记录: --")

        # RS errors
        rs_err = ""
        if self.manager.rs_adapter is not None:
            rs_err = self.manager.rs_adapter.last_error
        if rs_err:
            self._on_error(f"RealSense: {rs_err}")

    def _on_depth_changed(self) -> None:
        self.manager.update_depth_colorizer(
            min_distance=self.depth_min_spin.value(),
            max_distance=self.depth_max_spin.value(),
            color_scheme=self.depth_cmap.currentIndex(),
            histogram_eq=self.depth_histeq.isChecked(),
        )

    # ============================================================
    #  Helpers
    # ============================================================

    @staticmethod
    def _to_pixmap(bgr_image):
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        scale = min(420 / w, 280 / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)

        canvas = QImage(420, 280, QImage.Format_RGB888)
        canvas.fill(Qt.black)
        off_x = (420 - nw) // 2
        off_y = (280 - nh) // 2

        qimg = QImage(resized.data, nw, nh, resized.strides[0], QImage.Format_RGB888).copy()

        from PyQt5.QtGui import QPainter
        pixmap = QPixmap(420, 280)
        pixmap.fill(Qt.black)
        painter = QPainter(pixmap)
        painter.drawImage(off_x, off_y, qimg)
        painter.end()
        return pixmap

    def closeEvent(self, event) -> None:
        if self.manager.is_recording():
            self.manager.stop_session(normal_stop=False)
        super().closeEvent(event)
