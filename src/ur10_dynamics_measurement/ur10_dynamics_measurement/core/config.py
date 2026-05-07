from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class MeasurementConfig:
    topic_joint_states: str = "/joint_states"
    topic_ft_data: str = "io_and_status_controller/ft_data"
    topic_speed_scaling: str = "io_and_status_controller/speed_scaling"

    joint_names: List[str] = field(default_factory=lambda: [
        "shoulder_pan_joint",
        "shoulder_lift_joint",
        "elbow_joint",
        "wrist_1_joint",
        "wrist_2_joint",
        "wrist_3_joint",
    ])

    motor_gains: List[float] = field(default_factory=lambda: [
        13.5841, 14.2959, 11.3716,
        11.2408, 11.7681, 11.7682,
    ])  # Nm/A, from codeocean ur10_inverse_dynamics_solver

    ft_tare_samples: int = 100

    data_root: Path = field(
        default_factory=lambda: Path.home() / "ur10_measurement_data"
    )

    plot_window: int = 300  # number of points in rolling plot buffer
    ros_spin_interval_ms: int = 20   # 50 Hz
    plot_refresh_interval_ms: int = 50  # 20 Hz
