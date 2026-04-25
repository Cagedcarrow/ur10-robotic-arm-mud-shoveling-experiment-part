"""Simple UR monitor utility used by ur10_server_.py.

Provides:
- URMonitor.connect() -> bool
- URMonitor.start_logging(csv_path, stop_event)

Data source uses python-urx high-level getters and writes CSV rows.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import List, Optional

import urx


@dataclass
class URMonitor:
    robot_ip: str
    sample_hz: float = 50.0
    connect_timeout_sec: float = 5.0
    _robot: Optional[urx.Robot] = field(default=None, init=False, repr=False)

    def connect(self) -> bool:
        """Connect to UR robot using python-urx.

        Returns True on success, False on failure.
        """
        try:
            # timeout here is socket timeout used internally by urx
            self._robot = urx.Robot(self.robot_ip, use_rt=True)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[URMonitor] connect failed: {exc}")
            self._robot = None
            return False

    def close(self) -> None:
        """Close robot connection safely."""
        if self._robot is not None:
            try:
                self._robot.close()
            except Exception:
                pass
            finally:
                self._robot = None

    def _safe_getj(self) -> List[float]:
        try:
            return list(self._robot.getj()) if self._robot is not None else [float("nan")] * 6
        except Exception:
            return [float("nan")] * 6

    def _safe_getl(self) -> List[float]:
        try:
            return list(self._robot.getl()) if self._robot is not None else [float("nan")] * 6
        except Exception:
            return [float("nan")] * 6

    def _safe_get_tcp_force(self) -> List[float]:
        # Prefer tcp-force vector if available, fallback to scalar force.
        if self._robot is None:
            return [float("nan")] * 6

        try:
            f = self._robot.get_tcp_force()
            if isinstance(f, (list, tuple)) and len(f) >= 6:
                return [float(f[i]) for i in range(6)]
        except Exception:
            pass

        try:
            scalar = float(self._robot.get_force())
            return [scalar, float("nan"), float("nan"), float("nan"), float("nan"), float("nan")]
        except Exception:
            return [float("nan")] * 6

    def start_logging(self, csv_path: str, stop_event: Event) -> None:
        """Write robot state to CSV until stop_event is set.

        CSV columns:
          timestamp_local_iso, unix_time,
          q0..q5, x,y,z,rx,ry,rz,
          fx,fy,fz,tx,ty,tz
        """
        if self._robot is None:
            raise RuntimeError("URMonitor is not connected. Call connect() first.")

        path = Path(csv_path)
        if path.parent and str(path.parent) not in ("", "."):
            path.parent.mkdir(parents=True, exist_ok=True)

        period = 1.0 / max(1.0, float(self.sample_hz))

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp_local_iso",
                "unix_time",
                "q0",
                "q1",
                "q2",
                "q3",
                "q4",
                "q5",
                "x",
                "y",
                "z",
                "rx",
                "ry",
                "rz",
                "fx",
                "fy",
                "fz",
                "tx",
                "ty",
                "tz",
            ])

            while not stop_event.is_set():
                t_wall = time.time()
                t_local = datetime.now().isoformat()

                q = self._safe_getj()
                tcp = self._safe_getl()
                wrench = self._safe_get_tcp_force()

                writer.writerow([
                    t_local,
                    f"{t_wall:.6f}",
                    *[f"{v:.9f}" for v in q],
                    *[f"{v:.9f}" for v in tcp],
                    *[f"{v:.9f}" for v in wrench],
                ])
                f.flush()

                # Sleep with stop responsiveness.
                end_t = time.time() + period
                while not stop_event.is_set() and time.time() < end_t:
                    time.sleep(0.001)
