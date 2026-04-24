"""Configuration schema for UR10 unified GUI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict


@dataclass
class UnifiedGUIConfig:
    mode: str = "Real"

    # Real mode
    host_ip: str = "192.168.56.1"
    robot_ip: str = "192.168.56.101"
    robot_subnet: str = "192.168.56.0/24"
    reverse_ip: str = ""
    wrist3_delta: str = "0.5"
    controller: str = "scaled_joint_trajectory_controller"
    status_timeout: str = "600"

    # Sim mode
    ur_type: str = "ur10"
    use_fake_hardware: str = "false"
    world: str = "/root/ur10_ws/src/ur10_perception/worlds/gantry_only.world"
    start_rviz: str = "true"
    enable_gantry_rviz_control: str = "false"
    start_cpp_demo: str = "false"
    start_py_demo: str = "false"
    start_py_tools: str = "false"

    # UI/logic
    auto_network_check: bool = True

    # paths
    run_full_verify_script: str = "/root/ur10_ws/src/ur10_real_comm/scripts/run_full_verify.sh"
    run_full_verify_wsl_script: str = "/root/ur10_ws/src/docs/ur10_real_comm_实机微动验证总结/run_full_verify_wsl.sh"
    workspace_root: str = "/root/ur10_ws"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "UnifiedGUIConfig":
        merged = {**cls().to_dict(), **{k: v for k, v in data.items() if v is not None}}
        return cls(**merged)
