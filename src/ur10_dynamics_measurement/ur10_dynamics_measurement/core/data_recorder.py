from __future__ import annotations

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import MeasurementConfig

CSV_HEADER = [
    "timestamp",
    "sec",
    "nanosec",
    "q_0", "q_1", "q_2", "q_3", "q_4", "q_5",
    "dq_0", "dq_1", "dq_2", "dq_3", "dq_4", "dq_5",
    "current_0", "current_1", "current_2", "current_3", "current_4", "current_5",
    "tau_estimated_0", "tau_estimated_1", "tau_estimated_2",
    "tau_estimated_3", "tau_estimated_4", "tau_estimated_5",
    "Fx", "Fy", "Fz",
    "Mx", "My", "Mz",
    "tau_ft_0", "tau_ft_1", "tau_ft_2",
    "tau_ft_3", "tau_ft_4", "tau_ft_5",
    "ft_tare_applied",
    "speed_scaling",
    "label",
]


class DataRecorder:
    """Manages CSV file writing and session metadata."""

    def __init__(self, config: MeasurementConfig) -> None:
        self.cfg = config
        self.session_dir: Optional[Path] = None
        self.csv_path: Optional[Path] = None
        self.csv_file = None
        self.csv_writer = None
        self.start_time: Optional[datetime] = None
        self.sample_count = 0
        self.is_recording = False
        self.errors: List[str] = []

    def start_session(self, tare_offsets: Optional[Dict[str, float]] = None,
                      motor_gains: Optional[List[float]] = None) -> Path:
        """Create a new session directory and open CSV file."""
        self.start_time = datetime.now()
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")

        base = self.cfg.data_root
        base.mkdir(parents=True, exist_ok=True)
        self.session_dir = base / timestamp
        self.session_dir.mkdir(parents=True, exist_ok=False)

        self.csv_path = self.session_dir / "measurement_data.csv"
        self.csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(CSV_HEADER)
        self.is_recording = True
        self.sample_count = 0

        # Store config snapshot for metadata
        self._tare_offsets = dict(tare_offsets or {})
        self._motor_gains = list(motor_gains or [])

        return self.session_dir

    def write_row(self, data: Dict) -> None:
        """Write one row from a data dict."""
        if not self.is_recording or self.csv_writer is None:
            return

        row = [
            time.time(),
            data.get("sec", 0),
            data.get("nanosec", 0),
            *data.get("q", [0.0] * 6),
            *data.get("dq", [0.0] * 6),
            *data.get("current", [0.0] * 6),
            *data.get("tau_estimated", [0.0] * 6),
            *data.get("force", [0.0] * 3),
            *data.get("torque", [0.0] * 3),
            *data.get("tau_ft", [0.0] * 6),
            1 if data.get("ft_tare_applied") else 0,
            data.get("speed_scaling", 1.0),
            data.get("label", 0),
        ]
        self.csv_writer.writerow(row)
        self.sample_count += 1

        if self.sample_count % 20 == 0 and self.csv_file is not None:
            self.csv_file.flush()
            os.fsync(self.csv_file.fileno())

    def stop_session(self, normal_stop: bool = True) -> None:
        """Close CSV and write metadata."""
        self.is_recording = False

        if self.csv_file is not None:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None

        self._write_metadata(normal_stop)

    def _write_metadata(self, normal_stop: bool) -> None:
        """Write session_metadata.txt with full experiment context."""
        if self.session_dir is None:
            return

        lines = [
            f"start_datetime: {self.start_time.isoformat(sep=' ', timespec='seconds') if self.start_time else 'unknown'}",
            f"stop_datetime: {datetime.now().isoformat(sep=' ', timespec='seconds')}",
            f"normal_stop: {'yes' if normal_stop else 'no'}",
            f"session_dir: {self.session_dir}",
            f"csv_path: {self.csv_path}",
            f"sample_count: {self.sample_count}",
            f"joint_names: {self.cfg.joint_names}",
            f"motor_gains: {self._motor_gains}",
            f"ft_tare_applied: {bool(self._tare_offsets)}",
        ]

        if self._tare_offsets:
            lines.append("ft_tare_offsets:")
            for k, v in self._tare_offsets.items():
                lines.append(f"  {k}: {v:.4f}")

        if self.errors:
            lines.append(f"errors: {' | '.join(self.errors)}")
        else:
            lines.append("errors: none")

        lines.append("")  # trailing newline

        (self.session_dir / "session_metadata.txt").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    def get_stats(self) -> dict:
        return {
            "sample_count": self.sample_count,
            "session_dir": str(self.session_dir) if self.session_dir else "",
            "csv_path": str(self.csv_path) if self.csv_path else "",
        }
