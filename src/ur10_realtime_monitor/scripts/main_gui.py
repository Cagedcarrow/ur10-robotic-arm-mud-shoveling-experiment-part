#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pyqtgraph as pg
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ur_full_monitor import URFullMonitor


class DataWorker(QThread):
    data_signal = pyqtSignal(list)
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    started_path_signal = pyqtSignal(str)
    finished_meta_signal = pyqtSignal(str)

    def __init__(self, robot_ip: str, port: int, base_dir: Path) -> None:
        super().__init__()
        self.robot_ip = robot_ip
        self.port = port
        self.base_dir = base_dir
        self.running = True
        self.current_label = 0
        self.sample_count = 0
        self._normal_stop = False
        self._t0 = None

        self.monitor = URFullMonitor(robot_ip=self.robot_ip, port=self.port)
        self.capture_dir: Path | None = None
        self.csv_path: Path | None = None
        self.metadata_path: Path | None = None
        self.start_dt: datetime | None = None

    def stop(self) -> None:
        self.running = False
        self._normal_stop = True
        self.monitor.close()
        self.wait(3000)

    def set_label(self, label: int) -> None:
        self.current_label = label

    def _write_metadata(self, stop_dt: datetime, normal_stop: bool) -> None:
        if self.metadata_path is None or self.csv_path is None or self.start_dt is None:
            return
        lines = [
            f"robot_ip: {self.robot_ip}",
            f"port: {self.port}",
            f"start_datetime: {self.start_dt.isoformat(sep=' ', timespec='seconds')}",
            f"csv_path: {self.csv_path}",
            f"sample_count: {self.sample_count}",
            f"stop_datetime: {stop_dt.isoformat(sep=' ', timespec='seconds')}",
            f"normal_stop: {'yes' if normal_stop else 'no'}",
        ]
        self.metadata_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.finished_meta_signal.emit(str(self.metadata_path))

    def run(self) -> None:
        self.start_dt = datetime.now()
        ts = self.start_dt.strftime("%Y%m%d_%H%M%S")
        self.capture_dir = self.base_dir / ts
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.capture_dir / "ur10_realtime_data.csv"
        self.metadata_path = self.capture_dir / "metadata.txt"
        self.started_path_signal.emit(str(self.csv_path))

        if not self.monitor.connect():
            self.error_signal.emit(f"连接失败: {self.robot_ip}:{self.port}")
            self._write_metadata(datetime.now(), normal_stop=False)
            return

        self.status_signal.emit("监控中...")
        try:
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.monitor.header)

                while self.running:
                    packet = self.monitor.read_packet()
                    if packet is None:
                        if self.running:
                            self.error_signal.emit("读取数据失败或连接中断")
                        break

                    row = self.monitor.parse_packet(packet)
                    if row is None:
                        continue

                    if self._t0 is None:
                        self._t0 = row[0]
                    row[0] = row[0] - self._t0
                    row.append(float(self.current_label))

                    writer.writerow(row)
                    self.sample_count += 1
                    if self.sample_count % 20 == 0:
                        f.flush()
                    self.data_signal.emit(row)
        except Exception as exc:
            self.error_signal.emit(f"采集线程异常: {exc}")
        finally:
            self.monitor.close()
            self._write_metadata(datetime.now(), normal_stop=self._normal_stop)
            self.status_signal.emit("已停止")


class PlotGridTab(QWidget):
    def __init__(self, title_names: List[str], y_unit: str = "") -> None:
        super().__init__()
        self.curves = {}
        layout = QGridLayout(self)

        for idx, name in enumerate(title_names):
            r, c = divmod(idx, 3)
            plot = pg.PlotWidget()
            plot.setTitle(f"{name} ({y_unit})" if y_unit else name)
            plot.showGrid(x=True, y=True, alpha=0.25)
            curve = plot.plot([], [], pen=pg.mkPen(width=2))
            layout.addWidget(plot, r, c)
            self.curves[name] = curve


class URMonitorApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UR10 实时数据接收验证系统 - WSL2")
        self.resize(1400, 900)

        self.points = 300
        self.worker: DataWorker | None = None
        self.is_marking = False
        self.root_dir = Path(__file__).resolve().parents[1]
        self.data_dir = self.root_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.series_map: Dict[str, deque] = {}
        self.signal_groups = {
            "关节角度": [f"Act_q{i}" for i in range(6)],
            "关节速度": [f"Act_qd{i}" for i in range(6)],
            "关节电流": [f"Act_I{i}" for i in range(6)],
            "TCP位姿": ["Act_X", "Act_Y", "Act_Z", "Act_RX", "Act_RY", "Act_RZ"],
            "TCP速度": ["Act_dX", "Act_dY", "Act_dZ", "Act_dRX", "Act_dRY", "Act_dRZ"],
            "目标关节角": [f"Tgt_q{i}" for i in range(6)],
            "状态信息": ["Robot_Mode", "Safety_Mode", "Main_Voltage", "Robot_Voltage", "Robot_Current"],
        }
        self.header_index = {name: i for i, name in enumerate(URFullMonitor().header)}

        for key in self.header_index:
            if key != "Label":
                self.series_map[key] = deque(maxlen=self.points)

        self.tabs: Dict[str, PlotGridTab] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        control = QHBoxLayout()
        self.ip_input = QLineEdit("10.160.9.21")
        self.port_input = QLineEdit("30003")
        self.btn_start = QPushButton("开始监控")
        self.btn_stop = QPushButton("停止监控")
        self.btn_mark = QPushButton("实验标记 (Space)")
        self.status_label = QLabel("状态: 等待启动")
        self.path_label = QLabel("CSV路径: -")

        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)
        self.btn_mark.setCheckable(True)

        control.addWidget(QLabel("机器人 IP:"))
        control.addWidget(self.ip_input)
        control.addWidget(QLabel("端口:"))
        control.addWidget(self.port_input)
        control.addWidget(self.btn_start)
        control.addWidget(self.btn_stop)
        control.addWidget(self.btn_mark)
        control.addWidget(self.status_label)
        root_layout.addLayout(control)
        root_layout.addWidget(self.path_label)

        tab_widget = QTabWidget()
        root_layout.addWidget(tab_widget)

        tab_defs = [
            ("关节角度页面", self.signal_groups["关节角度"], "rad"),
            ("关节速度页面", self.signal_groups["关节速度"], "rad/s"),
            ("关节电流页面", self.signal_groups["关节电流"], "A"),
            ("TCP位姿页面", self.signal_groups["TCP位姿"], ""),
            ("TCP速度页面", self.signal_groups["TCP速度"], ""),
            ("目标关节角页面", self.signal_groups["目标关节角"], "rad"),
            ("状态信息页面", self.signal_groups["状态信息"], ""),
        ]
        for title, names, unit in tab_defs:
            tab = PlotGridTab(names, unit)
            tab_widget.addTab(tab, title)
            self.tabs[title] = tab

        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.btn_mark.clicked.connect(self.toggle_mark)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Space and self.btn_mark.isEnabled():
            self.btn_mark.toggle()
            self.toggle_mark()
        super().keyPressEvent(event)

    def toggle_mark(self) -> None:
        self.is_marking = self.btn_mark.isChecked()
        if self.worker is not None:
            self.worker.set_label(1 if self.is_marking else 0)
        if self.is_marking:
            self.status_label.setText("状态: 正在标记实验段")
            self.btn_mark.setText("取消标记 (Space)")
        else:
            self.status_label.setText("状态: 监控中")
            self.btn_mark.setText("实验标记 (Space)")

    def start_monitor(self) -> None:
        robot_ip = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            self.status_label.setText("状态: 端口格式错误")
            return

        for k in self.series_map:
            self.series_map[k].clear()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_mark.setEnabled(True)
        self.btn_mark.setChecked(False)
        self.is_marking = False
        self.status_label.setText("状态: 正在连接...")

        self.worker = DataWorker(robot_ip=robot_ip, port=port, base_dir=self.data_dir)
        self.worker.data_signal.connect(self.on_data)
        self.worker.status_signal.connect(self.on_status)
        self.worker.error_signal.connect(self.on_error)
        self.worker.started_path_signal.connect(self.on_csv_path)
        self.worker.finished_meta_signal.connect(self.on_metadata_done)
        self.worker.start()

    def stop_monitor(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)
        self.btn_mark.setChecked(False)
        self.is_marking = False
        self.btn_mark.setText("实验标记 (Space)")

    def closeEvent(self, event) -> None:
        self.stop_monitor()
        super().closeEvent(event)

    def on_status(self, msg: str) -> None:
        self.status_label.setText(f"状态: {msg}")
        if msg == "已停止":
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_mark.setEnabled(False)

    def on_error(self, msg: str) -> None:
        self.status_label.setText(f"状态: {msg}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)

    def on_csv_path(self, path_str: str) -> None:
        self.path_label.setText(f"CSV路径: {path_str}")

    def on_metadata_done(self, path_str: str) -> None:
        self.statusBar().showMessage(f"metadata 已写入: {path_str}", 5000)

    def on_data(self, row: List[float]) -> None:
        row_map = {name: row[idx] for name, idx in self.header_index.items() if name != "Label"}
        for key, val in row_map.items():
            self.series_map[key].append(val)

        for tab_name, signals in [
            ("关节角度页面", self.signal_groups["关节角度"]),
            ("关节速度页面", self.signal_groups["关节速度"]),
            ("关节电流页面", self.signal_groups["关节电流"]),
            ("TCP位姿页面", self.signal_groups["TCP位姿"]),
            ("TCP速度页面", self.signal_groups["TCP速度"]),
            ("目标关节角页面", self.signal_groups["目标关节角"]),
            ("状态信息页面", self.signal_groups["状态信息"]),
        ]:
            tab = self.tabs[tab_name]
            for name in signals:
                y = list(self.series_map[name])
                x = list(range(len(y)))
                tab.curves[name].setData(x, y)


def main() -> int:
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv)
    win = URMonitorApp()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
