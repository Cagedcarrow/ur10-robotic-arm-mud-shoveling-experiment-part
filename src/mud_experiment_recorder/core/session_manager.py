from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from .config import MudRecorderConfig
from .data_recorder import ExcelRecorder
from .path_utils import create_session_dir
from .realsense_adapter import RealSenseAdapter
from .ur_ft_adapter import URFTAdapter


class SessionManager:
    """Orchestrates recording session: adapters + Excel output lifecycle."""

    def __init__(self) -> None:
        self.config = MudRecorderConfig()
        self.rs_adapter: Optional[RealSenseAdapter] = None
        self.urft_adapter: Optional[URFTAdapter] = None
        self.excel_recorder: Optional[ExcelRecorder] = None
        self.session_dir: Optional[Path] = None
        self.start_time: Optional[datetime] = None
        self.last_error = ""

        self.status_cb: Optional[Callable[[str], None]] = None
        self.error_cb: Optional[Callable[[str], None]] = None

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
        self.last_error = msg
        if self.error_cb:
            self.error_cb(msg)

    def start_session(self, config: MudRecorderConfig) -> Path:
        """Create session dir, start all adapters, begin recording. Returns session_dir."""
        self.config = config
        self.last_error = ""
        self.start_time = datetime.now()
        self.session_dir = create_session_dir(self.config.data_root)

        # 1. RealSense camera
        self.rs_adapter = RealSenseAdapter(
            width=self.config.rs_width,
            height=self.config.rs_height,
            fps=self.config.rs_fps,
            depth_min=self.config.depth_min,
            depth_max=self.config.depth_max,
            depth_color_scheme=self.config.depth_color_scheme,
            depth_histogram_eq=self.config.depth_histogram_eq,
        )

        # 2. UR + FT300 data pipeline (with dynamics + weight)
        self.urft_adapter = URFTAdapter(motor_gains=list(self.config.motor_gains))
        self.urft_adapter.configure_callbacks(
            status_cb=self._status, error_cb=self._error
        )

        # 3. Excel recorder (CSV real-time, xlsx on stop)
        self.excel_recorder = ExcelRecorder()

        # Start camera first (so meta.csv is ready)
        try:
            self.rs_adapter.start(self.session_dir)
            self._status("RealSense相机录制已启动")
        except Exception as exc:
            self._error(f"RealSense启动失败: {exc}")
            self.rs_adapter = None

        # Start UR+FT pipeline
        self.urft_adapter.start(
            session_dir=self.session_dir,
            ur_ip=self.config.ur_ip,
            ur_port=self.config.ur_port,
            ft_port=self.config.ft_port,
            ft_baud=self.config.ft_baud,
            ft_slave=self.config.ft_slave,
        )

        self._status(f"采集会话已启动: {self.session_dir}")
        return self.session_dir

    def stop_session(self, normal_stop: bool = True) -> None:
        """Stop all adapters and finalize Excel output."""
        if self.urft_adapter is not None:
            self.urft_adapter.stop()
        if self.rs_adapter is not None:
            self.rs_adapter.stop()

        # Finalize Excel from CSV (URFTAdapter writes the CSV)
        if self.excel_recorder is not None and self.urft_adapter is not None:
            csv_path = self.urft_adapter.csv_path
            sample_count = self.urft_adapter.sample_count
            weight_hist = self.urft_adapter.weight_calc.weight_history
            if csv_path and csv_path.exists():
                self.excel_recorder.finalize(
                    session_dir=self.session_dir,
                    csv_path=csv_path,
                    sample_count=sample_count,
                    weight_history=weight_hist,
                )

        self._write_session_metadata(normal_stop=normal_stop)
        self._status("采集会话已停止")

    def _write_session_metadata(self, normal_stop: bool) -> None:
        if self.session_dir is None:
            return

        # Copy RealSense meta.csv -> camera_meta.csv for consistency
        meta_csv = self.session_dir / "meta.csv"
        camera_meta_csv = self.session_dir / "camera_meta.csv"
        if meta_csv.exists() and not camera_meta_csv.exists():
            try:
                shutil.copyfile(meta_csv, camera_meta_csv)
            except Exception:
                pass

        stats = self.urft_adapter.get_stats() if self.urft_adapter is not None else {}
        weight_hist = []
        if self.urft_adapter is not None:
            weight_hist = self.urft_adapter.weight_calc.weight_history

        lines = [
            f"start_datetime: {self.start_time.isoformat(sep=' ', timespec='seconds') if self.start_time else 'unknown'}",
            f"stop_datetime: {datetime.now().isoformat(sep=' ', timespec='seconds')}",
            f"normal_stop: {'yes' if normal_stop else 'no'}",
            f"session_dir: {self.session_dir}",
            f"ur_ip: {self.config.ur_ip}",
            f"ur_port: {self.config.ur_port}",
            f"ft_port: {self.config.ft_port}",
            f"ft_baud: {self.config.ft_baud}",
            f"ft_slave: {self.config.ft_slave}",
            f"rs_width: {self.config.rs_width}",
            f"rs_height: {self.config.rs_height}",
            f"rs_fps: {self.config.rs_fps}",
            f"sample_count: {stats.get('sample_count', 0)}",
            f"csv_path: {stats.get('csv_path', '')}",
            f"errors: {' | '.join(stats.get('errors', [])) if stats.get('errors') else (self.last_error or 'none')}",
            f"shovel_tare_Fz: {self.urft_adapter.weight_calc.shovel_tare_Fz if self.urft_adapter else 0.0}",
            f"weight_records: {weight_hist}",
        ]
        (self.session_dir / "session_metadata.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def get_preview(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Return (rgb_bgr, depth_bgr) latest camera frames."""
        if self.rs_adapter is None:
            return None, None
        return self.rs_adapter.get_latest_preview()

    def update_depth_colorizer(
        self,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        color_scheme: Optional[int] = None,
        histogram_eq: Optional[bool] = None,
    ) -> None:
        if self.rs_adapter is not None:
            self.rs_adapter.update_depth_colorizer(
                min_distance=min_distance,
                max_distance=max_distance,
                color_scheme=color_scheme,
                histogram_eq=histogram_eq,
            )

    def is_recording(self) -> bool:
        return bool(
            self.rs_adapter is not None and self.rs_adapter.is_recording
        )

    def get_runtime_stats(self) -> Dict[str, Any]:
        if self.session_dir is None:
            return {
                "session_dir": "-",
                "sample_count": 0,
                "errors": [],
                "last_error": self.last_error,
                "weight_g": 0.0,
                "Fz_world": 0.0,
                "shovel_tare_Fz": 0.0,
            }

        stats = self.urft_adapter.get_stats() if self.urft_adapter else {}
        weight_info = {
            "weight_g": self.urft_adapter.weight_calc.current_weight_g if self.urft_adapter else 0.0,
            "Fz_world": self.urft_adapter.weight_calc.current_Fz_world if self.urft_adapter else 0.0,
            "shovel_tare_Fz": self.urft_adapter.weight_calc.shovel_tare_Fz if self.urft_adapter else 0.0,
            "last_recorded_weight_g": self.urft_adapter.weight_calc.last_recorded_weight_g if self.urft_adapter else 0.0,
            "last_recorded_time": self.urft_adapter.weight_calc.last_recorded_time if self.urft_adapter else "",
            "is_stable": self.urft_adapter.weight_calc.is_stable if self.urft_adapter else False,
            "tare_in_progress": self.urft_adapter.is_tare_in_progress() if self.urft_adapter else False,
            "tare_progress": self.urft_adapter.tare_progress() if self.urft_adapter else 0.0,
            "csv_writing_enabled": stats.get("csv_writing_enabled", False),
        }

        return {
            "session_dir": str(self.session_dir),
            "sample_count": stats.get("sample_count", 0),
            "errors": stats.get("errors", []),
            "last_error": self.last_error,
            **weight_info,
        }
