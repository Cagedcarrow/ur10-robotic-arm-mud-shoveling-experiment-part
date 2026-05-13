# 本次任务总结

## 1. 任务目标

将 `ur10_assembly_real_control` 的真实 UR10 控制链路对齐 Universal Robots ROS2 Driver 官方结构：UR10 本体由 `ur_description` 官方 `ur_robot` 宏生成，保留本项目底座与铲斗末端，避免 driver、MoveIt、RViz 使用不同 `robot_description` 导致 TF 树分裂和执行链路不一致。

## 2. 根因分析

原模型在 `assembly_real.urdf.xacro` 中手写了 UR10 链路、关节、transmission 和 Gazebo/ROS1 控制分支，而 driver 启动时又使用官方 `ur_control.launch.py` 的 UR 描述。这导致真实 driver 的 TF/control 语义是官方 `base_link -> tool0`，MoveIt/RViz 侧却是自定义 `ur10 -> ur10_shoulder -> ... -> sensor_shovel_tcp`。GUI 还会在启动 MoveIt 前杀掉 driver 的 `robot_state_publisher`，进一步破坏官方 driver 发布的 TF 链。

## 3. 修改文件清单

- `config/assembly_real.urdf.xacro`
- `config/assembly_real.srdf`
- `config/ur10/joint_limits.yaml`
- `config/ur10/default_kinematics.yaml`
- `config/ur10/physical_parameters.yaml`
- `config/ur10/visual_parameters.yaml`
- `urdf/assembly_real.urdf.xacro`
- `launch/include/ur_driver_bringup.launch.py`
- `launch/ur10_assembly_real.launch.py`
- `scripts/real_control_gui.py`
- `scripts/check_real_ur10_ready.sh`
- `CMakeLists.txt`
- `package.xml`

## 4. 新增功能

- 新增官方 driver 可加载的 `urdf/assembly_real.urdf.xacro` 入口。
- 新增本包 `config/ur10/` 官方 UR10 参数副本，使 `ur_control.launch.py` 使用 `description_package:=ur10_assembly_real_control` 时可以找到 joint/physical/visual/kinematics 参数。
- 新增 `launch_rsp` 参数，默认不启动第二个 `robot_state_publisher`，避免与官方 driver RSP 冲突。

## 5. 核心实现逻辑

- `assembly_real.urdf.xacro` 删除手写 UR10 本体，改为包含 `$(find ur_description)/urdf/ur_macro.xacro` 并调用 `<xacro:ur_robot>`。
- 官方 UR10 挂载到原底座安装链接 `base_jizuo_base_ur10_with_dizuo`。
- 原底座 `base_jizuo`、`base_jizuo_base_ur10_with_dizuo`、铲斗 `sensor_shovel`、TCP `sensor_shovel_tcp` 保留。
- 铲斗固定接到官方 `tool0`，SRDF planning group 改为 `base_link -> sensor_shovel_tcp`。
- Driver 启动命令显式传入 `description_package:=ur10_assembly_real_control`、`description_file:=assembly_real.urdf.xacro`、`initial_joint_controller:=scaled_joint_trajectory_controller`。
- GUI 启动 MoveIt 时不再杀 `robot_state_publisher`，MoveIt launch 使用相同 assembly 描述且 `launch_rsp:=false`。
- RTDE overflow readiness 检测不再读取历史 `docs/task_logs/5_10.md`，只检查最近 ROS log，避免历史 overflow 阻塞新 driver 会话。

## 6. 执行命令

```bash
git status --short
cp /root/ur10_ws/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro /root/ur10_ws/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro.bak_20260510_123120
cp /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py.bak_20260510_123120
python3 -m py_compile /root/ur10_ws/src/ur10_assembly_real_control/scripts/real_control_gui.py
bash -n /root/ur10_ws/src/ur10_assembly_real_control/scripts/check_real_ur10_ready.sh
cd /root/ur10_ws && source /opt/ros/humble/setup.bash && colcon build --packages-select ur10_assembly_real_control --symlink-install
source /opt/ros/humble/setup.bash && source /root/ur10_ws/install/setup.bash && ros2 run xacro xacro /root/ur10_ws/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro ur_type:=ur10 robot_ip:=192.168.1.10 > /tmp/assembly_real.urdf
check_urdf /tmp/assembly_real.urdf
ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py --show-args
cd /root/ur10_ws && source /opt/ros/humble/setup.bash && source install/setup.bash && timeout 12s ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py robot_ip:=192.168.1.10 launch_driver:=false launch_rsp:=true launch_rviz:=false
```

## 7. 测试结果

- Python 语法检查通过。
- readiness shell 脚本语法检查通过。
- `colcon build --packages-select ur10_assembly_real_control --symlink-install` 通过。
- xacro 展开通过。
- `check_urdf` 通过，树结构为 `base_jizuo -> base_jizuo_base_ur10_with_dizuo -> base_link -> ... -> tool0 -> sensor_shovel -> sensor_shovel_tcp`。
- `ros2 launch ... --show-args` 通过。
- 离线 MoveIt/RSP 启动通过，日志出现 `You can start planning now!`。
- 静态确认当前有效 xacro/SRDF/launch/GUI 中不再包含 `ur10_shoulder`、`GazeboSystem`、`gazebo_ros_control`。

## 8. 剩余问题

- 离线启动仍有 KDL 根链接惯性 warning：`base_jizuo` 是 URDF root 且带 inertial。该 warning 不阻塞 MoveIt 启动，后续可通过增加 dummy `world` root 单独清理。
- 离线 MoveIt 无 3D sensor plugin 的 warning 属于常规 octomap 配置缺省，不影响当前执行链路修复。
- 本轮未连接真实 UR10 执行轨迹，真实 RTDE overflow 是否消失需要在实机低速小范围运动中验证。
- 如果 driver 仍报 calibration mismatch，需要用 `ur_calibration` 从真实控制柜提取 calibration，再替换 `config/ur10/default_kinematics.yaml`。

## 9. 下一步建议

- 真机启动 GUI 后先点 driver，再点 verify，确认 controller active、action online、speed scaling nonzero、RTDE_OK。
- RViz 中只做 `Start State = Current` 的极小 joint-space 规划，先不要执行大范围路径。
- 单独清理 `base_jizuo/base_link` TF 根结构和 KDL root inertia warning。
- 使用 `ur_calibration` 提取真实 UR10 calibration。
- 如果继续出现 `Pipeline producer overflowed`，重点检查 WSL2 CPU 占用、网络延迟、防火墙、端口转发、External Control 程序和是否存在第二个 RTDE client。

## 10. 追加修正：RTDE overflow 下允许打开 RViz/MoveIt 做 Plan-only

验证日志显示 `JOINT_STATES_OK`、`CONTROLLER_ACTIVE`、`ACTION_ONLINE`、`SPEED_SCALING_NONZERO` 均已通过，阻塞 `READY_FOR_RVIZ2_MOVEIT_EXECUTION` 的唯一硬条件是当前 driver 会话持续出现 `Pipeline producer overflowed! <RTDE Data Pipeline>`。

因此 GUI 改为两级判断：

- `READY_FOR_RVIZ2_MOVEIT_EXECUTION` 仍必须满足 RTDE_OK，RTDE overflow 时不能显示 READY，也不建议 Execute。
- `MOVEIT_RVIZ_PLAN_ONLY_OK` 只要求 joint states、scaled controller、action server、speed scaling 在线，用于允许打开 RViz2/MoveIt2 查看模型和做 Plan。

这不会把 RTDE overflow 降级为 warning；它仍然是 Execute 硬失败。该修改只避免 RTDE 不稳定时连 RViz2/MoveIt2 可视化都无法打开。

## 11. 追加修正：UR10 与龙门架安装旋转

用户反馈官方 UR10 替换后，UR10 基座与龙门架连接处安装位置不对。复查原始 `ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro` 后发现，原 `base_jizuo-ur10` 固定关节虽然带有 `quat_xyzw="0 0 0.70710678 0.70710678"`，但标准 URDF `origin` 不支持 `quat_xyzw` 属性，ROS 实际生效的是 `rpy="0 0 0"`。

上一轮迁移时误把该无效 quaternion 当作 90 度 yaw 应用到了官方 `ur_robot` 挂载 origin，导致官方 `base_link` 相对 `base_jizuo_base_ur10_with_dizuo` 旋转错误。

已将 `assembly_real.urdf.xacro` 中官方 UR10 挂载改为：

```xml
<origin xyz="0 0 0" rpy="0 0 0" />
```

验证：

```bash
ros2 run xacro xacro /root/ur10_ws/src/ur10_assembly_real_control/config/assembly_real.urdf.xacro ur_type:=ur10 robot_ip:=192.168.1.10 > /tmp/assembly_real_fixed_mount.urdf
check_urdf /tmp/assembly_real_fixed_mount.urdf
colcon build --packages-select ur10_assembly_real_control --symlink-install
```

结果：xacro 展开、URDF 检查、包构建均通过。

## 12. 追加修正：铲子安装姿态

用户反馈铲子姿态错误。复查原始 `ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro` 中 `ur10-sensor_shovel` 固定关节：

```xml
<origin xyz="0 0.09 0" rpy="-1.5707963 0 0" quat_xyzw="-0.5 0.5 0.5 0.5" />
```

标准 URDF 不支持 `quat_xyzw`，但该字段表达的姿态明显来自原 CAD/转换结果。为让 RViz/MoveIt 真正使用该意图，将 quaternion `[-0.5, 0.5, 0.5, 0.5]` 转换为标准 URDF RPY：

```xml
<origin xyz="0 0.09 0" rpy="-1.57079632679 1.57079632679 0" />
```

当前铲子仍挂到官方 `tool0`，因为官方 UR10 链中 `wrist_3_link -> flange -> tool0` 的净旋转近似为单位变换，可保持原 wrist_3 安装语义。

验证：xacro 展开、`check_urdf`、`colcon build --packages-select ur10_assembly_real_control --symlink-install` 均通过。
