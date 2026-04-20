# 节点与 Launch 清单

适合谁看：想知道“系统到底启动了哪些节点、哪些是自动起的、参数从哪传”的读者。

本文档汇总当前工作区中的主要 launch 文件、可执行节点以及关键 ROS 接口。

相关文档：

- [编译与重编指南](01_build_and_rebuild_guide.md)
- [工作区结构说明](02_workspace_structure.md)
- [运行手册](03_runbook.md)

## 1. Launch 文件清单

### `ur10_simulation_bringup/launch/complete_simulation.launch.py`

作用：

- 项目总入口
- 串联 Gazebo、MoveIt、感知、PCD 导入和示例节点
- 启动前自动清理旧的 Gazebo / MoveIt 残留进程

典型用途：

- 一条命令完整演示系统能力

最常改的参数：

- `start_rviz`
- `start_cpp_demo`
- `start_py_demo`
- `pcd_file`
- `ur_type`

### `ur10_simulation_bringup/launch/gazebo_sim.launch.py`

作用：

- 启动 Gazebo Classic
- 发布机器人描述
- 在 Gazebo 中生成 UR10
- 启动控制器

典型用途：

- 单独调试仿真与控制器

最常改的参数：

- `world`
- `ur_type`
- `use_fake_hardware`

### `ur10_simulation_bringup/launch/moveit_planning.launch.py`

作用：

- 启动 MoveIt2 规划环境
- 调用 `ur10_moveit_config/launch/ur_moveit.launch.py`

典型用途：

- 单独调试 `move_group` 与 RViz

最常改的参数：

- `start_rviz`
- `ur_type`

### `ur10_simulation_bringup/launch/demo_nodes.launch.py`

作用：

- 启动 C++ `move_group_interface_demo`
- 启动 Python `moveit_py_demo`

典型用途：

- 在已有仿真与 MoveIt 环境中只调试示例节点

最常改的参数：

- `start_cpp_demo`
- `start_py_demo`
- `wait_for_obstacle`
- `obstacle_id`

### `ur10_perception/launch/perception_only.launch.py`

作用：

- 单独启动俯视点云感知链路

典型用途：

- 调试点云相机与 PCD 生成

最常改的参数：

- `pointcloud_topic`
- `pcd_file`

### `ur10_description/launch/view_description.launch.py`

作用：

- 仅查看机器人描述、关节状态和 RViz 模型

典型用途：

- 调试 URDF / xacro

最常改的参数：

- `ur_type`

## 2. 节点总览表

| 节点 | 包 | 是否自动启动 | 更适合做什么 |
| --- | --- | --- | --- |
| `move_group_interface_demo` | `ur10_examples` | 是 | 自动或手动调试 C++ 规划执行 |
| `moveit_py_demo` | `ur10_examples_py` | 默认否 | 手动调试 Python 规划执行 |
| `capture_and_import_pcd` | `ur10_examples_py` | 默认否 | 手动触发一次点云采集和导入 |
| `pcd_capture_node` | `ur10_perception` | 是 | 调试 PCD 写盘 |
| `pcd_to_collision_scene_node` | `ur10_perception` | 是 | 调试障碍物回灌 |
| `synthetic_overhead_camera_node` | `ur10_perception` | 是 | 提供稳定点云输入 |

## 3. 可执行节点清单

## `move_group_interface_demo`

包：

```text
ur10_examples
```

作用：

- C++ `MoveGroupInterface` 示例
- 等待规划场景障碍物
- 请求规划并执行轨迹

默认是否自动启动：

- 是，由 `complete_simulation.launch.py` 自动启动

输入参数在哪里传入：

- `demo_nodes.launch.py`
- 或者手动执行 `ros2 run ... --ros-args -p ...`

常用参数名：

- `use_sim_time`
- `planning_group`
- `obstacle_id`

## `moveit_py_demo`

包：

```text
ur10_examples_py
```

作用：

- Python `moveit_py` 示例
- 在已启动的 `move_group` 环境中完成规划与执行

默认是否自动启动：

- 默认否，可单独运行或通过 `start_py_demo:=true` 启动

输入参数在哪里传入：

- `demo_nodes.launch.py`
- 或者手动执行 `ros2 run ur10_examples_py moveit_py_demo`

常用参数名：

- `planning_group`
- `use_sim_time`

## `capture_and_import_pcd`

包：

```text
ur10_examples_py
```

作用：

- 依次调用点云采集与 PCD 导入
- 适合一次性手动触发点云链路

默认是否自动启动：

- 否，可通过 `start_py_tools:=true` 启动

输入参数在哪里传入：

- `complete_simulation.launch.py`
- 或者手动运行脚本时从节点参数传入

常用参数名：

- `pcd_file`
- `pointcloud_topic`
- `obstacle_id`

## `pcd_capture_node`

包：

```text
ur10_perception
```

作用：

- 订阅点云并写为 PCD 文件

输入：

- `/overhead_camera/points`

输出：

- `/root/ur10_ws/data/latest_obstacle.pcd`

默认是否自动启动：

- 是，由总启动自动触发一次

输入参数在哪里传入：

- `complete_simulation.launch.py`
- 或者手动运行 `ros2 run ur10_perception pcd_capture_node --ros-args -p ...`

常用参数名：

- `pointcloud_topic`
- `output_file`
- `use_sim_time`

## `pcd_to_collision_scene_node`

包：

```text
ur10_perception
```

作用：

- 读取 PCD
- 提取障碍物
- 发布 `CollisionObject`

输入：

- `pcd_file` 参数

输出：

- `work_table`
- `pcd_obstacle_box`

默认是否自动启动：

- 是，在 PCD 采集完成后自动触发

输入参数在哪里传入：

- `complete_simulation.launch.py`
- 或者手动运行 `ros2 run ur10_perception pcd_to_collision_scene_node --ros-args -p ...`

常用参数名：

- `pcd_file`
- `obstacle_id`
- `use_sim_time`

## `synthetic_overhead_camera_node`

包：

```text
ur10_perception
```

作用：

- 发布俯视点云
- 为 PCD 采集提供稳定输入

输入：

- 无外部输入

输出：

- `/overhead_camera/points`

默认是否自动启动：

- 是，由总启动自动启动

输入参数在哪里传入：

- `complete_simulation.launch.py`

常用参数名：

- `pointcloud_topic`
- `frame_id`
- `use_sim_time`

## 4. 关键 ROS 接口

### 话题

| 接口 | 类型 | 作用 |
| --- | --- | --- |
| `/joint_states` | `sensor_msgs/msg/JointState` | 机械臂当前关节状态 |
| `/overhead_camera/points` | `sensor_msgs/msg/PointCloud2` | 俯视点云输入 |
| `/planning_scene` | MoveIt 规划场景更新 | MoveIt 场景同步 |
| `/planning_scene_world` | MoveIt 场景世界对象 | 障碍物世界状态 |

### 控制器

| 控制器 | 作用 |
| --- | --- |
| `joint_state_broadcaster` | 发布当前关节状态 |
| `joint_trajectory_controller` | 执行 MoveIt 输出的关节轨迹 |

### 常用文件输出

| 路径 | 作用 |
| --- | --- |
| `/root/ur10_ws/data/latest_obstacle.pcd` | 默认点云输出文件 |

下一篇建议阅读：[代码讲解](05_code_walkthrough.md)
