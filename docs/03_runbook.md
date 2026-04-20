# 运行手册

本文档面向使用者，介绍如何启动、调试和验证整个 UR10 仿真与避障系统。

相关文档：

- [编译与重编指南](01_build_and_rebuild_guide.md)
- [工作区结构说明](02_workspace_structure.md)
- [节点与 Launch 清单](04_nodes_and_launches.md)

## 1. 环境准备

每次打开新终端后，先执行：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

## 2. 一键启动

最常用的启动方式：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py
```

默认行为：

1. 启动 Gazebo Classic
2. 加载 UR10 模型
3. 激活 `joint_state_broadcaster` 和 `joint_trajectory_controller`
4. 启动 `move_group` 与 RViz
5. 启动俯视点云节点
6. 生成 `latest_obstacle.pcd`
7. 导入 `work_table` 和 `pcd_obstacle_box`
8. 自动启动 C++ 示例节点并执行一次避障规划

## 3. 自动链路说明

### Gazebo

Gazebo 使用的场景默认是：

```text
/root/ur10_ws/src/ur10_perception/worlds/obstacle_scene.world
```

其中包含：

- 工作台
- 规则障碍物
- UR10 模型生成所需世界环境

### MoveIt

MoveIt 由 `ur10_moveit_config` 提供配置，默认：

- 规划组：`ur_manipulator`
- 规划管线：`ompl`
- 控制器：`joint_trajectory_controller`

### 点云采集

俯视点云默认发布到：

```text
/overhead_camera/points
```

### PCD 文件写盘

默认 PCD 输出文件：

```text
/root/ur10_ws/data/latest_obstacle.pcd
```

### 障碍物回灌

PCD 会被转换为两个规划场景对象：

- `work_table`
- `pcd_obstacle_box`

### C++ 自动规划执行

总启动会自动运行：

```text
ur10_examples/move_group_interface_demo
```

它会等待障碍物导入完成，然后执行一次避障关节空间规划。

## 4. 手动运行方式

### 4.1 只启动总环境，不自动运行示例

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_cpp_demo:=false start_py_demo:=false
```

### 4.2 只起 Gazebo 仿真

```bash
ros2 launch ur10_simulation_bringup gazebo_sim.launch.py
```

### 4.3 只起 MoveIt 规划环境

```bash
ros2 launch ur10_simulation_bringup moveit_planning.launch.py
```

### 4.4 单独运行 C++ 示例

在 `move_group` 已经运行、障碍物已导入的前提下：

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

### 4.5 单独运行 Python 示例

在完整环境已启动后执行：

```bash
ros2 run ur10_examples_py moveit_py_demo
```

### 4.6 单独运行 PCD 采集与导入辅助脚本

```bash
ros2 run ur10_examples_py capture_and_import_pcd
```

这个脚本会：

1. 触发点云采集
2. 生成 PCD
3. 导入规划场景障碍物

### 4.7 单独运行点云采集节点

```bash
ros2 run ur10_perception pcd_capture_node --ros-args -p pointcloud_topic:=/overhead_camera/points -p output_file:=/root/ur10_ws/data/latest_obstacle.pcd
```

### 4.8 单独运行 PCD 导入节点

```bash
ros2 run ur10_perception pcd_to_collision_scene_node --ros-args -p pcd_file:=/root/ur10_ws/data/latest_obstacle.pcd -p obstacle_id:=pcd_obstacle_box
```

## 5. 常用变体参数

### 总启动常用参数

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py \
  start_cpp_demo:=false \
  start_py_demo:=false \
  start_rviz:=false \
  ur_type:=ur10 \
  pcd_file:=/root/ur10_ws/data/latest_obstacle.pcd
```

常用参数说明：

- `start_cpp_demo`
  - 是否自动运行 C++ 示例
- `start_py_demo`
  - 是否自动运行 Python 示例
- `start_rviz`
  - 是否启动 RViz
- `ur_type`
  - 默认 `ur10`，可切换为 `ur10e`
- `pcd_file`
  - 指定 PCD 输出与导入文件

## 6. 结果检查

### 应生成的 PCD 文件

检查：

```bash
ls -lh /root/ur10_ws/data/latest_obstacle.pcd
```

### 控制器状态

检查：

```bash
ros2 control list_controllers
```

应看到：

- `joint_state_broadcaster` 为 `active`
- `joint_trajectory_controller` 为 `active`

### 典型成功日志

完整自动链路中常见成功日志包括：

- `You can start planning now!`
- `Saved 2591 points to /root/ur10_ws/data/latest_obstacle.pcd`
- `Injected table work_table and collision box pcd_obstacle_box`
- `Execution succeeded for obstacle-aware joint-space goal.`
- `moveit_py execution status: SUCCEEDED`

### Gazebo / RViz 中应看到的现象

- Gazebo 中出现 UR10、工作台和障碍物
- 机械臂完成一条避开障碍物的规划轨迹
- RViz 中能看到机器人模型和 MotionPlanning 面板

## 7. 回退到 UR10e

如果需要使用回退模型：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py ur_type:=ur10e
```

这条链路保持相同接口，不需要改 C++ 或 Python 示例代码。
