# 完整系统升级总结

## 1. 本次目标
将工作区主线收敛为：
- `my_robot`
- `my_robot_moveit_config`
- `ur10_trajectory_planner`
- `ur10_bringup`
- `ur10_unified_gui`

并打通一键启动链：Gantry + UR10 + shovel + bucket + Gazebo + MoveIt2 + RViz2 + GUI + DP-RRT + 轨迹拟合 + 执行。

## 2. 整理后的包结构
### 核心主线包
- `my_robot`
- `my_robot_moveit_config`
- `ur10_trajectory_planner`
- `ur10_bringup`
- `ur10_unified_gui`

### 辅助包
- `ur10_simulation_bringup`
- `ur10_examples` / `ur10_examples_py`
- `ur10_perception`
- `ur10_real_comm`
- `FT300/ft300_gui_ros2`

### 历史/保留包
- `ur10_with_shovel`、`ur10_description`、`ur10_moveit_config`
- `FT300/my_robotiq_force_torque_sensor-master`（ROS1）
- `轨迹构建与拟合说明文档`（保留文档，不作为主线运行入口）

## 3. 新增包
1. `ur10_bringup`（ament_python）
- `launch/full_system.launch.py`
- `ur10_bringup/bucket_scene_node.py`

2. `ur10_unified_gui` ROS2 包化（ament_python）
- `package.xml`、`setup.py`、`setup.cfg`、`resource/`
- `ur10_unified_gui/gui_node.py`
- `launch/gui.launch.py`

3. `ur10_trajectory_planner`（由原模板包硬切换重构）
- C++ 主实现三节点：`trajectory_node` / `planner_node` / `executor_node`

## 4. 修改包
- `ur10_trajectory_planner`
  - 统一接口：
    - Service `/trajectory/generate`
    - Topics `/planning/path` `/planning/markers` `/planning/tree_markers` `/planning/status`
    - Action `/execution/execute_shovel_task`
    - Topics `/execution/feedback` `/execution/status`
  - `planner_node`：DP-RRT 规划、分段路径拼接、状态发布（移除自定义 `ompl` 占位分支）
  - `trajectory_node`：桶约束轨迹生成与姿态序列发布
  - `executor_node`：`demo|moveit` 双执行模式
  - `executor_adapter`：关节名改为真实 `ur10_*`

- `ur10_bringup`
  - `full_system.launch.py` 集成：Gazebo、MoveIt2、轨迹三节点、桶场景、GUI
  - `bucket_scene_node.py`：Gazebo 桶实体 + RViz Marker + `/bucket/features`

- `ur10_simulation_bringup`
  - 依赖更新为 `ur10_trajectory_planner`

- `ur10_real_comm`
  - 修复 `setup.py` 数据文件安装冲突（移除高风险 scripts data_files 项）

- `/root/ur10_ws/src/README.md`
  - 重写为工程级总文档

## 5. 主线启动架构
统一入口：
```bash
ros2 launch ur10_bringup full_system.launch.py
```

启动链：
1. Gazebo + world
2. robot_state_publisher + spawn robot
3. ros2_control + controllers
4. MoveIt2 move_group
5. bucket scene node
6. trajectory/planner/executor 三节点
7. GUI（非 headless）

## 6. 桶模型实现
- 参数：
  - `bucket_center_x/y/z`
  - `bucket_radius`
  - `bucket_height`
  - `bucket_wall_thickness`
  - `safe_margin`
- Gazebo：动态 `SpawnEntity`
- RViz：`/bucket/marker`、`/bucket/safe_margin_marker`
- 轨迹输入：`/bucket/features`

## 7. DP-RRT 接入说明
位于 `ur10_trajectory_planner/planner_node`，保留机制：
- 动态目标偏置 `Pg`
- 动态引力融合 `rho`
- 自适应步长 `lambda(d_min)`
- 失败计数恢复 `fail_count`

规划对象：末端 TCP 笛卡尔路径（非 9 轴联合采样）。

语义修正：
- 自定义规划器仅保留 `dp_rrt`。
- OMPL 多算法选择统一在 MoveIt/RViz 链路中使用（`/query_planner_interface` 校验 planner_ids）。

## 8. 轨迹生成说明
`trajectory_node` 提供 `/trajectory/generate` 服务，围绕桶生成分阶段路径：
- 接近桶口
- 入桶
- 桶内作业弧段
- 抬升退出

并发布 `TargetPoseSeq` 到 `/trajectory/target_poses`。

## 9. 姿态拟合说明
在 `build_pose_sequence` 中执行：
- 轨迹切线对齐
- 正交基重建
- 符号连续化（避免姿态翻转）
- 攻角/装配角补偿

目标：降低 wrist 突跳与姿态反转风险。

## 10. PyQt5 GUI 说明
`ur10_unified_gui/gui_node` 已可作为 ROS2 节点启动，支持：
- 关节控制页（Gantry 3 轴 + UR10 6 轴，中文映射真实 joint）
- 轨迹规划页（桶参数 + 规划/执行按钮）
- 系统状态页（Gazebo/MoveIt/控制器/joint_states/markers）
- 日志页

## 11. demo / moveit 执行模式说明
- `execution_mode:=demo`
  - 发布 `/execution/demo_marker` 动画演示
  - 不依赖完整 IK，保证演示闭环

- `execution_mode:=moveit`
  - 发送 `JointTrajectory` 到 `/joint_trajectory_controller/follow_joint_trajectory`
  - 当前版本为可执行保底链，IK 仍以近似映射为主（见遗留问题）

## 12. 测试命令与结果
### 构建
```bash
cd /root/ur10_ws
colcon build --symlink-install --packages-select \
  my_robot my_robot_moveit_config ur10_trajectory_planner ur10_bringup ur10_unified_gui ur10_simulation_bringup
```
结果：通过。

```bash
cd /root/ur10_ws
colcon build --symlink-install --packages-select ur10_real_comm
```
结果：通过（已修复安装冲突）。

### 单节点
```bash
ros2 run ur10_trajectory_planner planner_node
ros2 run ur10_trajectory_planner trajectory_node
ros2 run ur10_trajectory_planner executor_node
QT_QPA_PLATFORM=offscreen ros2 run ur10_unified_gui gui_node
```
结果：均可启动。

### 一键无头链路检查（脚本化）
验证到：
- 节点：`trajectory_node/planner_node/executor_node` 在图中
- service：`/trajectory/generate` 存在
- action：`/execution/execute_shovel_task` 存在
- topics：`/planning/*`、`/execution/*`、`/bucket/features` 存在

## 13. 当前遗留问题
1. `ros2 control list_controllers` 在“短时超时窗口”偶发连接失败（XMLRPC connection refused），通常是查询时机过早导致。
2. `moveit` 执行模式当前采用“可执行保底”实现，未完成逐点真实 MoveIt IK 优选链。
3. `bucket_scene_node` 当前为一次性 spawn 逻辑，参数运行时热更新/重生成功能仍可增强。
4. 工作区中存在历史遗留运行进程时，可能干扰新测试（需先清理残留进程）。

## 14. 下一步建议
1. 将 `execution_mode=moveit` 升级为 `compute_ik + 关节连续性优化 + 时间参数化` 全链。
2. 增加桶壁距离代价与入桶窗口约束，提升 DP-RRT 在真实作业场景稳定性。
3. 为 `ur10_bringup` 增加 `cleanup` 选项，启动前自动清理历史仿真残留进程。
4. 增加自动化回归脚本：一键构建 + 无头启动 + 接口验收。
