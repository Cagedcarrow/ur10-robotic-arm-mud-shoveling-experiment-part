# 本次任务总结

## 1. 任务目标

把 UR10 External Control 真机通讯、ROS2 driver 验证、RViz2/MoveIt2 启动整合到一个 GUI。

## 2. 根因分析

原流程需要多个终端手动启动，容易重复启动 driver、遗漏 `scaled_joint_trajectory_controller` 检查，且参考源码目录可能被整仓构建误覆盖 `/opt/ros/humble` 的正式 driver。

## 3. 修改文件清单

- `ur10_assembly_real_control/scripts/real_control_gui.py`
- `ur10_assembly_real_control/scripts/start_real_control_gui.sh`
- `ur10_assembly_real_control/launch/real_control_gui.launch.py`
- `ur10_assembly_real_control/launch/ur10_assembly_real.launch.py`
- `ur10_assembly_real_control/launch/include/ur_driver_bringup.launch.py`
- `ur10_assembly_real_control/CMakeLists.txt`
- `ur10_assembly_real_control/package.xml`
- `/root/ur10_ws/start_ur10_external_control_gui.sh`
- `/root/ur10_ws/UR10_External_Control_GUI.desktop`
- `/root/Desktop/UR10_External_Control_GUI.desktop`
- `Universal_Robots_ROS2_Driver-main/COLCON_IGNORE`
- `Universal_Robots_Client_Library-master/COLCON_IGNORE`
- `Universal_Robots_ExternalControl_URCap-master/COLCON_IGNORE`

## 4. 新增功能

- GUI 按钮 1：启动官方 `ur_robot_driver` 监听 External Control。
- GUI 验证：检查 `50002`、`/joint_states`、scaled 控制器、FollowJointTrajectory action。
- GUI 验证增强：按 `docs/external_control/UR10_ROS2_WSL2_Checklist.md` 检查 Windows `portproxy` 与 `10.160.9.100:50002 LISTENING`。
- scaled 控制器修正：如果 `/joint_states` 已有但 `scaled_joint_trajectory_controller` 未 active，验证时自动执行 `switch_controllers --activate scaled_joint_trajectory_controller --strict`，失败后再尝试 `load_controller --set-state active scaled_joint_trajectory_controller`。
- GUI 按钮 2：在就绪后启动装配模型 MoveIt2 + RViz2。
- GUI 按钮 3：清理 driver、controller、MoveIt、RViz2 残留进程。
- 一键启动脚本：双击 `/root/ur10_ws/UR10_External_Control_GUI.desktop`、桌面上的 `UR10_External_Control_GUI.desktop`，或运行 `/root/ur10_ws/start_ur10_external_control_gui.sh` 后直接打开 GUI。

## 5. 核心实现逻辑

GUI 使用 PyQt5 管理两个受控 launch 进程。driver 阶段固定启动 `/opt/ros/humble` 的 `ur_robot_driver`，并拒绝非 `/opt/ros/humble` 前缀的 driver。MoveIt 阶段通过 `launch_driver:=false` 复用已经启动的 driver，避免重复占用 RTDE/External Control 端口。当前 `/opt/ros/humble` driver 使用 `use_fake_hardware:=false` 参数。

## 6. 执行命令

```bash
/root/ur10_ws/start_ur10_external_control_gui.sh
```

## 7. 测试结果

- `colcon build --symlink-install --packages-select ur10_assembly_real_control`：通过。
- `xacro .../assembly_real.urdf.xacro > /tmp/assembly_real.urdf && check_urdf /tmp/assembly_real.urdf`：通过。
- `ros2 launch ur10_assembly_real_control real_control_gui.launch.py --show-args`：通过。
- 离线 GUI 启动初测发现 ROS2 自动追加 `--ros-args`，已改为 `parse_known_args()` 兼容。
- `QT_QPA_PLATFORM=offscreen timeout 5s ros2 launch ur10_assembly_real_control real_control_gui.launch.py`：GUI 可启动并保持运行，测试由 timeout 主动结束。
- `ros2 run ur10_assembly_real_control check_real_ur10_ready.sh`：无真机时正确输出 `JOINT_STATES_MISSING`、`CONTROLLER_NOT_ACTIVE`、`ACTION_MISSING`。
- `QT_QPA_PLATFORM=offscreen timeout 5s /root/ur10_ws/start_ur10_external_control_gui.sh`：一键脚本可启动 GUI，测试由 timeout 主动结束。
- Windows 检查可从 WSL 调用 `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`，并能识别当前 `10.160.9.100:50002 -> 172.17.201.231:50002` 与 `10.160.9.100:50002 LISTENING`。
- `docs/error_check/scale_error.md` 显示 scaled switch 已成功，但 `ros2 control list_controllers` 输出含 ANSI 颜色码，旧 grep 误判为 `CONTROLLER_NOT_ACTIVE`；已在 GUI 和 `check_real_ur10_ready.sh` 中先去除 ANSI 后再判断。
- `docs/error_check/rviz2_nowindow.md` 显示 RViz2 崩溃于 PyQt5 Qt 插件路径：`/root/ur10_ws/.venv/.../PyQt5/Qt5/plugins/platforms/...libQt5XcbQpa.so.5`。已在 GUI 启动 ROS 子进程时清理 `QT_PLUGIN_PATH` 和 `QT_QPA_PLATFORM_PLUGIN_PATH`，避免 RViz2 继承 GUI 的 PyQt5 环境；同时 RViz2 launch 输出改为 `screen`，后续错误会直接进入 GUI 日志。
- scaled controller 状态匹配改为“最后一列是 `active`”，避免 `inactive` 字符串包含 `active` 导致误判。
- 修正 `assembly_real.srdf` 中不存在的 `ur10_wrist_*_link`，补回 `shovel_eef_group`，并将铲子末端执行器挂到真实存在的 `wrist_3_joint` 链接，避免 RViz2/MoveIt 启动时 SRDF 链接警告影响 TCP 交互标记。

## 8. 剩余问题

真机连接、Windows portproxy、防火墙和示教器 External Control 点击运行仍需现场硬件配合验证。

## 9. 下一步建议

现场按 GUI 顺序启动，看到 `READY_FOR_RVIZ2_MOVEIT_EXECUTION` 后再在 RViz2 中小范围 Plan/Execute。
