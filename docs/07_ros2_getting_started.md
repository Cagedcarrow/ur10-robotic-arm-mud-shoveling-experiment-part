# ROS 2 入门与本项目上手指南

适合谁看：ROS 2 新手、第一次接触 MoveIt2 的用户、第一次想运行这套 UR10 仿真系统的人。

这篇文档会从最基础的 ROS 2 概念讲起，再一步一步把本项目真正使用到的节点、参数、launch、Gazebo 和 MoveIt2 串起来。目标不是讲抽象理论，而是让你能看懂这套工程、能自己运行、能知道应该去哪里改参数和代码。

相关文档：

- [Docs 导航](README.md)
- [运行手册](03_runbook.md)
- [节点与 Launch 清单](04_nodes_and_launches.md)
- [代码讲解](05_code_walkthrough.md)
- [路径规划与避障原理](06_motion_planning_and_obstacle_avoidance.md)

## 1. ROS 2 是什么

ROS 2 可以把它理解为“机器人软件开发框架”。

它帮你解决的不是“怎么写机械臂运动学公式”这种单一问题，而是整套机器人系统如何组织起来的问题，比如：

- 一个程序如何发布机械臂当前状态
- 另一个程序如何读取这些状态
- 一个程序如何发运动目标
- 另一个程序如何执行这个目标
- 一整套系统如何一键启动

在这套 UR10 工程里，ROS 2 承担的是“系统胶水”的角色。Gazebo、MoveIt2、控制器、点云节点、C++ 示例、Python 示例，全部靠 ROS 2 的通信机制连接起来。

## 2. 先理解这几个最重要的 ROS 2 概念

### 2.1 工作区 workspace

ROS 2 工作区通常长这样：

```text
ur10_ws/
├── src/
├── build/
├── install/
└── log/
```

可以这样理解：

- `src/` 放源码
- `build/` 放编译中间产物
- `install/` 放编译后的可运行结果
- `log/` 放编译日志

本项目的源码都在：

```text
/root/ur10_ws/src
```

### 2.2 包 package

ROS 2 不是把所有代码都丢进一个大目录，而是按“包”组织。

在本项目里最重要的包有：

- `ur10_description`
- `ur10_moveit_config`
- `ur10_simulation_bringup`
- `ur10_perception`
- `ur10_examples`
- `ur10_examples_py`

你可以把包理解成一个个功能模块。

### 2.3 节点 node

节点是 ROS 2 里真正运行的程序。

例如本项目里：

- `move_group` 是 MoveIt 的核心节点
- `robot_state_publisher` 负责发布机器人 TF 和关节树
- `pcd_capture_node` 负责采集点云并写 PCD
- `move_group_interface_demo` 是 C++ 规划示例

你以后看到：

```bash
ros2 run <package> <executable>
```

实际上就是在启动一个节点。

### 2.4 话题 topic

话题是 ROS 2 最常见的数据通道。

一个节点发布数据，另一个节点订阅数据。

本项目里的典型话题：

- `/joint_states`
- `/overhead_camera/points`
- `/planning_scene`
- `/planning_scene_world`

比如：

- `synthetic_overhead_camera_node` 发布 `/overhead_camera/points`
- `pcd_capture_node` 订阅 `/overhead_camera/points`

### 2.5 参数 parameter

参数就是运行时配置。

例如：

- 是否启动 RViz
- PCD 写到哪个文件
- 使用哪个机器人型号
- 是否启用仿真时间

参数一般有两种常见输入方式：

#### launch 参数

写在 `ros2 launch` 后面：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false
```

#### 节点参数

写在 `ros2 run ... --ros-args -p` 后面：

```bash
ros2 run ur10_perception pcd_capture_node --ros-args -p output_file:=/root/ur10_ws/data/latest_obstacle.pcd
```

### 2.6 launch 文件

如果一个系统只需要一个节点，你可以直接 `ros2 run`。

但机器人系统通常要同时起很多节点，所以 ROS 2 提供了 launch 文件。

本项目里的 launch 文件主要在：

```text
/root/ur10_ws/src/ur10_simulation_bringup/launch
```

最重要的是：

```text
complete_simulation.launch.py
```

它可以一条命令拉起整套系统。

## 3. 为什么每次都要 source

你经常会看到这三行：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

它们的作用是把环境变量准备好，让当前终端知道：

- ROS 2 的命令在哪里
- MoveIt2 的包在哪里
- 你自己的工作区包在哪里

可以这样理解：

- `/opt/ros/humble/setup.bash` 载入系统 ROS 2
- `/root/moveit_ws/install/setup.bash` 载入上游 MoveIt2
- `/root/ur10_ws/install/setup.bash` 载入你自己的 UR10 工作区

如果不 `source`，ROS 2 就找不到你的包、节点和 launch 文件。

## 4. 这套 UR10 系统里真正有哪些节点

最常见的节点大致分成 5 类。

### 4.1 仿真类节点

- `gzserver`
- `gzclient`
- `robot_state_publisher`

这些节点负责：

- 提供 Gazebo 仿真世界
- 显示 Gazebo 界面
- 发布机器人模型和 TF

### 4.2 控制类节点

严格说控制器不总是以你熟悉的普通 ROS 节点形式出现，但你可以先记住两件事：

- `gazebo_ros2_control` 把 Gazebo 和 ROS 2 控制器连接起来
- `joint_trajectory_controller` 负责真正执行机械臂轨迹

### 4.3 规划类节点

最关键的是：

- `move_group`

它是 MoveIt 的大脑，负责：

- 接收目标
- 读取当前状态
- 读取障碍物
- 做轨迹规划
- 触发执行

### 4.4 感知类节点

本项目主要有：

- `synthetic_overhead_camera_node`
- `pcd_capture_node`
- `pcd_to_collision_scene_node`

它们共同完成：

- 发布点云
- 保存 PCD
- 导入障碍物

### 4.5 示例类节点

- `move_group_interface_demo`
- `moveit_py_demo`

它们是“用户给 MoveIt 发目标”的示例程序。

## 5. Gazebo 到底有什么用

这是很多新手最容易问的问题。

### 5.1 Gazebo 的作用不是“做规划”

Gazebo 不负责路径规划。

Gazebo 的主要作用是：

- 提供仿真世界
- 提供机器人的物理模型和关节状态
- 让你看到机械臂真的在动

也就是说：

- MoveIt 负责“算怎么走”
- Gazebo 负责“把结果显示并执行出来”

### 5.2 本项目里 Gazebo 具体做了什么

在这套工程里，Gazebo 负责：

1. 加载 `obstacle_scene.world`
2. 接收 `spawn_entity.py` 生成的 UR10
3. 通过 `gazebo_ros2_control` 接入控制器
4. 执行 `joint_trajectory_controller` 发来的轨迹

所以如果没有 Gazebo：

- 你仍然可以在理论上做 MoveIt 规划
- 但你看不到真实的仿真执行过程

### 5.3 为什么本项目还需要 world 文件

因为 Gazebo 不是只显示机械臂，它还要显示“世界”。

本项目世界文件是：

```text
/root/ur10_ws/src/ur10_perception/worlds/obstacle_scene.world
```

里面包括：

- 地面
- 工作台
- 障碍物

这些对象一方面让仿真更真实，另一方面也有助于点云采集。

## 6. MoveIt2 到底在做什么

MoveIt2 是机械臂规划框架。

在本项目里它最重要的职责是：

- 读取当前关节状态
- 读取碰撞场景
- 根据目标生成一条无碰撞轨迹
- 把轨迹交给控制器执行

你可以把 MoveIt2 理解成：

- “机械臂路径规划的大脑”

### 6.1 `move_group` 是什么

`move_group` 是 MoveIt2 最核心的运行节点。

它负责：

- 对外提供规划能力
- 调用 OMPL
- 管理 Planning Scene
- 触发执行

所以当你说“MoveIt 起了吗”，很多时候本质上就是在问：

- `move_group` 起了吗

### 6.2 什么是规划组

本项目默认规划组是：

```text
ur_manipulator
```

规划组决定：

- 哪些关节参与规划
- 示例节点到底在控制哪一组关节

### 6.3 什么是 Planning Scene

Planning Scene 可以理解成 MoveIt 心中的“世界模型”。

里面至少包含两类信息：

- 机器人当前状态
- 外界障碍物

如果障碍物没进入 Planning Scene，MoveIt 就不会避障。

## 7. 点云障碍物是怎么进入 MoveIt 的

这条链路是本项目最有特色的部分。

### 7.1 第一步：生成点云

节点：

```text
synthetic_overhead_camera_node
```

输出：

```text
/overhead_camera/points
```

它的作用是持续发布俯视点云。

### 7.2 第二步：保存成 PCD

节点：

```text
pcd_capture_node
```

它会订阅点云并把结果写到：

```text
/root/ur10_ws/data/latest_obstacle.pcd
```

为什么要先写 PCD：

- 方便调试
- 方便复现
- 方便把同一份障碍物数据重复导入

### 7.3 第三步：从 PCD 生成障碍物

节点：

```text
pcd_to_collision_scene_node
```

它负责：

1. 读取 PCD
2. 提取工作台和平面上方障碍物
3. 生成碰撞对象
4. 发布到 MoveIt 场景中

最终常见对象是：

- `work_table`
- `pcd_obstacle_box`

### 7.4 第四步：MoveIt 规划时避开它

一旦 `pcd_obstacle_box` 已经进入 Planning Scene：

- MoveIt 在规划时就会把它当成障碍物
- 如果某条轨迹穿过这个障碍物，就不会被接受

这就是本项目的避障逻辑。

## 8. 如何真正运行这套系统

### 8.1 最标准的运行方式

在新终端中执行：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash

ros2 launch ur10_simulation_bringup complete_simulation.launch.py
```

默认会自动完成：

1. 清理旧进程
2. 启动 Gazebo
3. 加载 UR10
4. 启动控制器
5. 启动 MoveIt
6. 生成 PCD
7. 导入障碍物
8. 自动执行一次 C++ 避障规划

### 8.2 无图形界面怎么运行

如果你在远程终端或没有图形桌面，建议：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false
```

### 8.3 如何单独运行 MoveIt2 机械臂运动规划

如果你已经把仿真环境起好了，想单独运行机械臂规划示例：

#### C++ 示例

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

#### Python 示例

```bash
ros2 run ur10_examples_py moveit_py_demo
```

这两条命令的前提是：

- `move_group` 已经在运行
- 控制器已经激活
- 机器人已经在 Gazebo 里生成

### 8.4 如何手动调试 PCD 导入

如果你想自己控制感知链路，可以这样：

先采集：

```bash
ros2 run ur10_perception pcd_capture_node --ros-args -p pointcloud_topic:=/overhead_camera/points -p output_file:=/root/ur10_ws/data/latest_obstacle.pcd
```

再导入：

```bash
ros2 run ur10_perception pcd_to_collision_scene_node --ros-args -p pcd_file:=/root/ur10_ws/data/latest_obstacle.pcd -p obstacle_id:=pcd_obstacle_box
```

### 8.5 参数应该在哪里写

最常见的写法有两种。

#### 给 launch 写参数

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false ur_type:=ur10
```

#### 给节点写参数

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

如果命令行不写，程序就会回到 launch 默认值或源码默认值。

## 9. 如何理解代码应该从哪里看

如果你是新手，建议按下面顺序看代码：

1. `ur10_simulation_bringup/launch/complete_simulation.launch.py`
2. `ur10_simulation_bringup/launch/gazebo_sim.launch.py`
3. `ur10_moveit_config/launch/ur_moveit.launch.py`
4. `ur10_examples/src/move_group_interface_demo.cpp`
5. `ur10_examples_py/ur10_examples_py/moveit_py_demo.py`
6. `ur10_perception/src/pcd_capture_node.cpp`
7. `ur10_perception/src/pcd_to_collision_scene_node.cpp`

原因很简单：

- 先看“系统怎么串起来”
- 再看“规划怎么发起”
- 最后看“障碍物怎么进场景”

## 10. 常见问题

### 10.1 为什么我 `source` 之后还是跑不起来

先确认：

- 你是在新终端里执行的
- 三个 `source` 的顺序没写错
- `ur10_ws` 和 `moveit_ws` 都已经编译过

### 10.2 为什么 Gazebo 里有机器人，但机械臂不动

常见原因：

- `joint_trajectory_controller` 没有激活
- `move_group` 没有真正执行成功
- 当前环境里有旧的残留进程

### 10.3 为什么我看到了点云，但机械臂还是撞障碍物

因为：

- 点云存在不等于障碍物已经进入 MoveIt 场景

你还需要确认：

- PCD 已经生成
- `pcd_to_collision_scene_node` 已经运行
- `pcd_obstacle_box` 已经被导入

### 10.4 `Entity already exists` 是什么意思

说明 Gazebo 里已经有一个同名机器人。

通常意味着：

- 旧的仿真没退出干净

### 10.5 `Controller already loaded` 是什么意思

说明旧的控制器实例还在。

通常意味着：

- 旧 Gazebo / `controller_manager` 还活着

### 10.6 `PREEMPTED` 是什么意思

通常表示轨迹执行被中断或被其他实例抢占。

最常见原因：

- 系统里同时存在多套 `move_group` 或控制器

## 11. 你学会这篇文档后，应该能做到什么

看完这篇文档后，你应该至少能做到：

- 知道 ROS 2 工作区、包、节点、话题、参数和 launch 是什么
- 知道 Gazebo 在本项目里是做什么的
- 知道 MoveIt2 在本项目里是做什么的
- 知道点云如何变成 MoveIt 的障碍物
- 知道如何启动完整系统
- 知道如何单独运行 MoveIt2 机械臂运动规划
- 知道该从哪里开始读代码

下一篇建议阅读：[运行手册](03_runbook.md)
