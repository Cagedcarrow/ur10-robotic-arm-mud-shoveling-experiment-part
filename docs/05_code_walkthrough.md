# 代码讲解

适合谁看：已经能运行系统，现在想知道“这套系统的代码到底是怎么串起来的”的新手。

这篇文档按“先看调用链，再看代码”的顺序讲解项目代码结构。

相关文档：

- [Docs 导航](README.md)
- [工作区结构说明](02_workspace_structure.md)
- [运行手册](03_runbook.md)
- [路径规划与避障原理](06_motion_planning_and_obstacle_avoidance.md)
- [ROS 2 入门与本项目上手指南](07_ros2_getting_started.md)

## 1. 系统代码总览

整套系统的总入口是：

```text
ur10_simulation_bringup/launch/complete_simulation.launch.py
```

你可以把它理解为一个“总导演”：

1. 先清理旧的 Gazebo / MoveIt 残留进程
2. 启动 Gazebo 和 UR10
3. 启动 MoveIt
4. 启动点云采集
5. 生成 PCD
6. 导入障碍物
7. 启动 C++ 或 Python 示例节点

所以如果你以后要理解整套调用链，第一眼先看 `complete_simulation.launch.py` 最有效。

## 2. 启动链代码讲解

### `complete_simulation.launch.py`

它负责：

- 定义总启动参数，例如 `start_rviz`、`start_cpp_demo`、`pcd_file`
- 启动前自动清理旧进程
- 按顺序启动 Gazebo、MoveIt、点云、PCD 导入和示例节点

你最常会改这里的地方：

- 默认是否启动 RViz
- 默认是否自动运行 C++ / Python 示例
- 默认 PCD 文件路径
- 自动启动顺序

### `gazebo_sim.launch.py`

它负责：

- 调用 Gazebo 的官方 launch
- 通过 `xacro` 生成 `robot_description`
- 启动 `robot_state_publisher`
- 调用 `spawn_entity.py` 把 UR10 放进 Gazebo
- 依次启动 `joint_state_broadcaster` 和 `joint_trajectory_controller`

这里最重要的概念是：

- `robot_description` 只是机器人模型字符串
- 真正让机器人出现在 Gazebo 里的是 `spawn_entity.py`

### `moveit_planning.launch.py`

它负责：

- 引入 MoveIt 启动文件
- 把机器人描述、语义描述和规划参数传给 `move_group`
- 根据参数决定是否启动 RViz

这个文件更像一个“桥接层”，把 `ur10_moveit_config` 的内容接到总系统里。

### `demo_nodes.launch.py`

它负责：

- 启动 C++ 示例节点
- 启动 Python 示例节点
- 给示例节点传入必要参数

如果你以后想换成自己的规划节点，这里通常就是入口。

## 3. 机器人与规划配置代码讲解

### `ur10_description/urdf/ur10_sim.urdf.xacro`

这是机器人描述的总入口。

它负责：

- 选择 `ur10` 或 `ur10e`
- 组合机器人几何、关节和仿真插件
- 让 Gazebo 能识别这台机械臂

如果你想加传感器、改机器人模型、换末端工具，通常从这里开始。

### `ur10_description/config/ros2_controllers.yaml`

这是控制器配置。

它告诉 `gazebo_ros2_control`：

- 需要哪些控制器
- 控制哪些关节
- 控制器叫什么名字

本项目最关键的是两个控制器：

- `joint_state_broadcaster`
- `joint_trajectory_controller`

### `ur10_moveit_config/launch/ur_moveit.launch.py`

这是 MoveIt 的启动入口。

它负责：

- 启动 `move_group`
- 加载 SRDF、OMPL、关节限制和控制器映射
- 根据参数决定是否启动 RViz

### `ur10_moveit_config/config/ompl_planning.yaml`

这是 OMPL 规划器的参数文件。

它控制：

- 用哪个 OMPL 规划器
- 规划器的默认配置
- 规划相关参数

当前默认使用的是：

```text
RRTConnectkConfigDefault
```

## 4. C++ 示例代码讲解

文件：

```text
ur10_examples/src/move_group_interface_demo.cpp
```

这个文件是 C++ 运动规划示例，核心流程可以理解为：

1. 初始化 ROS 2 节点
2. 从 `/move_group` 同步 MoveIt 参数
3. 创建 `MoveGroupInterface`
4. 等待当前关节状态可用
5. 等待障碍物 `pcd_obstacle_box` 出现在规划场景中
6. 设置关节目标
7. 请求规划
8. 执行轨迹

### 你最常会改哪里

#### 改默认目标关节值

看设置关节目标的那段代码。那里决定了机械臂最终想去的姿态。

#### 改规划组

看 `planning_group` 相关变量，默认应是：

```text
ur_manipulator
```

#### 改等待逻辑

如果你不想等待障碍物，或者想换障碍物名字，就看等待 `pcd_obstacle_box` 的那一段。

## 5. Python 示例代码讲解

文件：

```text
ur10_examples_py/ur10_examples_py/moveit_py_demo.py
```

这个文件是 Python 版本的运动规划示例。它的流程和 C++ 版很像：

1. 先做 Python 环境自举
2. 构造 `MoveItPy` 所需配置
3. 读取当前状态
4. 设置规划组
5. 设置目标关节
6. 调用规划
7. 调用执行

### 你最常会改哪里

#### 改默认目标

看目标关节数组或目标状态设置部分。

#### 改规划参数

看 `planning_pipeline`、`planner_id`、规划请求参数的设置部分。

## 6. 点云与障碍物代码讲解

### `synthetic_overhead_camera_node.cpp`

它负责：

- 发布一个稳定的俯视点云
- 话题默认是 `/overhead_camera/points`

你可以把它理解成“提供原始障碍物数据的相机”。

### `pcd_capture_node.cpp`

它负责：

- 订阅 `/overhead_camera/points`
- 接收到点云后写成 PCD 文件

输出文件默认是：

```text
/root/ur10_ws/data/latest_obstacle.pcd
```

### `pcd_to_collision_scene_node.cpp`

它负责：

- 读取 PCD 文件
- 从点云里提取工作台和障碍物
- 生成 `CollisionObject`
- 把障碍物送进 MoveIt 的 Planning Scene

这里最重要的输出对象是：

- `work_table`
- `pcd_obstacle_box`

### 点云链路怎么串起来

整条链路是：

1. `synthetic_overhead_camera_node` 发布点云
2. `pcd_capture_node` 把点云写成 PCD
3. `pcd_to_collision_scene_node` 读回 PCD
4. `pcd_to_collision_scene_node` 生成 `CollisionObject`
5. MoveIt 之后在规划时把这个障碍物当作碰撞体

## 7. 如果你想二次开发，最常改哪些文件

如果你想改启动逻辑，先看：

- `ur10_simulation_bringup/launch/complete_simulation.launch.py`

如果你想改机器人模型和控制器，先看：

- `ur10_description/urdf/ur10_sim.urdf.xacro`
- `ur10_description/config/ros2_controllers.yaml`

如果你想改 MoveIt 规划行为，先看：

- `ur10_moveit_config/launch/ur_moveit.launch.py`
- `ur10_moveit_config/config/ompl_planning.yaml`

如果你想改 C++ 默认轨迹，先看：

- `ur10_examples/src/move_group_interface_demo.cpp`

如果你想改 Python 默认轨迹，先看：

- `ur10_examples_py/ur10_examples_py/moveit_py_demo.py`

如果你想改障碍物导入逻辑，先看：

- `ur10_perception/src/pcd_capture_node.cpp`
- `ur10_perception/src/pcd_to_collision_scene_node.cpp`

下一篇建议阅读：[路径规划与避障原理](06_motion_planning_and_obstacle_avoidance.md)
