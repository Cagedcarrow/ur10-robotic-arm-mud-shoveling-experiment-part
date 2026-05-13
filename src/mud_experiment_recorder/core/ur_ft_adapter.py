from __future__ import annotations

import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

# --- Import UR / FT300 readers from sibling package ---
FT300_DIR = Path(__file__).resolve().parents[2] / "ur10_ft300_monitor" / "scripts"
if str(FT300_DIR) not in sys.path:
    sys.path.insert(0, str(FT300_DIR))

from ft300_reader import FT300Reader  # type: ignore  # noqa: E402
from ur_reader import URReader  # type: ignore  # noqa: E402

# --- Import dynamics / kinematics / weight ---
_PKG = Path(__file__).resolve().parents[1]
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from kinematics.dynamics_estimator import DynamicsEstimator  # type: ignore  # noqa: E402
from kinematics.kinematics import UR10Kinematics  # type: ignore  # noqa: E402
from core.weight_calculator import WeightCalculator  # type: ignore  # noqa: E402


# ============================================================
#  Worker threads  (unchanged from experiment_data_recorder)
# ============================================================

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


# ============================================================
#  URFTAdapter  (enhanced with dynamics + weight)
# ============================================================

class URFTAdapter:
    """Orchestrates UR + FT300 data streams, computes dynamics and weight."""

    def __init__(self, motor_gains: List[float]) -> None:
        self.ur_worker: Optional[URWorker] = None
        self.ft_worker: Optional[FTWorker] = None

        self.ur_fields = URReader().fields
        self.ft_fields = FT300Reader().fields

        # --- Dynamics estimation ---
        self.dynamics = DynamicsEstimator(motor_gains)
        self.kinematics = self.dynamics.ensure_kinematics()
        R_tcp_sensor = self.kinematics.get_tcp_to_sensor_rotation()
        self.weight_calc = WeightCalculator(R_tcp_sensor)

        # --- Extended CSV header ---
        tau_est_cols = [f"tau_estimated_{i}" for i in range(6)]
        tau_ft_cols = [f"tau_ft_{i}" for i in range(6)]
        weight_cols = ["force_base_x", "force_base_y", "force_base_z", "weight_g"]
        self.header = (
            ["epoch_time"]
            + self.ur_fields
            + self.ft_fields
            + tau_est_cols
            + tau_ft_cols
            + weight_cols
            + ["Label", "ur_fresh", "ft_fresh"]
        )

        # --- Latest data ---
        self.latest_ur: Dict[str, float] = {}
        self.latest_ft: Dict[str, float] = {}
        self.latest_ft_raw: Dict[str, float] = {}
        self.ft_zero_offset: Dict[str, float] = {}

        # --- Computed values for GUI ---
        self.latest_tau_estimated: np.ndarray = np.zeros(6)
        self.latest_tau_ft: np.ndarray = np.zeros(6)
        self.latest_Fz_world: float = 0.0
        self.latest_weight_g: float = 0.0
        self.latest_force_base: np.ndarray = np.zeros(3)

        self.ur_fresh = 0
        self.ft_fresh = 0

        self.csv_file: Any = None
        self.csv_writer: Any = None
        self.csv_path: Optional[Path] = None
        self.sample_count = 0
        self.csv_writing_enabled: bool = False  # CSV writing starts only after tare

        self.status_cb: Optional[Callable[[str], None]] = None
        self.error_cb: Optional[Callable[[str], None]] = None
        self.errors: List[str] = []
        self.is_marking = False

    # ---- Callbacks ----

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

    # ---- Start / Stop ----

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
        self.csv_writing_enabled = False
        self.weight_calc.reset()

        # CSV file path is set but file is NOT opened yet.
        # It will be opened on enable_csv_writing() after the user clicks "清零并皮重".
        self.csv_path = session_dir / "session_data.csv"
        self.csv_file = None
        self.csv_writer = None

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
        self._status("UR/FT采集已启动 (CSV等待清零并皮重后开始记录)")

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

    # ---- Data handlers (called via Qt signals, running in main thread) ----

    def on_ur_data(self, data: Dict[str, float]) -> None:
        self.latest_ur.update(data)
        self.ur_fresh = 1

        # Compute estimated torques from motor currents
        try:
            currents = [float(data.get(f"Act_I{i}", 0.0)) for i in range(6)]
            self.latest_tau_estimated = self.dynamics.estimate_joint_torques(currents)
        except Exception:
            pass

        self._write_fused_row()

    def on_ft_data(self, data: Dict[str, float]) -> None:
        self.latest_ft_raw.update(data)
        corrected = {
            key: float(data.get(key, 0.0)) - float(self.ft_zero_offset.get(key, 0.0))
            for key in self.ft_fields
        }
        self.latest_ft.update(corrected)
        self.ft_fresh = 1

        # Compute FT-mapped joint torques
        try:
            q = [float(self.latest_ur.get(f"Act_q{i}", 0.0)) for i in range(6)]
            force = [float(corrected.get("Fx", 0.0)), float(corrected.get("Fy", 0.0)), float(corrected.get("Fz", 0.0))]
            torque = [float(corrected.get("Mx", 0.0)), float(corrected.get("My", 0.0)), float(corrected.get("Mz", 0.0))]
            self.latest_tau_ft = self.dynamics.compute_ft_joint_torques(q, force, torque)
        except Exception:
            pass

        # Compute weight (force projected to world Z)
        try:
            tcp_rotvec = [
                float(self.latest_ur.get("Act_RX", 0.0)),
                float(self.latest_ur.get("Act_RY", 0.0)),
                float(self.latest_ur.get("Act_RZ", 0.0)),
            ]
            self.latest_weight_g = self.weight_calc.update(force, tcp_rotvec)
            self.latest_Fz_world = self.weight_calc.current_Fz_world
            self.latest_force_base = self.weight_calc.current_force_base.copy()
        except Exception:
            pass

        self._write_fused_row()

    # ---- CSV writing ----

    def enable_csv_writing(self) -> None:
        """Open CSV file, write header, and enable row writing.

        Called after the user clicks the combined "清零并皮重" button.
        """
        if self.csv_writing_enabled:
            return
        if self.csv_path is None:
            return
        self.csv_file = self.csv_path.open("w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(self.header)
        self.csv_file.flush()
        self.csv_writing_enabled = True
        self._status("CSV记录已开始")

    def _write_fused_row(self) -> None:
        if not self.csv_writing_enabled or self.csv_writer is None:
            return
        epoch_time = time.time()
        row: List[Any] = [epoch_time]

        # UR fields
        for f in self.ur_fields:
            row.append(self.latest_ur.get(f, float("nan")))
        # FT fields
        for f in self.ft_fields:
            row.append(self.latest_ft.get(f, float("nan")))
        # tau_estimated 0-5
        for i in range(6):
            row.append(float(self.latest_tau_estimated[i]))
        # tau_ft 0-5
        for i in range(6):
            row.append(float(self.latest_tau_ft[i]))
        # force_base_x/y/z, weight_g
        row.append(float(self.latest_force_base[0]))
        row.append(float(self.latest_force_base[1]))
        row.append(float(self.latest_force_base[2]))
        row.append(float(self.latest_weight_g))
        # Label, freshness flags
        row.append(1 if self.is_marking else 0)
        row.append(self.ur_fresh)
        row.append(self.ft_fresh)

        self.csv_writer.writerow(row)
        self.sample_count += 1
        if self.csv_file is not None and self.sample_count % 20 == 0:
            self.csv_file.flush()
        self.ur_fresh = 0
        self.ft_fresh = 0

    # ---- Tare / Weight ----

    def tare_ft_sensor(self) -> bool:
        """Zero FT300 sensor reading."""
        if not self.latest_ft_raw:
            return False
        for key in self.ft_fields:
            self.ft_zero_offset[key] = float(self.latest_ft_raw.get(key, 0.0))
        self._status(
            "FT300已清零: "
            + ", ".join(f"{k}={self.ft_zero_offset[k]:.3f}" for k in self.ft_fields)
        )
        return True

    def zero_and_tare(self) -> None:
        """Zero FT300 sensor + begin shovel tare sampling.

        CSV writing is NOT enabled here — user must click "开始记录数据" separately.
        """
        self.tare_ft_sensor()
        self.weight_calc.start_tare_shovel()

    def is_tare_in_progress(self) -> bool:
        return self.weight_calc.is_tare_in_progress()

    def tare_progress(self) -> float:
        return self.weight_calc.tare_progress()

    def record_weight(self) -> float:
        """Capture current mud weight. Returns weight in grams."""
        return self.weight_calc.record_weight()

    # ---- Stats ----

    def get_stats(self) -> dict:
        return {
            "sample_count": self.sample_count,
            "errors": list(self.errors),
            "csv_path": str(self.csv_path) if self.csv_path else "",
            "csv_writing_enabled": self.csv_writing_enabled,
            "last_update": datetime.now().isoformat(sep=" ", timespec="seconds"),
        }
