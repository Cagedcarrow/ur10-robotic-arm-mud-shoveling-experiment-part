from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class MudRecorderConfig:
    # UR robot connection (socket, port 30003)
    ur_ip: str = "10.160.9.21"
    ur_port: int = 30003

    # FT300 force/torque sensor (serial Modbus RTU)
    ft_port: str = "/dev/ttyUSB0"
    ft_baud: int = 19200
    ft_slave: int = 9

    # RealSense D435i depth camera
    rs_width: int = 640
    rs_height: int = 480
    rs_fps: int = 30
    depth_min: float = 1.25
    depth_max: float = 1.35
    depth_color_scheme: int = 0  # 0=Jet,1=Gray(NB/FW),2=Gray(NW/FB),3=Bio,4=Cold,5=Warm,6=Quantized,7=Pattern
    depth_histogram_eq: bool = True

    # Motor torque gains K (Nm/A) from codeocean ur10_inverse_dynamics_solver
    motor_gains: List[float] = field(default_factory=lambda: [
        13.5841, 14.2959, 11.3716, 11.2408, 11.7681, 11.7682,
    ])

    # FT300 sensor mounting offset relative to wrist_3 (ur10-sensor_shovel joint)
    # From assembly_xacro: origin rpy="-1.5708 0 0"
    sensor_rpy_offset: List[float] = field(default_factory=lambda: [-1.570796, 0.0, 0.0])

    # TCP offset: sensor_shovel → sensor_shovel_tcp (the UR tool point)
    # From assembly_xacro: origin rpy="-1.5708 1.5708 -0.61087"
    tcp_rpy_offset: List[float] = field(default_factory=lambda: [-1.570796, 1.570796, -0.61087])

    # Data storage root — session dirs created as data/MM_DD_HHMMSS/
    data_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "data")

    # Rolling plot buffer size
    plot_window: int = 300

    # Timer intervals (ms)
    plot_refresh_ms: int = 50    # 20 Hz
    status_refresh_ms: int = 250 # 4 Hz
    preview_refresh_ms: int = 50 # 20 Hz
