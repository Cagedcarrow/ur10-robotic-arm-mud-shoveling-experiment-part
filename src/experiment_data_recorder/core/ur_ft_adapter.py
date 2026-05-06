from __future__ import annotations

import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

FT300_DIR = Path(__file__).resolve().parents[2] / "ur10_ft300_monitor" / "scripts"
if str(FT300_DIR) not in sys.path:
    sys.path.insert(0, str(FT300_DIR))

from ft300_reader import FT300Reader  # type: ignore  # noqa: E402
from ur_reader import URReader  # type: ignore  # noqa: E402


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


class URFTAdapter:
    def __init__(self) -> None:
        self.ur_worker: Optional[URWorker] = None
        self.ft_worker: Optional[FTWorker] = None

        self.ur_fields = URReader().fields
        self.ft_fields = FT300Reader().fields
        self.header = ["epoch_time", *self.ur_fields, *self.ft_fields, "Label", "ur_fresh", "ft_fresh"]

        self.latest_ur: Dict[str, float] = {}
        self.latest_ft: Dict[str, float] = {}
        self.latest_ft_raw: Dict[str, float] = {}
        self.ft_zero_offset: Dict[str, float] = {}
        self.ur_fresh = 0
        self.ft_fresh = 0

        self.csv_file = None
        self.csv_writer = None
        self.csv_path: Optional[Path] = None
        self.sample_count = 0

        self.status_cb: Optional[Callable[[str], None]] = None
        self.error_cb: Optional[Callable[[str], None]] = None
        self.errors: List[str] = []
        self.is_marking = False

    def configure_callbacks(
        self,
        status_cb: Optional[Callable[[str], None]] = None,
        error_cb: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.status_cb = status_cb
        self.error_cb = error_cb

    def _status(self, msg: str) -> None:
        if self.status_cb:
            self.status_cb(msg)

    def _error(self, msg: str) -> None:
        self.errors.append(msg)
        if self.error_cb:
            self.error_cb(msg)

    def start(
        self,
        session_dir: Path,
        ur_ip: str,
        ur_port: int,
        ft_port: str,
        ft_baud: int,
        ft_slave: int,
    ) -> None:
        self.sample_count = 0
        self.errors = []
        self.latest_ur = {}
        self.latest_ft = {}
        self.latest_ft_raw = {}
        self.ft_zero_offset = {k: 0.0 for k in self.ft_fields}
        self.ur_fresh = 0
        self.ft_fresh = 0

        self.csv_path = session_dir / "ur10_ft300_realtime_data.csv"
        self.csv_file = self.csv_path.open("w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(self.header)

        self.ur_worker = URWorker(ur_ip, ur_port, timeout=3.0)
        self.ft_worker = FTWorker(ft_port, ft_baud, timeout=0.2, slave_id=ft_slave)

        self.ur_worker.data_signal.connect(self.on_ur_data)
        self.ur_worker.error_signal.connect(self._error)
        self.ur_worker.status_signal.connect(self._status)

        self.ft_worker.data_signal.connect(self.on_ft_data)
        self.ft_worker.error_signal.connect(self._error)
        self.ft_worker.status_signal.connect(self._status)

        self.ur_worker.start()
        self.ft_worker.start()
        self._status("UR/FT采集已启动")

    def stop(self) -> None:
        if self.ur_worker is not None:
            self.ur_worker.stop()
            self.ur_worker = None
        if self.ft_worker is not None:
            self.ft_worker.stop()
            self.ft_worker = None

        if self.csv_file is not None:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
        self.csv_file = None
        self.csv_writer = None
        self._status("UR/FT采集已停止")

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

    def on_ft_data(self, data: Dict[str, float]) -> None:
        self.latest_ft_raw.update(data)
        corrected = {
            key: float(data.get(key, 0.0)) - float(self.ft_zero_offset.get(key, 0.0))
            for key in self.ft_fields
        }
        self.latest_ft.update(corrected)
        self.ft_fresh = 1
        self._write_fused_row()

    def tare_ft_sensor(self) -> bool:
        if not self.latest_ft_raw:
            return False
        for key in self.ft_fields:
            self.ft_zero_offset[key] = float(self.latest_ft_raw.get(key, 0.0))
        self._status(
            "FT300已清零: "
            + ", ".join(f"{k}={self.ft_zero_offset[k]:.3f}" for k in self.ft_fields)
        )
        return True

    def get_stats(self) -> dict:
        return {
            "sample_count": self.sample_count,
            "errors": list(self.errors),
            "csv_path": str(self.csv_path) if self.csv_path else "",
            "last_update": datetime.now().isoformat(sep=" ", timespec="seconds"),
        }
