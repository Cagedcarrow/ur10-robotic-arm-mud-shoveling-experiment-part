from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

RS_WORKPLACE = Path(__file__).resolve().parents[2] / "intel_realsense" / "work_place"
if str(RS_WORKPLACE) not in sys.path:
    sys.path.insert(0, str(RS_WORKPLACE))

from recorder import RealSenseRecorder  # type: ignore  # noqa: E402


class RealSenseAdapter:
    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        depth_min: float = 1.25,
        depth_max: float = 1.35,
        depth_color_scheme: int = 0,
        depth_histogram_eq: bool = True,
    ) -> None:
        self.recorder = RealSenseRecorder(
            width=width,
            height=height,
            fps=fps,
            depth_min=depth_min,
            depth_max=depth_max,
            depth_color_scheme=depth_color_scheme,
            depth_histogram_eq=depth_histogram_eq,
        )

    def start(self, session_dir: Path) -> None:
        self.recorder.start(session_dir)

    def stop(self) -> None:
        self.recorder.stop()

    def get_latest_preview(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        return self.recorder.get_latest_preview()

    def update_depth_colorizer(
        self,
        min_distance: Optional[float] = None,
        max_distance: Optional[float] = None,
        color_scheme: Optional[int] = None,
        histogram_eq: Optional[bool] = None,
    ) -> None:
        self.recorder.update_depth_colorizer(
            min_distance=min_distance,
            max_distance=max_distance,
            color_scheme=color_scheme,
            histogram_eq=histogram_eq,
        )

    @property
    def is_recording(self) -> bool:
        return bool(self.recorder.is_recording)

    @property
    def last_error(self) -> str:
        return str(self.recorder.last_error or "")
