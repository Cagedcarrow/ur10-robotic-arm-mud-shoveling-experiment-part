from __future__ import annotations

import math
import time
from collections import deque
from typing import Deque, List, Tuple

import numpy as np

GRAVITY = 9.80665  # m/s^2
TARE_COLLECT_SAMPLES = 80       # collect ~80 FT samples for tare averaging
EMA_ALPHA = 0.08                # weight EMA smoothing factor (0 < alpha <= 1)
STABILITY_WINDOW = 30           # samples for stability check


def rotvec_to_matrix(rotvec: np.ndarray) -> np.ndarray:
    """Rodrigues formula: axis-angle -> 3x3 rotation matrix."""
    theta = float(np.linalg.norm(rotvec))
    if theta < 1e-12:
        return np.eye(3)
    axis = rotvec / theta
    skew = np.array([
        [0.0, -axis[2], axis[1]],
        [axis[2], 0.0, -axis[0]],
        [-axis[1], axis[0], 0.0],
    ])
    return np.eye(3) + math.sin(theta) * skew + (1.0 - math.cos(theta)) * (skew @ skew)


class WeightCalculator:
    """Projects FT300 force to world Z-axis and computes mud weight in real-time.

    Improvements over the original:
    - Tare averaging: collects multiple samples to get a stable zero reference.
    - EMA filtering: smooths the weight display to reduce sensor noise.
    - Stability detection: warns when force readings are fluctuating too much.
    """

    def __init__(self, R_tcp_to_sensor: np.ndarray) -> None:
        self.R_tcp_to_sensor = R_tcp_to_sensor

        # Tare values
        self.shovel_tare_Fz: float = 0.0
        self._tare_buffer: List[float] = []  # collects Fz samples during tare
        self._tare_active: bool = False

        # Current values
        self.current_Fz_world: float = 0.0
        self.current_force_base: np.ndarray = np.zeros(3)
        self._raw_weight_g: float = 0.0        # unfiltered
        self.current_weight_g: float = 0.0      # EMA-filtered for display
        self._weight_ema: float = 0.0           # EMA accumulator

        # Stability check
        self._fz_history: Deque[float] = deque(maxlen=STABILITY_WINDOW)
        self.is_stable: bool = False

        # Recording
        self.last_recorded_weight_g: float = 0.0
        self.last_recorded_time: str = ""
        self.weight_history: List[Tuple[str, float]] = []

    def update(self, force_sensor: List[float], tcp_rotvec: List[float]) -> float:
        """Compute Fz in world frame and update weight with EMA filtering."""
        # Step 1: R_base_tcp from TCP axis-angle
        R_base_tcp = rotvec_to_matrix(np.array(tcp_rotvec, dtype=float))

        # Step 2: Sensor frame in base frame
        R_base_sensor = R_base_tcp @ self.R_tcp_to_sensor

        # Step 3: Force in world frame
        F_sensor = np.array(force_sensor, dtype=float)
        self.current_force_base = R_base_sensor @ F_sensor
        self.current_Fz_world = float(self.current_force_base[2])

        # Step 4: Raw weight = delta_Fz / g * 1000
        delta_Fz = self.current_Fz_world - self.shovel_tare_Fz
        self._raw_weight_g = abs(delta_Fz) / GRAVITY * 1000.0

        # Step 5: EMA filter for smooth display
        if self._weight_ema == 0.0 and self.shovel_tare_Fz == 0.0:
            # Not tared yet — just follow raw
            self._weight_ema = self._raw_weight_g
        else:
            self._weight_ema = EMA_ALPHA * self._raw_weight_g + (1.0 - EMA_ALPHA) * self._weight_ema
        self.current_weight_g = self._weight_ema

        # Step 6: Stability check
        self._fz_history.append(self.current_Fz_world)
        if len(self._fz_history) >= STABILITY_WINDOW:
            vals = np.array(self._fz_history)
            std = float(np.std(vals))
            self.is_stable = std < 0.15  # Fz std < 0.15N → stable enough for weighing

        # Step 7: If tare is active, collect sample
        if self._tare_active:
            self._tare_buffer.append(self.current_Fz_world)
            if len(self._tare_buffer) >= TARE_COLLECT_SAMPLES:
                self._finish_tare()

        return self.current_weight_g

    # ---- Tare ----

    def start_tare_shovel(self) -> None:
        """Begin collecting samples for tare averaging."""
        self._tare_buffer.clear()
        self._tare_active = True

    def _finish_tare(self) -> float:
        """Complete tare: compute mean Fz from collected samples."""
        if not self._tare_buffer:
            return self.shovel_tare_Fz
        self.shovel_tare_Fz = float(np.mean(self._tare_buffer))
        self._tare_buffer.clear()
        self._tare_active = False
        # Recompute raw weight with new tare, seed EMA from it
        delta = self.current_Fz_world - self.shovel_tare_Fz
        self._raw_weight_g = abs(delta) / GRAVITY * 1000.0
        self._weight_ema = self._raw_weight_g
        self.current_weight_g = self._weight_ema
        return self.shovel_tare_Fz

    def tare_shovel_immediate(self) -> float:
        """Single-sample tare (fallback when not enough samples available)."""
        self._tare_active = False
        self._tare_buffer.clear()
        self.shovel_tare_Fz = self.current_Fz_world
        # Recompute raw weight with new tare, seed EMA from it
        delta = self.current_Fz_world - self.shovel_tare_Fz
        self._raw_weight_g = abs(delta) / GRAVITY * 1000.0
        self._weight_ema = self._raw_weight_g
        self.current_weight_g = self._weight_ema
        return self.shovel_tare_Fz

    def is_tare_in_progress(self) -> bool:
        return self._tare_active

    def tare_progress(self) -> float:
        """Return 0.0–1.0 progress of tare sample collection."""
        return min(len(self._tare_buffer) / TARE_COLLECT_SAMPLES, 1.0)

    # ---- Recording ----

    def record_weight(self) -> float:
        """Capture current filtered weight into history."""
        ts = time.strftime("%H:%M:%S")
        self.last_recorded_weight_g = self.current_weight_g
        self.last_recorded_time = ts
        self.weight_history.append((ts, self.current_weight_g))
        return self.current_weight_g

    # ---- Reset ----

    def reset(self) -> None:
        self.shovel_tare_Fz = 0.0
        self._tare_buffer.clear()
        self._tare_active = False
        self.current_Fz_world = 0.0
        self.current_force_base = np.zeros(3)
        self._raw_weight_g = 0.0
        self.current_weight_g = 0.0
        self._weight_ema = 0.0
        self._fz_history.clear()
        self.is_stable = False
        self.last_recorded_weight_g = 0.0
        self.last_recorded_time = ""
        self.weight_history = []
