# 龙门架 UR10 智能作业系统

## 1. 项目简介
本工程基于 Ubuntu 22.04 + ROS2 Humble，面向“龙门架三轴定位 + UR10 六轴作业 + 末端铲子围桶轨迹任务”。
主线目标是形成一条可运行、可维护、可扩展的一键集成链路：Gazebo 仿真、MoveIt2 规划、RViz2 可视化、PyQt5 GUI 控制、DP-RRT 轨迹规划与执行。

## 2. 系统架构
主线包固定为：

- `my_robot`：Gantry + UR10 + shovel_tip 机器人模型与 ros2_control 控制器配置
- `my_robot_moveit_config`：仅 UR10 六轴 MoveIt2 规划配置（Gantry 不进 MoveIt 采样空间）
- `ur10_trajectory_planner`：DP-RRT、轨迹生成、姿态拟合、demo/moveit 双模式执行
- `ur10_bringup`：统一一键启动入口 `full_system.launch.py`
- `ur10_unified_gui`：PyQt5 GUI（3+6 轴控制 + 桶参数 + 规划/执行操作）

## 3. 功能包分层
### 核心主线包
- `my_robot`
- `my_robot_moveit_config`
- `ur10_trajectory_planner`
- `ur10_bringup`
- `ur10_unified_gui`

### 辅助包
- `ur10_simulation_bringup`（历史仿真编排入口，仍可单独使用）
- `ur10_examples`、`ur10_examples_py`（示例控制/调试节点）
- `ur10_perception`（world、相机、点云相关）
- `ur10_real_comm`（实机通信与验证）
- `FT300/ft300_gui_ros2`（力传感器 GUI）

### 历史/保留包
- `ur10_with_shovel`、`ur10_description`、`ur10_moveit_config`
- `FT300/my_robotiq_force_torque_sensor-master`（ROS1）
- `轨迹构建与拟合说明文档`（文档与模板保留，不作为主线运行入口）

## 4. 模型组成
### 4.1 龙门架
- 关节：`gantry_x_joint`、`gantry_y_joint`、`gantry_z_joint`
- 作用：整体定位，不进入 MoveIt2 采样空间

### 4.2 UR10 机械臂
- 关节：`ur10_shoulder_pan`、`ur10_shoulder_lift`、`ur10_elbow`、`ur10_wrist_1_joint`、`ur10_wrist_2_joint`、`ur10_wrist_3_joint`
- 作用：末端作业与轨迹执行

### 4.3 末端铲子
- link：`shovel_link`、`shovel_tip`
- 用于围桶入桶、桶内作业、抬升退出任务

### 4.4 圆柱桶
- 参数：`bucket_center_x/y/z`、`bucket_radius`、`bucket_height`、`bucket_wall_thickness`、`safe_margin`
- Gazebo 实体由 `ur10_bringup/bucket_scene_node` 动态生成
- RViz 发布 `/bucket/marker`、`/bucket/safe_margin_marker`，并发布 `/bucket/features`

## 5. Gazebo 仿真流程
1. `my_robot/launch/gazebo_gantry.launch.py` 启动 `gzserver`。
2. `robot_state_publisher` 发布机器人模型。
3. `spawn_entity.py` 将 Gantry+UR10+shovel 实体注入 Gazebo。
4. `gazebo_ros2_control` 在 Gazebo 内加载控制器管理器。

## 6. ros2_control 控制器链路
- 控制器配置文件：`my_robot/config/ros2_controllers.yaml`
- 启动控制器：
  - `joint_state_broadcaster`
  - `joint_trajectory_controller`（UR10）
  - `gantry_trajectory_controller`（Gantry）
- 执行 action：
  - `/joint_trajectory_controller/follow_joint_trajectory`
  - `/gantry_trajectory_controller/follow_joint_trajectory`

## 7. MoveIt2 规划流程
- 启动文件：`my_robot_moveit_config/launch/my_robot_moveit.launch.py`
- 规划组：`my_robot_manipulator`（仅 UR10 六轴链）
- 核心配置：
  - `kinematics.yaml`
  - `joint_limits.yaml`
  - `ompl_planning.yaml`
  - `moveit_controllers.yaml`

## 8. RViz2 可视化流程
- RobotModel、TF、MotionPlanning 由 MoveIt2/RViz2 侧提供
- DP-RRT 与执行链可视化话题：
  - `/planning/tree_markers`
  - `/planning/markers`
  - `/planning/path`
  - `/execution/demo_marker`

## 9. DP-RRT 算法说明
`ur10_trajectory_planner/planner_node` 将 `Algo_DP_RRT_3D.m` 核心思想迁移到 C++：
- 动态目标偏置 `Pg`
- 动态引力融合 `rho`
- 自适应步长 `lambda(d_min)`
- 失败计数恢复机制 `fail_count`

规划对象为末端 TCP 笛卡尔路径，发布规划状态 `/planning/status` 与可视化 Marker。

## 10. 轨迹生成流程
`trajectory_node` 提供 `/trajectory/generate` 服务，输入桶参数后生成阶段化 TCP 轨迹：
1. 桶口上方接近
2. 入桶段
3. 桶内作业段
4. 抬升退出段

并发布：
- `/trajectory/target_poses`
- `/trajectory/target_pose_array`

## 11. 末端姿态拟合流程
在轨迹点上执行：
- 切线方向构造局部坐标系
- 铲面攻角/装配角补偿
- 姿态连续化（避免翻转）
- 轨迹点重采样与平滑

目标是减少 wrist 突跳与姿态反转。

## 12. PyQt5 GUI 使用说明
GUI 包：`ur10_unified_gui`，启动节点 `gui_node`。

界面分 4 页：
1. 关节控制：Gantry 3 轴 + UR10 6 轴（滑块+数值）
2. 轨迹规划：桶参数输入、规划/执行/停止
3. 系统状态：Gazebo/MoveIt/控制器/joint_states/marker/执行状态
4. 日志页：规划日志、执行日志、系统日志

中文到真实关节映射：
- 龙门架 X/Y/Z -> `gantry_x_joint/gantry_y_joint/gantry_z_joint`
- 基座/肩部/肘部/腕1/腕2/腕3 -> `ur10_shoulder_pan/ur10_shoulder_lift/ur10_elbow/ur10_wrist_1_joint/ur10_wrist_2_joint/ur10_wrist_3_joint`

## 13. 一键启动命令
```bash
cd /root/ur10_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch ur10_bringup full_system.launch.py
```

常用参数：
```bash
ros2 launch ur10_bringup full_system.launch.py \
  headless:=false \
  start_rviz:=true \
  gazebo_gui:=true \
  planner_mode:=dp_rrt \
  execution_mode:=demo \
  use_bucket:=true \
  bucket_center_x:=0.8 bucket_center_y:=0.0 bucket_center_z:=0.0 \
  bucket_radius:=0.18 bucket_height:=0.30 bucket_wall_thickness:=0.005 safe_margin:=0.03
```

## 14. 调试命令
```bash
cd /root/ur10_ws
source install/setup.bash

ros2 pkg list | grep -E "ur10|my_robot|bringup|planner|gui"
ros2 launch ur10_bringup full_system.launch.py headless:=true start_rviz:=false gazebo_gui:=false
ros2 node list
ros2 topic list
ros2 service list | grep trajectory
ros2 action list | grep follow_joint_trajectory
ros2 control list_controllers
```

## 15. 常见问题排查
1. `AMENT_TRACE_SETUP_FILES: unbound variable`：脚本中 `set -u` 前先给 `AMENT_TRACE_SETUP_FILES` 默认值，或先 `set +u` 再 `source`。
2. `gzserver exit code 255`：通常是已有旧 `gzserver` 进程占用端口，先清理残留再启动。
3. 控制器无法加载：确认 `gazebo_ros2_control` 已加载，且 `ros2_controllers.yaml` 中 joint 名与 URDF 完全一致。
4. 轨迹执行无动作：检查 `execution_mode`、`/execution/execute_shovel_task` action 是否存在，以及 `joint_trajectory_controller` 是否激活。

## 16. 后续开发计划
- 将 moveit 执行模式升级为“真实 IK 轨迹链（按姿态约束逐点求解）”
- 增加桶壁碰撞距离的规划代价函数与失败恢复策略
- GUI 增加运行参数持久化与任务模板
- 接入力/视觉传感器，形成闭环作业策略
