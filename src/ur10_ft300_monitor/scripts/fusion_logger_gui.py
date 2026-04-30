#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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

from ft300_reader import FT300Reader
from ur_reader import URReader


class URWorker(QThread):
    data_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, ip: str, port: int, timeout: float = 3.0) -> None:
        super().__init__()
        self.reader = URReader(ip, port, timeout)
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.reader.close()
        self.wait(2000)

    def run(self) -> None:
        if not self.reader.connect():
            self.error_signal.emit(f"UR连接失败: {self.reader.robot_ip}:{self.reader.port}")
            return
        self.status_signal.emit("UR已连接")
        try:
            while self.running:
                pkt = self.reader.read_packet()
                if pkt is None:
                    if self.running:
                        self.error_signal.emit("UR读取失败或断开")
                    break
                row = self.reader.parse_packet(pkt)
                if row is not None:
                    self.data_signal.emit(row)
        finally:
            self.reader.close()


class FTWorker(QThread):
    data_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, port: str, baudrate: int, timeout: float, slave_id: int) -> None:
        super().__init__()
        self.reader = FT300Reader(port=port, baudrate=baudrate, timeout=timeout, slave_id=slave_id)
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.reader.close()
        self.wait(2000)

    def run(self) -> None:
        if not self.reader.connect():
            self.error_signal.emit(
                f"FT300连接失败: {self.reader.port} @ {self.reader.baudrate}, slave={self.reader.slave_id}"
            )
            return
        self.status_signal.emit("FT300已连接")
        try:
            while self.running:
                sample = self.reader.read_sample()
                if sample is not None:
                    self.data_signal.emit(sample)
        finally:
            self.reader.close()


class FusionWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("UR10 + FT300 一体化监控 GUI (绝对时间)")
        self.resize(1500, 950)

        self.points = 300
        self.root_dir = Path(__file__).resolve().parents[1]
        self.data_root = self.root_dir / "data"
        self.data_root.mkdir(parents=True, exist_ok=True)

        self.ur_worker: Optional[URWorker] = None
        self.ft_worker: Optional[FTWorker] = None
        self.is_marking = False

        self.latest_ur: Dict[str, float] = {}
        self.latest_ft: Dict[str, float] = {}
        self.ur_fresh = 0
        self.ft_fresh = 0

        self.ur_fields = URReader().fields
        self.ft_fields = FT300Reader().fields
        self.header = ["epoch_time", *self.ur_fields, *self.ft_fields, "Label", "ur_fresh", "ft_fresh"]

        self.csv_file = None
        self.csv_writer = None
        self.csv_path: Optional[Path] = None
        self.meta_path: Optional[Path] = None
        self.sample_count = 0
        self.start_dt: Optional[datetime] = None
        self.errors: List[str] = []

        self.curves = {}
        self.buffers = {name: deque(maxlen=self.points) for name in self.ur_fields + self.ft_fields}
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)

        top = QHBoxLayout()
        self.ur_ip = QLineEdit("10.160.9.21")
        self.ur_port = QLineEdit("30003")
        self.ft_port = QLineEdit("/dev/ttyUSB0")
        self.ft_baud = QLineEdit("19200")
        self.ft_slave = QLineEdit("9")
        self.btn_start = QPushButton("开始采集")
        self.btn_stop = QPushButton("停止采集")
        self.btn_mark = QPushButton("实验标记 (Space)")
        self.btn_mark.setCheckable(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)
        self.status = QLabel("状态: 等待启动")
        self.path_label = QLabel("CSV: -")

        top.addWidget(QLabel("UR IP"))
        top.addWidget(self.ur_ip)
        top.addWidget(QLabel("UR Port"))
        top.addWidget(self.ur_port)
        top.addWidget(QLabel("FT Port"))
        top.addWidget(self.ft_port)
        top.addWidget(QLabel("Baud"))
        top.addWidget(self.ft_baud)
        top.addWidget(QLabel("Slave"))
        top.addWidget(self.ft_slave)
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)
        top.addWidget(self.btn_mark)
        top.addWidget(self.status)
        vbox.addLayout(top)
        vbox.addWidget(self.path_label)

        grid_wrap = QWidget()
        grid = QGridLayout(grid_wrap)
        vbox.addWidget(grid_wrap)

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
                pen = pg.mkPen(colors[j % len(colors)], width=2)
                cv = pw.plot([], [], pen=pen, name=name)
                self.curves[title].append((name, cv))
            grid.addWidget(pw, r, c)

        self.btn_start.clicked.connect(self.start_capture)
        self.btn_stop.clicked.connect(self.stop_capture)
        self.btn_mark.clicked.connect(self.toggle_mark)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Space and self.btn_mark.isEnabled():
            self.btn_mark.toggle()
            self.toggle_mark()
        super().keyPressEvent(event)

    def toggle_mark(self) -> None:
        self.is_marking = self.btn_mark.isChecked()
        if self.is_marking:
            self.status.setText("状态: 正在标记实验段")
            self.btn_mark.setText("取消标记 (Space)")
        else:
            self.status.setText("状态: 采集中")
            self.btn_mark.setText("实验标记 (Space)")

    def _open_csv(self) -> None:
        self.start_dt = datetime.now()
        ts = self.start_dt.strftime("%Y%m%d_%H%M%S")
        session = self.data_root / ts
        session.mkdir(parents=True, exist_ok=True)
        self.csv_path = session / "ur10_ft300_realtime_data.csv"
        self.meta_path = session / "metadata.txt"
        self.csv_file = self.csv_path.open("w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(self.header)
        self.path_label.setText(f"CSV: {self.csv_path}")

    def _close_csv_and_write_meta(self, normal_stop: bool) -> None:
        if self.csv_file is not None:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
        if self.meta_path is not None and self.csv_path is not None and self.start_dt is not None:
            text = [
                f"ur_ip: {self.ur_ip.text().strip()}",
                f"ur_port: {self.ur_port.text().strip()}",
                f"ft_port: {self.ft_port.text().strip()}",
                f"ft_baudrate: {self.ft_baud.text().strip()}",
                f"ft_slave_id: {self.ft_slave.text().strip()}",
                f"start_datetime: {self.start_dt.isoformat(sep=' ', timespec='seconds')}",
                f"csv_path: {self.csv_path}",
                f"sample_count: {self.sample_count}",
                f"stop_datetime: {datetime.now().isoformat(sep=' ', timespec='seconds')}",
                f"normal_stop: {'yes' if normal_stop else 'no'}",
                f"errors: {' | '.join(self.errors) if self.errors else 'none'}",
            ]
            self.meta_path.write_text("\n".join(text) + "\n", encoding="utf-8")

    def start_capture(self) -> None:
        try:
            ur_port = int(self.ur_port.text().strip())
            ft_baud = int(self.ft_baud.text().strip())
            ft_slave = int(self.ft_slave.text().strip())
        except ValueError:
            self.status.setText("状态: 参数格式错误")
            return

        self.sample_count = 0
        self.errors = []
        self.latest_ur = {}
        self.latest_ft = {}
        self.ur_fresh = 0
        self.ft_fresh = 0
        for v in self.buffers.values():
            v.clear()
        self._open_csv()

        self.ur_worker = URWorker(self.ur_ip.text().strip(), ur_port, timeout=3.0)
        self.ft_worker = FTWorker(self.ft_port.text().strip(), ft_baud, timeout=0.2, slave_id=ft_slave)

        self.ur_worker.data_signal.connect(self.on_ur_data)
        self.ur_worker.error_signal.connect(self.on_error)
        self.ur_worker.status_signal.connect(self.on_status)
        self.ft_worker.data_signal.connect(self.on_ft_data)
        self.ft_worker.error_signal.connect(self.on_error)
        self.ft_worker.status_signal.connect(self.on_status)

        self.ur_worker.start()
        self.ft_worker.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_mark.setEnabled(True)
        self.btn_mark.setChecked(False)
        self.is_marking = False
        self.status.setText("状态: 正在连接...")

    def stop_capture(self) -> None:
        if self.ur_worker is not None:
            self.ur_worker.stop()
            self.ur_worker = None
        if self.ft_worker is not None:
            self.ft_worker.stop()
            self.ft_worker = None

        self._close_csv_and_write_meta(normal_stop=True)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_mark.setEnabled(False)
        self.btn_mark.setChecked(False)
        self.btn_mark.setText("实验标记 (Space)")
        self.status.setText("状态: 已停止")

    def on_status(self, msg: str) -> None:
        self.status.setText(f"状态: {msg}")

    def on_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.status.setText(f"状态: {msg}")

    def _write_fused_row(self) -> None:
        if self.csv_writer is None:
            return
        epoch_time = time.time()
        row = [epoch_time]
        for f in self.ur_fields:
            row.append(self.latest_ur.get(f, float("nan")))
        for f in self.ft_fields:
            row.append(self.latest_ft.get(f, float("nan")))
        row.append(1 if self.is_marking else 0)
        row.append(self.ur_fresh)
        row.append(self.ft_fresh)
        self.csv_writer.writerow(row)
        self.sample_count += 1
        if self.csv_file is not None and self.sample_count % 20 == 0:
            self.csv_file.flush()
        self.ur_fresh = 0
        self.ft_fresh = 0

    def on_ur_data(self, data: Dict[str, float]) -> None:
        self.latest_ur.update(data)
        self.ur_fresh = 1
        self._write_fused_row()
        self._refresh_plots()

    def on_ft_data(self, data: Dict[str, float]) -> None:
        self.latest_ft.update(data)
        self.ft_fresh = 1
        self._write_fused_row()
        self._refresh_plots()

    def _refresh_plots(self) -> None:
        for f in self.ur_fields:
            if f in self.latest_ur:
                self.buffers[f].append(self.latest_ur[f])
        for f in self.ft_fields:
            if f in self.latest_ft:
                self.buffers[f].append(self.latest_ft[f])

        for _, pairs in self.curves.items():
            for name, cv in pairs:
                y = list(self.buffers[name])
                x = list(range(len(y)))
                cv.setData(x, y)

    def closeEvent(self, event) -> None:
        self.stop_capture()
        super().closeEvent(event)


def main() -> int:
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv)
    win = FusionWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
