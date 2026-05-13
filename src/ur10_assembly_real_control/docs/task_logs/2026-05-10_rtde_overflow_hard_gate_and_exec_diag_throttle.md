# 本次任务总结

## 1. 任务目标
降低 UR10 实机 Execute 期间 GUI 对 RTDE 实时通信链路的干扰，并将 RTDE pipeline overflow 从普通日志 warning 升级为 MoveIt 执行 READY 的硬失败条件。

## 2. 根因分析
已有日志显示 MoveIt 规划成功、Execute 请求被接受、`scaled_joint_trajectory_controller` 进入执行阶段，但 driver 侧反复出现 `Pipeline producer overflowed! <RTDE Data Pipeline>`。同时 GUI 在 MoveIt/RViz 启动后每 1 秒反复执行 ROS2 shell 诊断命令，可能在 WSL2 + 实机 RTDE 场景下增加调度和通信负载。

## 3. 修改文件清单
- `ur10_assembly_real_control/scripts/real_control_gui.py`
- `ur10_assembly_real_control/docs/task_logs/2026-05-10_rtde_overflow_hard_gate_and_exec_diag_throttle.md`

未修改 TF/URDF/SRDF/MoveIt controller/launch 配置。

## 4. 新增功能
- 新增 GUI 状态 token：`RTDE_OK`，显示为 `RTDE 链路`。
- 新增 RTDE overflow 关键词检测。
- 检测到 RTDE overflow 后，GUI 设置 `RTDE_OVERFLOW` / `NOT_READY`，并禁止显示执行 READY。
- Execute 期间停止 1 秒循环 shell 诊断，只保留执行前/执行后的一次性 snapshot。

## 5. 核心实现逻辑
- `_contains_rtde_overflow()` 匹配 `Pipeline producer overflowed`、`RTDE Data Pipeline`，以及同时包含 `RTDE` 和 `overflowed` 的日志。
- `_mark_rtde_overflow()` 将 `self.rtde_ok=False`、`self.ready=False`，并更新 `RTDE_OK` 和 `READY_FOR_RVIZ2_MOVEIT_EXECUTION` 标签为失败状态。
- `_is_ready_from_tokens()` 不再因为输出里出现旧的 `READY_FOR_RVIZ2_MOVEIT_EXECUTION` 就直接通过，必须满足 `RTDE_OK` 与现有 controller/action/speed/network 条件。
- `_start_exec_diag_thread()` 保留接口但禁用循环，避免 Execute 期间持续运行 `ros2 control list_controllers`、`ros2 topic echo`、`ros2 action info` 等 subprocess。
- `_runtime_exec_diag_cmd()` 保留为一次性 pre/post snapshot 使用。

## 6. 执行命令
```bash
git -C /root/ur10_ws status
cp /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py.bak_20260510_121213
python3 -m py_compile /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py
cd /root/ur10_ws && source /opt/ros/humble/setup.bash && colcon build --packages-select ur10_assembly_real_control --symlink-install
rg "_start_exec_diag_thread|_runtime_exec_diag_cmd|RTDE_OK|RTDE_OVERFLOW|READY_FOR_RVIZ2_MOVEIT_EXECUTION" /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py
```

## 7. 测试结果
- Python 语法检查：通过。
- ROS2 单包构建：通过，`ur10_assembly_real_control` finished。
- 静态检查：`_start_exec_diag_thread()` 不再包含 1 秒循环 subprocess；Execute 期间只触发 pre/post snapshot。

## 8. 剩余问题
- 当前日志仍提示 `base_jizuo` 与 `base_link` 不在同一 TF tree，本轮未处理。
- 当前日志曾提示 UR calibration mismatch，本轮未处理。
- RTDE overflow 的根因仍可能来自 WSL2 调度、CPU 占用、网络抖动、防火墙、portproxy 或其他 RTDE 客户端/driver 状态。

## 9. 下一步建议
- 单独清理 `base_jizuo` / `base_link` TF 树分裂，统一 planning frame 与 driver/RSP 输出边界。
- 使用 `ur_calibration` 从真实 UR10 提取 calibration，并接入官方 driver description。
- 检查 WSL2 CPU/网络/防火墙/端口转发稳定性，避免 Execute 期间 RTDE 数据管线积压。
- 在真实执行前先重启 driver 并重新验证，确保历史 RTDE overflow 清空后再允许 READY。

## 10. 回退方法
```bash
cp /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py.bak_20260510_121213 /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py
python3 -m py_compile /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py
cd /root/ur10_ws && source /opt/ros/humble/setup.bash && colcon build --packages-select ur10_assembly_real_control --symlink-install
```
