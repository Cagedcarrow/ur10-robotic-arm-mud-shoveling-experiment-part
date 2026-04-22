# ur10_with_shovel Runbook

本包提供 UR10 + 铲子末端（`shovel_tip`）的一体化路径规划配置：
- Gazebo + MoveIt2 仿真可直接跑通
- 真实 UR10 通信接口文件和启动入口已预留（默认不强制联调）
- 规划末端 TCP 默认使用 `shovel_tip`

## 1. 环境准备与编译

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
colcon build --packages-up-to ur10_moveit_config ur10_with_shovel
source install/setup.bash
```

URDF 快速检查：

```bash
xacro src/ur10_with_shovel/urdf/ur10_shovel.urdf.xacro > /tmp/shovel.urdf
check_urdf /tmp/shovel.urdf
```

## 1a. 姿态校准版本说明（与附件基准逐项对齐）

本文件当前版本为“姿态与连接校准”阶段，仅做机械臂-铲子连接对齐，不承诺与现有 MoveIt 主线链路的命名兼容。

- 基准来源：`/root/ur10_ws/src/my_robot_xacro (1)/my_robot/my_robot.urdf.xacro` 与 `ur10_shovel.urdf`
- 覆盖对象：末端两处固定关节与铲/铲尖参数
- 对齐目标1（`ur10-robot`）：`parent="ur10_wrist_3"`，`child="铲子"`，`origin xyz="0 0.105 0"`，`origin rpy="1.5707963 0 -1.5707963"`
- 对齐目标2（`wrist_3_to_shovel_tip`）：`parent="ur10_wrist_3"`，`child="shovel_tip"`，`origin xyz="-0.00318 0.15268 0.47736"`，`origin rpy="1.2194 -0.0628 -0.0628"`
- 链条参数：`ur10 -> ur10_shoulder -> ... -> ur10_wrist_3` 的 link/joint 名称、惯性、mesh、origin 按照 my_robot 链逐项复刻
- 铲子参数：`meshes/base_link.STL`、惯量与惯性参数、`ur10-robot` 安装位姿与基准一致；`shovel_tip` 保持当前基准姿态数值

可执行一致性自检（建议）：

```bash
xacro src/ur10_with_shovel/urdf/ur10_shovel.urdf.xacro > /tmp/shovel_calib.urdf
grep -n 'name=\"ur10-robot\"\\|name=\"wrist_3_to_shovel_tip\"\\|name=\"ur10_wrist_3\"' /tmp/shovel_calib.urdf
```

## 2. 仿真一键启动（推荐）

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10_with_shovel sim_planning_shovel.launch.py
```

默认行为：
- 启动 Gazebo
- 加载 `joint_state_broadcaster` 与 `joint_trajectory_controller`
- 启动 MoveIt2 `move_group`
- 启动 RViz MotionPlanning
- 规划末端 TCP 为 `shovel_tip`

常用参数：

```bash
ros2 launch ur10_with_shovel sim_planning_shovel.launch.py start_rviz:=true use_sim_time:=true
```

## 3. 在 RViz 中通过目标点进行运动规划（以铲尖为基准）

启动后在 RViz 的 **MotionPlanning** 面板操作：

1. 选择规划组：`ur_manipulator`
2. 在场景中拖动末端交互 Marker（即铲尖目标）
3. 点击 `Plan`
4. 观察轨迹预览
5. 点击 `Execute` 发送到 Gazebo 控制器

建议先验证 3 个目标点：
- 点 A：仅沿 X 正方向小位移
- 点 B：仅沿 Z 方向抬高
- 点 C：在 B 基础上增加姿态旋转

如果 `Plan` 失败，优先检查：
- 目标是否超出可达空间
- 是否出现自碰/场景碰撞
- 控制器是否 active

## 4. 关键状态检查与排错命令

```bash
# 控制器状态
ros2 control list_controllers

# 关节状态刷新
ros2 topic hz /joint_states

# MoveIt动作接口
ros2 action list | rg follow_joint_trajectory

# TF中是否有铲尖坐标
ros2 run tf2_ros tf2_echo base_link shovel_tip
```

语义（SRDF）加载检查（重点用于确认碰撞豁免规则已生效）：

```bash
# 先确保只启用 ur10_with_shovel 主线，避免连接到旧 move_group
pkill -9 -f "move_group|rviz2|ros2_control_node|spawner|robot_state_publisher" || true

# 启动纯 MoveIt + RViz(fake hardware，无Gazebo)
ros2 launch ur10_with_shovel moveit_rviz_fake_hardware.launch.py start_rviz:=false
```

另开终端查询：

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
ros2 param get /move_group robot_description_semantic | rg "disable_collisions|wrist_3_link|铲子|shovel_tip"
```

## 5. 真实 UR10 通信接口（预留，默认不强制执行）

已提供模板文件：
- `src/ur10_with_shovel/config/real_robot.env.example`
- `src/ur10_with_shovel/config/real_robot_network.yaml`

请按你的网络修改：
- `ROBOT_IP`
- `REVERSE_IP`
- 网卡名与端口

实机接口启动入口（驱动 + MoveIt，默认仅准备通信/规划链路）：

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10_with_shovel real_robot_interface_shovel.launch.py \
  robot_ip:=192.168.56.101 reverse_ip:=192.168.56.1 launch_rviz:=true
```

> 安全建议：首次接实机前，先在仿真验证同一目标点流程；实机先低速、小范围、空载测试。

## 6. 单独启动入口说明

仅 Gazebo：

```bash
ros2 launch ur10_with_shovel gazebo_shovel.launch.py
```

仅 MoveIt（依赖你已有机器人状态源）：

```bash
ros2 launch ur10_with_shovel moveit_shovel.launch.py planning_tip_link:=shovel_tip sim_gazebo:=true
```

纯模型可视化：

```bash
ros2 launch ur10_with_shovel view_shovel_rviz.launch.py
```

## 7. 铲子与本体碰撞策略（当前默认）

当前仅豁免你明确允许的安装重叠碰撞：
- `wrist_3_link` ↔ `铲子`
- `铲子` ↔ `shovel_tip`（固定相邻）

不会放宽以下碰撞：
- `铲子` 与 `wrist_2_link` / `wrist_1_link` / `forearm_link` 等其余连杆

这保证了：
- 安装处误报不影响规划
- 非安装区域的真实干涉仍可被 MoveIt 阻止
