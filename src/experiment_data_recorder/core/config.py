from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RecorderConfig:
    ur_ip: str = "10.160.9.21"
    ur_port: int = 30003
    ft_port: str = "/dev/ttyUSB0"
    ft_baud: int = 19200
    ft_slave: int = 9

    rs_width: int = 640
    rs_height: int = 480
    rs_fps: int = 30

    depth_min: float = 1.25
    depth_max: float = 1.35
    depth_color_scheme: int = 0  # 0=Jet, 1=Gray(NB/FW), 2=Gray(NW/FB), 3=Bio, 4=Cold, 5=Warm, 6=Quantized, 7=Pattern
    depth_histogram_eq: bool = True

    data_root: Path = Path(__file__).resolve().parents[1] / "data"
