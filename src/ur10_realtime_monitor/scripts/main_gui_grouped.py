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
    QVBoxLayout,
    QWidget,
)

from ur_full_monitor import URFullMonitor


class DataWorker(QThread):
    data_signal = pyqtSignal(list)
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    path_signal = pyqtSignal(str)

    def __init__(self, robot_ip: str, port: int, data_root: Path) -> None:
        super().__init__()
        self.robot_ip = robot_ip
        self.port = port
        self.data_root = data_root
        self.monitor = URFullMonitor(robot_ip=robot_ip, port=port)
        self.running = True
        self.label = 0
        self.normal_stop = False

    def set_label(self, val: int) -> None:
        self.label = val

    def stop(self) -> None:
        self.running = False
        self.normal_stop = True
        self.monitor.close()
        self.wait(3000)

    def run(self) -> None:
        start_dt = datetime.now()
        stamp = start_dt.strftime("%Y%m%d_%H%M%S")
        session_dir = self.data_root / stamp
        session_dir.mkdir(parents=True, exist_ok=True)
        csv_path = session_dir / "ur10_realtime_data.csv"
        meta_path = session_dir / "metadata.txt"
        self.path_signal.emit(str(csv_path))

        sample_count = 0
        t0 = None

        if not self.monitor.connect():
            self.error_signal.emit(f"连接失败: {self.robot_ip}:{self.port}")
            meta_path.write_text(
                f"robot_ip: {self.robot_ip}\n"
                f"port: {self.port}\n"
                f"start_datetime: {start_dt.isoformat(sep=' ', timespec='seconds')}\n"
                f"csv_path: {csv_path}\n"
                f"sample_count: 0\n"
                f"stop_datetime: {datetime.now().isoformat(sep=' ', timespec='seconds')}\n"
                f"normal_stop: no\n",
                encoding="utf-8",
            )
            return

        self.status_signal.emit("监控中...")
        try:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.monitor.header)

                while self.running:
                    packet = self.monitor.read_packet()
                    if packet is None:
                        if self.running:
                            self.error_signal.emit("读取失败或连接断开")
                        break
                    row = self.monitor.parse_packet(packet)
                    if row is None:
                        continue

                    if t0 is None:
                        t0 = row[0]
                    row[0] = row[0] - t0
                    row.append(float(self.label))

                    writer.writerow(row)
                    sample_count += 1
                    if sample_count % 20 == 0:
                        f.flush()
                    self.data_signal.emit(row)
        except Exception as exc:
            self.error_signal.emit(f"线程异常: {exc}")
        finally:
            self.monitor.close()
            meta_path.write_text(
                f"robot_ip: {self.robot_ip}\n"
                f"port: {self.port}\n"
                f"start_datetime: {start_dt.isoformat(sep=' ', timespec='seconds')}\n"
                f"csv_path: {csv_path}\n"
                f"sample_count: {sample_count}\n"
                f"stop_datetime: {datetime.now().isoformat(sep=' ', timespec='seconds')}\n"
                f"normal_stop: {'yes' if self.normal_stop else 'no'}\n",
                encoding="utf-8",
            )
            self.status_signal.emit("已停止")


class URGroupedMonitorApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UR10 分组曲线监控 GUI - WSL2")
        self.resize(1450, 950)

        self.points = 300
        self.worker: DataWorker | None = None
        self.data_root = Path(__file__).resolve().parents[1] / "data"
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.header = URFullMonitor().header
        self.idx = {k: i for i, k in enumerate(self.header)}
        self.cache: Dict[str, deque] = {k: deque(maxlen=self.points) for k in self.header if k != "Label"}
        self.is_marking = False

        self.groups = {
            "关节角度 q (rad)": [f"Act_q{i}" for i in range(6)],
            "关节速度 qd (rad/s)": [f"Act_qd{i}" for i in range(6)],
            "关节电流 I (A)": [f"Act_I{i}" for i in range(6)],
            "TCP 位姿 (m/rad)": ["Act_X", "Act_Y", "Act_Z", "Act_RX", "Act_RY", "Act_RZ"],
            "TCP 速度": ["Act_dX", "Act_dY", "Act_dZ", "Act_dRX", "Act_dRY", "Act_dRZ"],
            "目标关节角 Tgt_q (rad)": [f"Tgt_q{i}" for i in range(6)],
            "状态量": ["Robot_Mode", "Safety_Mode", "Main_Voltage", "Robot_Voltage", "Robot_Current"],
        }
        self.plots = {}
        self.curves = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)

        ctrl = QHBoxLayout()
        self.ip_input = QLineEdit("10.160.9.21")
        self.port_input = QLineEdit("30003")
        self.btn_start = QPushButton("开始监控")
        self.btn_stop = QPushButton("停止监控")
        self.btn_mark = QPushButton("实验标记 (Space)")
        self.btn_mark.setCheckable(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)
        self.status_label = QLabel("状态: 等待启动")
        self.path_label = QLabel("CSV路径: -")

        ctrl.addWidget(QLabel("机器人IP:"))
        ctrl.addWidget(self.ip_input)
        ctrl.addWidget(QLabel("端口:"))
        ctrl.addWidget(self.port_input)
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.btn_mark)
        ctrl.addWidget(self.status_label)
        vbox.addLayout(ctrl)
        vbox.addWidget(self.path_label)

        grid_wrap = QWidget()
        grid = QGridLayout(grid_wrap)
        vbox.addWidget(grid_wrap)

        colors = ["#ff4d4f", "#40a9ff", "#73d13d", "#faad14", "#9254de", "#13c2c2"]
        group_items = list(self.groups.items())
        for i, (title, signals) in enumerate(group_items):
            r, c = divmod(i, 3)
            plot = pg.PlotWidget(title=title)
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.addLegend()
            curves = []
            for j, sig in enumerate(signals):
                pen = pg.mkPen(colors[j % len(colors)], width=2)
                curves.append(plot.plot([], [], pen=pen, name=sig))
            self.plots[title] = plot
            self.curves[title] = curves
            grid.addWidget(plot, r, c)

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
        if self.worker:
            self.worker.set_label(1 if self.is_marking else 0)
        if self.is_marking:
            self.status_label.setText("状态: 正在标记实验段")
            self.btn_mark.setText("取消标记 (Space)")
        else:
            self.status_label.setText("状态: 监控中")
            self.btn_mark.setText("实验标记 (Space)")

    def start_monitor(self) -> None:
        ip = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            self.status_label.setText("状态: 端口格式错误")
            return

        for q in self.cache.values():
            q.clear()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_mark.setEnabled(True)
        self.btn_mark.setChecked(False)
        self.status_label.setText("状态: 正在连接...")

        self.worker = DataWorker(ip, port, self.data_root)
        self.worker.data_signal.connect(self.on_data)
        self.worker.status_signal.connect(self.on_status)
        self.worker.error_signal.connect(self.on_error)
        self.worker.path_signal.connect(lambda p: self.path_label.setText(f"CSV路径: {p}"))
        self.worker.start()

    def stop_monitor(self) -> None:
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)
        self.btn_mark.setChecked(False)
        self.btn_mark.setText("实验标记 (Space)")

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

    def on_data(self, row: List[float]) -> None:
        for key, i in self.idx.items():
            if key == "Label":
                continue
            self.cache[key].append(row[i])

        for title, signals in self.groups.items():
            for j, sig in enumerate(signals):
                y = list(self.cache[sig])
                x = list(range(len(y)))
                self.curves[title][j].setData(x, y)

    def closeEvent(self, event) -> None:
        self.stop_monitor()
        super().closeEvent(event)


def main() -> int:
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv)
    win = URGroupedMonitorApp()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
