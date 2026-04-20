# 编译与重编指南

本文档分为两部分：

1. 最终可复现的标准编译流程
2. 本次对话中的关键修复与联调纪要

相关文档：

- [工作区结构说明](02_workspace_structure.md)
- [运行手册](03_runbook.md)
- [节点与 Launch 清单](04_nodes_and_launches.md)

## 1. 系统前提

- Ubuntu + ROS 2 Humble
- `/root/moveit_ws` 作为上游 MoveIt2 源码工作区
- `/root/ur10_ws` 作为当前 UR10 overlay 工作区
- Gazebo Classic 已安装
- UR 官方描述包等依赖通过 apt 或上游工作区可用

推荐的环境 source 顺序：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

## 2. 依赖来源策略

本工作区采用“系统 apt 优先、源码工作区 overlay 补充”的策略：

- `ur_description`、Gazebo、`ros2_control`、MoveIt2 运行时依赖优先复用系统和已有工作区
- `moveit_py` 由 `/root/moveit_ws` 提供
- `/root/ur10_ws` 只保存本项目需要的自定义包和配置

## 3. 最终可复现编译流程

### 3.1 构建上游 MoveIt2 工作区

如果 `/root/moveit_ws` 尚未构建：

```bash
source /opt/ros/humble/setup.bash

cd /root/moveit_ws
colcon build
```

如果只需要保证 Python 开发接口可用，至少确认 `moveit_py` 已被构建。

### 3.2 构建当前 UR10 工作区

推荐使用普通安装方式构建整个工作区：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash

cd /root/ur10_ws
colcon build --base-paths /root/ur10_ws/src
```

构建完成后：

```bash
source /root/ur10_ws/install/setup.bash
```

### 3.3 单包重编命令

#### 重编 C++ 示例包

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash

cd /root/ur10_ws
colcon build --packages-select ur10_examples --base-paths /root/ur10_ws/src --allow-overriding ur10_examples
```

#### 重编 Python 示例包

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash

cd /root/ur10_ws
colcon build --packages-select ur10_examples_py --base-paths /root/ur10_ws/src --allow-overriding ur10_examples_py
```

#### 重编点云环境包

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash

cd /root/ur10_ws
colcon build --packages-select ur10_perception --base-paths /root/ur10_ws/src --allow-overriding ur10_perception
```

#### 重编 MoveIt 配置与总启动包

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash

cd /root/ur10_ws
colcon build --packages-select ur10_moveit_config ur10_simulation_bringup ur10_description --base-paths /root/ur10_ws/src
```

## 4. 本次对话中的关键修复与编译纪要

### 4.1 MoveIt 配置修正

- 将 `ur10_moveit_config` 的规划管线收敛到 `OMPL`
- 修正 `ur_moveit.launch.py` 的参数组织方式，避免运行时回退到 CHOMP
- 保证 `move_group` 与 `joint_trajectory_controller` 的控制器映射一致

### 4.2 C++ `MoveGroupInterface` 修正

- 初版 C++ 示例在障碍物规划阶段存在不稳定问题
- 后续改为：
  - 从 `/move_group` 同步本地需要的 MoveIt 参数
  - 使用 `MoveGroupInterface` 设定目标
  - 再通过 `plan_kinematic_path` 服务和 `execute_trajectory` action 完成规划与执行
- 这一版本最终通过联调验收

### 4.3 Python `moveit_py` 修正

- 修正了 `moveit_py` 的 `config_dict` 组织方式
- 显式指定 `planning_pipeline="ompl"` 与 `planner_id="RRTConnectkConfigDefault"`
- 加入 Python 环境自举，避免包查找与导入不稳定
- 处理了退出阶段的稳定性问题，使 `moveit_py_demo` 最终以退出码 `0` 返回

### 4.4 点云与 PCD 链路修正

- 新增俯视点云节点 `synthetic_overhead_camera_node`
- 新增 `pcd_capture_node`，将点云写盘为 PCD
- 新增 `pcd_to_collision_scene_node`，把 PCD 转为 `work_table` 与 `pcd_obstacle_box`
- 在总启动链中串联 PCD 采集和障碍物回灌流程

## 5. 常见问题

### `move_group` 没有起来

先确认：

```bash
ros2 node list | grep move_group
```

再确认 `complete_simulation.launch.py` 是否已经完成 Gazebo 与控制器初始化。

### 控制器未激活

检查：

```bash
ros2 control list_controllers
```

应至少看到：

- `joint_state_broadcaster`
- `joint_trajectory_controller`

两者都应为 `active`。

### PCD 没生成

检查：

```bash
ls -lh /root/ur10_ws/data/latest_obstacle.pcd
```

如果文件不存在，先确认 `/overhead_camera/points` 是否有数据。

### Python 示例运行失败

先确认：

1. `/root/moveit_ws/install/setup.bash` 已 source
2. `/root/ur10_ws/install/setup.bash` 已 source
3. `move_group` 已经在运行

推荐在完整环境启动后再执行：

```bash
ros2 run ur10_examples_py moveit_py_demo
```

### `complete_simulation.launch.py` 可以起，但不想自动运行示例

可以关闭自动示例：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_cpp_demo:=false start_py_demo:=false
```
