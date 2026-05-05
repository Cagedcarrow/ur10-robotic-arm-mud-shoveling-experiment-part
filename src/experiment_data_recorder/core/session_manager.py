from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from typing import Callable, Optional

from .config import RecorderConfig
from .path_utils import create_timestamp_dir
from .realsense_adapter import RealSenseAdapter
from .ur_ft_adapter import URFTAdapter


class SessionManager:
    def __init__(self) -> None:
        self.config = RecorderConfig()
        self.rs_adapter: Optional[RealSenseAdapter] = None
        self.urft_adapter: Optional[URFTAdapter] = None
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

    def start_session(self, config: RecorderConfig) -> Path:
        self.config = config
        self.last_error = ""
        self.start_time = datetime.now()
        self.session_dir = create_timestamp_dir(self.config.data_root)

        self.rs_adapter = RealSenseAdapter(
            width=self.config.rs_width,
            height=self.config.rs_height,
            fps=self.config.rs_fps,
            depth_min=self.config.depth_min,
            depth_max=self.config.depth_max,
            depth_color_scheme=self.config.depth_color_scheme,
            depth_histogram_eq=self.config.depth_histogram_eq,
        )
        self.urft_adapter = URFTAdapter()
        self.urft_adapter.configure_callbacks(status_cb=self._status, error_cb=self._error)

        try:
            self.rs_adapter.start(self.session_dir)
            self.urft_adapter.start(
                session_dir=self.session_dir,
                ur_ip=self.config.ur_ip,
                ur_port=self.config.ur_port,
                ft_port=self.config.ft_port,
                ft_baud=self.config.ft_baud,
                ft_slave=self.config.ft_slave,
            )
        except Exception as exc:
            self._error(f"启动失败: {exc}")
            self.stop_session(normal_stop=False)
            raise

        self._status(f"采集会话已启动: {self.session_dir}")
        return self.session_dir

    def stop_session(self, normal_stop: bool = True) -> None:
        if self.urft_adapter is not None:
            self.urft_adapter.stop()
        if self.rs_adapter is not None:
            self.rs_adapter.stop()

        self._write_session_metadata(normal_stop=normal_stop)
        self._status("采集会话已停止")

    def _write_session_metadata(self, normal_stop: bool) -> None:
        if self.session_dir is None:
            return

        meta_csv = self.session_dir / "meta.csv"
        camera_meta_csv = self.session_dir / "camera_meta.csv"
        if meta_csv.exists() and not camera_meta_csv.exists():
            try:
                shutil.copyfile(meta_csv, camera_meta_csv)
            except Exception:
                pass

        stats = self.urft_adapter.get_stats() if self.urft_adapter is not None else {}
        text = [
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
        ]
        (self.session_dir / "session_metadata.txt").write_text("\n".join(text) + "\n", encoding="utf-8")

    def get_preview(self):
        if self.rs_adapter is None:
            return None, None
        return self.rs_adapter.get_latest_preview()

    def update_depth_colorizer(
        self,
        min_distance: float | None = None,
        max_distance: float | None = None,
        color_scheme: int | None = None,
        histogram_eq: bool | None = None,
    ) -> None:
        if self.rs_adapter is not None:
            self.rs_adapter.update_depth_colorizer(
                min_distance=min_distance,
                max_distance=max_distance,
                color_scheme=color_scheme,
                histogram_eq=histogram_eq,
            )

    def is_recording(self) -> bool:
        return bool(self.rs_adapter is not None and self.rs_adapter.is_recording)

    def get_runtime_stats(self) -> dict:
        if self.session_dir is None:
            return {"session_dir": "-", "sample_count": 0, "errors": [], "last_error": self.last_error}
        stats = self.urft_adapter.get_stats() if self.urft_adapter else {}
        return {
            "session_dir": str(self.session_dir),
            "sample_count": stats.get("sample_count", 0),
            "errors": stats.get("errors", []),
            "last_error": self.last_error,
        }
