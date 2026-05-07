from __future__ import annotations

from typing import List, Optional

import numpy as np

from .kinematics import UR10Kinematics


class DynamicsEstimator:
    """Estimates joint torques from motor currents and FT300 wrench."""

    def __init__(self, motor_gains: List[float]) -> None:
        """Initialize with motor gain constants.

        Args:
            motor_gains: 6-element list of K gains (Nm/A) for each joint.
        """
        self.K = np.array(motor_gains, dtype=float)
        self.kinematics: Optional[UR10Kinematics] = None

    def ensure_kinematics(self) -> UR10Kinematics:
        """Lazy-init kinematics solver."""
        if self.kinematics is None:
            self.kinematics = UR10Kinematics()
        return self.kinematics

    def estimate_joint_torques(self, currents: List[float]) -> np.ndarray:
        """Convert motor currents to estimated joint torques.

        tau_joint[i] = K_gains[i] * I[i]
        """
        I = np.array(currents, dtype=float)
        return self.K * I

    def compute_ft_joint_torques(
        self,
        q: List[float],
        force: List[float],
        torque: List[float],
    ) -> np.ndarray:
        """Map FT300 wrench to equivalent joint torques via Jacobian transpose.

        Returns 6-element array of joint torques (Nm).
        """
        kin = self.ensure_kinematics()
        return kin.compute_ft_joint_torques(q, force, torque)

    def compute_residual(
        self,
        tau_estimated: np.ndarray,
        tau_ft: np.ndarray,
    ) -> np.ndarray:
        """Delta_tau = tau_estimated - tau_ft (Nm)."""
        return tau_estimated - tau_ft
