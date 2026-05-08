# 本次任务总结

## 1. 任务目标

修复 RViz2 MotionPlanning 面板中选择 `assembly_manipulator` 或 `shovel_eef_group` 时看不到可自由拖动末端目标球的问题，并让真实规划组的 IK 末端明确指向铲子 TCP。

## 2. 根因分析

直接根因是 `config/moveit.rviz` 中 `Planning Request / Interactive Marker Size` 被配置为 `0`，导致 MotionPlanning 的交互 marker 即使已经启动也不可见。

结构性原因是 `config/assembly_real.srdf` 中 `assembly_manipulator` 只声明了六个关节，没有声明从机械臂基座到 `sensor_shovel_tcp` 的 chain。这样 MoveIt2 对末端 tip 的理解不够明确，不利于在 RViz2 中把可拖动目标放到铲子 TCP。

`shovel_eef_group` 是末端执行器 link 组，不是应当用于拖动规划的机械臂规划组。实际拖动和执行应选择 `assembly_manipulator`。

## 3. 修改文件清单

- `ur10_assembly_real_control/config/moveit.rviz`
- `ur10_assembly_real_control/config/assembly_real.srdf`
- `ur10_assembly_real_control/docs/task_logs/2026-05-08_moveit_tcp_interactive_marker_fix.md`

## 4. 新增功能

- RViz2 MotionPlanning 目标交互 marker 恢复为可见尺寸。
- `assembly_manipulator` 明确声明为 `ur10 -> sensor_shovel_tcp` 的运动链，使铲子 TCP 成为规划组 tip。

## 5. 核心实现逻辑

`moveit.rviz` 中将：

```yaml
Interactive Marker Size: 0
```

改为：

```yaml
Interactive Marker Size: 0.22
```

`assembly_real.srdf` 中将 `assembly_manipulator` 从六关节枚举改为：

```xml
<group name="assembly_manipulator">
  <chain base_link="ur10" tip_link="sensor_shovel_tcp"/>
</group>
```

六个真实执行关节仍由 controller 和 group_state 约束，不改变 driver 或控制器链路。

## 6. 执行命令

```bash
xmllint --noout ur10_assembly_real_control/config/assembly_real.srdf
source /opt/ros/humble/setup.bash
xacro /root/ur10_ws/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro > /tmp/assembly_real_tcp_marker.urdf
check_urdf /tmp/assembly_real_tcp_marker.urdf
cd /root/ur10_ws
colcon build --symlink-install --packages-select ur10_assembly_real_control
timeout --kill-after=3s 14s bash -lc 'unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH; source /opt/ros/humble/setup.bash; source install/setup.bash; ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py robot_ip:=10.160.9.21 ur_type:=ur10 launch_driver:=false launch_rviz:=true'
```

## 7. 测试结果

- `xmllint` 通过。
- `xacro` 生成 URDF 成功。
- `check_urdf` 成功解析，链路为 `base_jizuo -> ... -> wrist_3_joint -> sensor_shovel -> sensor_shovel_tcp`。
- `colcon build --symlink-install --packages-select ur10_assembly_real_control` 通过。
- 短时启动 MoveIt2/RViz2 成功，日志显示：
  - `Ready to take commands for planning group assembly_manipulator.`
  - `Connected on namespace: /rviz_moveit_motion_planning_display/robot_interaction_interactive_marker_topic`
  - `Service response received for initialization`

## 8. 剩余问题

- `base_jizuo` 作为 URDF root link 仍带 inertia，KDL 会输出警告，但目前不阻塞规划和 RViz2 marker。
- RViz2 中应选择 `assembly_manipulator` 作为 Planning Group；`shovel_eef_group` 只表示末端 link 组，不适合作为机械臂运动规划组。

## 9. 下一步建议

真机联调时按 GUI 流程先确认 `READY_FOR_RVIZ2_MOVEIT_EXECUTION`，再打开 RViz2。进入 MotionPlanning 后选择 `assembly_manipulator`，设置 `Start State = Current`，小幅拖动铲子 TCP 目标球，先 Plan，再 Execute。
