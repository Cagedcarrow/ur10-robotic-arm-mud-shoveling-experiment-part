# 运行手册

适合谁看：第一次真正运行这套 UR10 系统的人，或者想知道命令应该怎么输入的人。

本文档面向使用者，介绍如何启动、调试和验证整个 UR10 仿真与避障系统。

相关文档：

- [Docs 导航](README.md)
- [编译与重编指南](01_build_and_rebuild_guide.md)
- [工作区结构说明](02_workspace_structure.md)
- [节点与 Launch 清单](04_nodes_and_launches.md)
- [代码讲解](05_code_walkthrough.md)
- [路径规划与避障原理](06_motion_planning_and_obstacle_avoidance.md)
- [ROS 2 入门与本项目上手指南](07_ros2_getting_started.md)
- [实机网线通信与驱动启动](08_real_robot_ethernet_and_driver.md)

## 1. 环境准备

### 1.1 必须在新终端执行

每次运行前，建议打开一个新的终端窗口，不要在已经跑过旧仿真、旧 MoveIt 的终端里反复叠加执行。

如果你在旧终端里多次运行，常见现象包括：

- `Entity already exists`
- `Controller already loaded`
- `PREEMPTED`

这些通常不是代码坏了，而是旧的 Gazebo / MoveIt 进程还没退出。

### 1.2 source 顺序

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

1. 自动清理旧的 Gazebo / MoveIt 残留进程
2. 启动 Gazebo Classic
3. 加载“倒装龙门架 + UR10”模型
4. 激活 `joint_state_broadcaster`、`joint_trajectory_controller` 和 `gantry_trajectory_controller`
5. 自动把龙门移动到 launch 参数指定的初始 `X/Y/Z`
6. 启动 `move_group` 与 RViz

当前默认场景是干净场景，不再自动放置桌子和障碍物。

如果你没有图形界面，或者是远程终端环境，建议关闭 RViz：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false
```

## 3. 参数应该在哪里输入

这是新手最容易混淆的部分。

### 3.1 launch 参数

如果你运行的是 `ros2 launch`，参数写在命令后面，格式是：

```bash
ros2 launch <package> <launch_file> key:=value
```

例如：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false
```

### 3.2 节点参数

如果你运行的是 `ros2 run`，节点参数写在 `--ros-args -p` 后面，格式是：

```bash
ros2 run <package> <executable> --ros-args -p key:=value
```

例如：

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

### 3.3 代码默认值

如果你不从命令行传参数，程序会使用源码里的默认值。常见位置有：

- C++ 示例默认目标：`ur10_examples/src/move_group_interface_demo.cpp`
- Python 示例默认目标：`ur10_examples_py/ur10_examples_py/moveit_py_demo.py`
- 总启动默认参数：`ur10_simulation_bringup/launch/complete_simulation.launch.py`

所以你可以把“参数输入位置”简单理解为三种：

- 命令行 `ros2 launch ... key:=value`
- 命令行 `ros2 run ... --ros-args -p key:=value`
- 源码里默认写死的值

## 4. 自动链路说明

### Gazebo

Gazebo 使用的场景默认是：

```text
/root/ur10_ws/src/ur10_perception/worlds/gantry_only.world
```

其中包含：

- 地面
- 光照
- 龙门架倒装 UR10 运行所需世界环境

### MoveIt

MoveIt 由 `ur10_moveit_config` 提供配置，默认：

- 规划组：`ur_manipulator`
- 规划管线：`ompl`
- 控制器：`joint_trajectory_controller`

### 点云采集

点云链路现在默认关闭。如果你显式启用，俯视点云默认发布到：

```text
/overhead_camera/points
```

### PCD 文件写盘

如果启用点云链路，默认 PCD 输出文件：

```text
/root/ur10_ws/data/latest_obstacle.pcd
```

### 障碍物回灌

如果启用障碍物模式，PCD 会被转换为两个规划场景对象：

- `work_table`
- `pcd_obstacle_box`

### C++ 自动规划执行

当前默认不会自动运行 C++ 示例。如果你显式设置 `start_cpp_demo:=true`，会运行：

```text
ur10_examples/move_group_interface_demo
```

它会等待障碍物导入完成，然后执行一次避障关节空间规划。

## 5. 最常见三种使用方式

### 5.1 启动干净龙门场景

直接运行：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py
```

适合：

- 第一次验证龙门架和 UR10 是否能正常起来
- 想先看纯仿真场景，不想自动加载障碍物

### 5.2 启动带 MoveIt 的龙门场景并手动控制

如果你想自己一步一步调试：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_cpp_demo:=false start_py_demo:=false
```

适合：

- 想先看 Gazebo 和 MoveIt 是否起来
- 不想立即自动执行示例节点

启动后，如果你要手动移动龙门：

```bash
ros2 run ur10_examples_py gantry_control --ros-args -p x:=0.20 -p y:=0.00 -p z:=-0.70
```

### 5.3 已启动环境下单独运行 C++ / Python 示例

如果完整环境已经启动，再开新终端执行：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

单独运行 C++：

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

单独运行 Python：

```bash
ros2 run ur10_examples_py moveit_py_demo
```

单独运行龙门控制：

```bash
ros2 run ur10_examples_py gantry_control --ros-args -p x:=0.10 -p y:=0.05 -p z:=-0.65
```

### 5.4 如果你仍然想启用旧的障碍物/PCD 场景

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py \
  world:=/root/ur10_ws/src/ur10_perception/worlds/obstacle_scene.world \
  enable_overhead_camera:=true \
  capture_pcd_on_start:=true \
  import_pcd_obstacle:=true \
  start_cpp_demo:=true
```

## 6. 手动运行方式

### 6.1 只起纯龙门仿真

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false start_cpp_demo:=false start_py_demo:=false
```

### 6.2 指定龙门初始位置

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py \
  gantry_x_initial:=0.15 \
  gantry_y_initial:=0.05 \
  gantry_z_initial:=-0.70
```

### 6.3 启动真实 UR10 驱动

```bash
ros2 launch ur10_simulation_bringup real_robot_driver.launch.py \
  ur_type:=ur10 \
  robot_ip:=192.168.56.101 \
  reverse_ip:=192.168.56.1
```

详细接线和 IP 规划见：

- [实机网线通信与驱动启动](08_real_robot_ethernet_and_driver.md)

### 6.1 只启动总环境，不自动运行示例

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_cpp_demo:=false start_py_demo:=false
```

### 6.2 只起 Gazebo 仿真

```bash
ros2 launch ur10_simulation_bringup gazebo_sim.launch.py
```

### 6.3 只起 MoveIt 规划环境

```bash
ros2 launch ur10_simulation_bringup moveit_planning.launch.py
```

### 6.4 单独运行 C++ 示例

在 `move_group` 已经运行、障碍物已导入的前提下：

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

### 6.5 单独运行 Python 示例

在完整环境已启动后执行：

```bash
ros2 run ur10_examples_py moveit_py_demo
```

### 6.6 单独运行 PCD 采集与导入辅助脚本

```bash
ros2 run ur10_examples_py capture_and_import_pcd
```

这个脚本会：

1. 触发点云采集
2. 生成 PCD
3. 导入规划场景障碍物

### 6.7 单独运行点云采集节点

```bash
ros2 run ur10_perception pcd_capture_node --ros-args -p pointcloud_topic:=/overhead_camera/points -p output_file:=/root/ur10_ws/data/latest_obstacle.pcd
```

### 6.8 单独运行 PCD 导入节点

```bash
ros2 run ur10_perception pcd_to_collision_scene_node --ros-args -p pcd_file:=/root/ur10_ws/data/latest_obstacle.pcd -p obstacle_id:=pcd_obstacle_box
```

## 7. 常用变体参数

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

## 8. 常见报错是什么意思

### `Entity already exists`

含义：

- Gazebo 里已经有同名机器人实体了

常见原因：

- 上一轮 Gazebo 没有退出干净

现在默认总启动会先自动清理旧进程，但如果你手动起了其他 Gazebo，也可能遇到这个提示。

### `Controller already loaded`

含义：

- 控制器已经由旧的 `controller_manager` 加载过

常见原因：

- 旧的 Gazebo / `gazebo_ros2_control` 还在运行

### `PREEMPTED`

含义：

- 当前轨迹执行被中断，或者执行链路被旧实例抢占

常见原因：

- 有多套 `move_group` / `controller_manager` 同时存在
- 当前仿真不是一套干净启动出来的环境

最稳妥的办法：

- 关闭当前 launch
- 新开终端
- 重新 `source`
- 再次运行 `complete_simulation.launch.py`

## 9. 结果检查

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

下一篇建议阅读：[节点与 Launch 清单](04_nodes_and_launches.md)
