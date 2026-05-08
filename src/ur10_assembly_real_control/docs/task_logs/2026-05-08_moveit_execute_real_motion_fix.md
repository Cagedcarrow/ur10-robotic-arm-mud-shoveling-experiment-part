# 本次任务总结

## 1. 任务目标

排查 RViz2 中可以拖动铲子 TCP、可以 Plan 并播放动画，但点击 Execute 后真实 UR10 不运动的问题，并修正 GUI/launch 的真实执行检查链路。

## 2. 根因分析

日志显示 MoveIt2 规划成功，第一次 Execute 也已经把轨迹发送给 `scaled_joint_trajectory_controller`：

```text
sending trajectory to scaled_joint_trajectory_controller
scaled_joint_trajectory_controller started execution
Goal request accepted!
```

driver 侧也显示：

```text
scaled_joint_trajectory_controller: Received new action goal
scaled_joint_trajectory_controller: Accepted new action goal
```

后续失败的直接报错是：

```text
Cannot push a new trajectory while another is being executed
```

这说明不是 MoveIt 找不到 controller，而是第一条轨迹一直没有完成。结合当前 WSL2/Windows 检查，Windows 只配置了 `50002` portproxy：

```text
10.160.9.100    50002       172.17.201.231  50002
```

`50002` 只负责 External Control 程序请求；真实运动还需要 driver 的 `50001/50003/50004` 运动反向通道。缺少这些端口映射时，机器人可以请求程序、ROS2 可以读 `/joint_states`，但轨迹命令无法完整闭环到真实机械臂。

另一个必须检查的执行条件是 `speed_scaling`。如果 speed scaling 为 0，controller 会接受 action goal，但机器人不会动，MoveIt 会持续认为上一条轨迹还在执行。

## 3. 修改文件清单

- `ur10_assembly_real_control/scripts/real_control_gui.py`
- `ur10_assembly_real_control/scripts/check_real_ur10_ready.sh`
- `ur10_assembly_real_control/launch/include/ur_driver_bringup.launch.py`
- `ur10_assembly_real_control/launch/ur10_assembly_real.launch.py`
- `docs/external_control/UR10_ROS2_WSL2_Checklist.md`
- `ur10_assembly_real_control/docs/task_logs/2026-05-08_moveit_execute_real_motion_fix.md`

## 4. 新增功能

- GUI driver 启动时显式传入 `reverse_ip:=10.160.9.100`。
- GUI driver 固定真实执行端口：
  - `reverse_port:=50001`
  - `script_sender_port:=50002`
  - `trajectory_port:=50003`
  - `script_command_port:=50004`
- GUI 验证按钮新增：
  - WSL2 `50001/50002/50003/50004` 监听检查
  - Windows `50001/50002/50003/50004` portproxy 检查
  - Windows `50001/50002/50003/50004` LISTENING 检查
  - `speed_scaling` 大于 0 检查
  - `/scaled_joint_trajectory_controller/state` 采样输出
- ready 脚本新增 `SPEED_SCALING_NONZERO` gate，只有 speed scaling 非零时才输出 `READY_FOR_RVIZ2_MOVEIT_EXECUTION`。

## 5. 核心实现逻辑

MoveIt2 动画只表示规划轨迹在 RViz 中可视化；真实执行必须经过：

```text
RViz2 Execute
-> move_group
-> /scaled_joint_trajectory_controller/follow_joint_trajectory
-> ur_robot_driver reverse/trajectory sockets
-> CB3 External Control program
-> true UR10 joint motion
-> /joint_states
-> robot_state_publisher
-> RViz2 current robot state
```

因此 GUI 的验证条件从原来的 `/joint_states + controller + action` 扩展为：

```text
WSL_50002_LISTENING
WSL_MOTION_PORTS_LISTENING
WINDOWS_PORTPROXY_OK
WINDOWS_50002_LISTENING
WINDOWS_MOTION_PORTS_LISTENING
JOINT_STATES_OK
CONTROLLER_ACTIVE
ACTION_ONLINE
SPEED_SCALING_NONZERO
READY_FOR_RVIZ2_MOVEIT_EXECUTION
```

## 6. 执行命令

```bash
python3 -m py_compile ur10_assembly_real_control/scripts/real_control_gui.py
bash -n ur10_assembly_real_control/scripts/check_real_ur10_ready.sh
source /opt/ros/humble/setup.bash
cd /root/ur10_ws
colcon build --symlink-install --packages-select ur10_assembly_real_control
xacro /root/ur10_ws/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro > /tmp/assembly_real_execute_fix.urdf
check_urdf /tmp/assembly_real_execute_fix.urdf
ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py --show-args
```

## 7. 测试结果

- Python GUI 语法检查通过。
- readiness shell 脚本语法检查通过。
- `colcon build --symlink-install --packages-select ur10_assembly_real_control` 通过。
- `xacro` 和 `check_urdf` 通过。
- launch 参数检查通过，`reverse_ip` 已作为 launch 参数暴露，默认值为 `10.160.9.100`。
- 离线运行 GUI 验证命令时，成功检测到当前 Windows 只存在 `50002` portproxy，缺少 `50001/50003/50004`，并输出管理员 PowerShell 修复命令。

## 8. 剩余问题

- 当前环境没有持续运行的 driver/RViz2 节点，无法在本次离线验证中执行真实机械臂运动。
- Windows 端仍需要管理员 PowerShell 权限来重建 `50001/50002/50003/50004` 的 portproxy；WSL2 GUI 只能检测和提示，不能直接提权修改 Windows 管理员配置。
- driver 日志仍有 `Pipeline producer overflowed! <RTDE Data Pipeline>`，需要在四端口 portproxy 修复后再次观察。如果仍大量出现，应继续排查 WSL2 调度/网络负载。

## 9. 下一步建议

先点击 GUI 的“杀死所有相关进程”，然后按 GUI 重新启动 driver。验证页面必须看到四端口映射、speed scaling 非零、controller/action 全部 OK 后，再启动 RViz2 + MoveIt2。第一次 Execute 后等待轨迹完成，不要连续点击 Plan and Execute。
