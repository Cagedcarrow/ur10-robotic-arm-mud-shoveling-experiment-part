# 工作区结构说明

适合谁看：已经能把系统跑起来，想知道“代码放在哪、改哪个文件”的读者。

本文档说明 `/root/ur10_ws` 的目录结构、各 ROS 包职责，以及关键文件的用途和调用关系。

相关文档：

- [编译与重编指南](01_build_and_rebuild_guide.md)
- [运行手册](03_runbook.md)
- [节点与 Launch 清单](04_nodes_and_launches.md)
- [代码讲解](05_code_walkthrough.md)

## 1. 工作区顶层目录

| 路径 | 作用 |
| --- | --- |
| `src/` | 源码目录，包含 6 个自定义 ROS 包 |
| `build/` | `colcon build` 产生的中间构建目录 |
| `install/` | 工作区安装空间，运行时 `source` 的主要目标 |
| `log/` | `colcon` 构建日志目录 |
| `data/` | 运行时生成的 PCD 数据目录，例如 `latest_obstacle.pcd` |
| `README.md` | GitHub 首页总览文档 |
| `docs/` | 详细中文说明文档目录 |

## 2. 新手先看哪些文件

如果你刚接触这套代码，建议先按下面顺序看：

1. `ur10_simulation_bringup/launch/complete_simulation.launch.py`
2. `ur10_simulation_bringup/launch/gazebo_sim.launch.py`
3. `ur10_moveit_config/launch/ur_moveit.launch.py`
4. `ur10_examples/src/move_group_interface_demo.cpp`
5. `ur10_examples_py/ur10_examples_py/moveit_py_demo.py`
6. `ur10_perception/src/pcd_capture_node.cpp`
7. `ur10_perception/src/pcd_to_collision_scene_node.cpp`

可以把它理解成三层：

- `launch` 文件负责把系统串起来
- 配置文件负责提供参数
- 源码文件负责真正执行行为

## 3. ROS 包概览

### `ur10_description`

职责：

- 封装项目级 UR10/UR10e 模型描述
- 管理 `xacro`、初始位姿和 `ros2_control` 控制器配置

关键文件：

- `urdf/ur10_sim.urdf.xacro`
  - 项目主机器人描述文件
  - 什么时候需要改它：当你要改模型、传感器、`gazebo_ros2_control` 插件或机器人类型时
- `config/ros2_controllers.yaml`
  - Gazebo 仿真控制器配置
  - 什么时候需要改它：当你要改控制器名字、控制频率、关节列表时
- `config/initial_positions.yaml`
  - 初始关节位置
  - 什么时候需要改它：当你想改变机器人初始姿态时
- `launch/view_description.launch.py`
  - 仅查看模型与关节状态的轻量启动
  - 什么时候需要改它：一般不用改，只在单独调试 URDF 时使用

### `ur10_moveit_config`

职责：

- 提供 MoveIt2 的 SRDF、OMPL 配置、控制器映射和 RViz 配置

关键文件：

- `launch/ur_moveit.launch.py`
  - 启动 `move_group` 和 RViz
  - 什么时候需要改它：当你要改 MoveIt 参数组织方式或启动选项时
- `config/ompl_planning.yaml`
  - OMPL 规划参数
  - 什么时候需要改它：当你要改规划器、采样策略、规划时间时
- `config/kinematics.yaml`
  - 运动学求解器配置
  - 什么时候需要改它：当你要换 IK 求解器时
- `config/joint_limits.yaml`
  - MoveIt 关节限制
  - 什么时候需要改它：当你要调整速度、加速度或关节限制时
- `config/moveit_controllers.yaml`
  - MoveIt 控制器映射
  - 什么时候需要改它：当你要换执行控制器名字时
- `srdf/ur.srdf.xacro`
  - 语义模型描述
  - 什么时候需要改它：当你要改规划组、末端执行器或禁碰规则时
- `rviz/view_robot.rviz`
  - MoveIt RViz 预设
  - 什么时候需要改它：当你想调整 RViz 默认显示内容时

### `ur10_simulation_bringup`

职责：

- 作为项目总入口，串联 Gazebo、MoveIt、感知与示例节点

关键文件：

- `launch/complete_simulation.launch.py`
  - 一键总启动文件
  - 什么时候需要改它：当你要改变整套系统的启动顺序、自动清理逻辑、自动示例行为时
- `launch/gazebo_sim.launch.py`
  - 启动 Gazebo、机器人模型和控制器
  - 什么时候需要改它：当你要改变仿真世界、机器人加载方式、控制器时序时
- `launch/moveit_planning.launch.py`
  - 启动 MoveIt2 规划环境
  - 什么时候需要改它：当你要改变是否启动 RViz、MoveIt 参数源时
- `launch/demo_nodes.launch.py`
  - 启动 C++ / Python 示例节点
  - 什么时候需要改它：当你要改变示例节点参数、是否等待障碍物时

### `ur10_perception`

职责：

- 提供俯视点云数据、PCD 写盘与障碍物回灌

关键文件：

- `src/synthetic_overhead_camera_node.cpp`
  - 发布俯视点云
  - 什么时候需要改它：当你要改点云内容、话题名或相机位置时
- `src/pcd_capture_node.cpp`
  - 订阅点云并保存为 PCD
  - 什么时候需要改它：当你要改保存路径、采样策略或点云输入时
- `src/pcd_to_collision_scene_node.cpp`
  - 将 PCD 转换为规划场景障碍物
  - 什么时候需要改它：当你要改障碍物提取算法、包围盒逻辑或场景对象名字时
- `launch/perception_only.launch.py`
  - 单独启动感知链路
  - 什么时候需要改它：当你要单独调试点云链路时
- `urdf/overhead_depth_camera.xacro`
  - 俯视相机描述
  - 什么时候需要改它：当你要把相机改成真实 Gazebo 深度相机模型时
- `worlds/obstacle_scene.world`
  - 含工作台与障碍物的 Gazebo 场景
  - 什么时候需要改它：当你要增加、删除或移动世界障碍物时
- `config/camera_topics.yaml`
  - 点云话题相关参数
  - 什么时候需要改它：当你要统一话题名和 frame 设置时

### `ur10_examples`

职责：

- 提供 C++ `MoveGroupInterface` 示例

关键文件：

- `src/move_group_interface_demo.cpp`
  - C++ 规划与执行示例节点
  - 什么时候需要改它：当你要修改默认目标、等待逻辑、规划触发方式时

### `ur10_examples_py`

职责：

- 提供 Python `moveit_py` 示例和 PCD 辅助工具

关键文件：

- `ur10_examples_py/moveit_py_demo.py`
  - Python 规划执行示例
  - 什么时候需要改它：当你要改 Python 侧默认目标和规划参数时
- `ur10_examples_py/capture_and_import_pcd.py`
  - 一次性完成 PCD 采集与导入
  - 什么时候需要改它：当你要把点云采集和场景导入串成自己的脚本时
- `ur10_examples_py/env_bootstrap.py`
  - Python 环境自举工具
  - 什么时候需要改它：通常不用改，除非 Python 环境路径发生变化

## 4. 关键文件的使用关系

### 总启动链

`complete_simulation.launch.py` 是整个系统的主入口，它依次串联：

1. 启动前清理旧的 Gazebo / MoveIt 残留进程
2. `gazebo_sim.launch.py`
3. `synthetic_overhead_camera_node`
4. `moveit_planning.launch.py`
5. `pcd_capture_node`
6. `pcd_to_collision_scene_node`
7. `demo_nodes.launch.py`

### C++ 规划链

`move_group_interface_demo.cpp` 的核心流程是：

1. 同步 `/move_group` 参数
2. 获取当前状态
3. 等待 `pcd_obstacle_box`
4. 设置关节目标
5. 调用 MoveIt 规划
6. 执行轨迹

### Python 规划链

`moveit_py_demo.py` 的核心流程是：

1. 自举 Python / ROS 环境
2. 构造 `MoveItPy` 配置
3. 获取当前状态
4. 设置规划组与目标关节
5. 生成规划
6. 调用执行

### 感知链

点云与 PCD 链路是：

1. `synthetic_overhead_camera_node` 发布 `/overhead_camera/points`
2. `pcd_capture_node` 写入 `/root/ur10_ws/data/latest_obstacle.pcd`
3. `pcd_to_collision_scene_node` 导入 `work_table` 和 `pcd_obstacle_box`

## 5. 文件使用建议

如果你要修改模型和控制器，优先查看：

- `ur10_description/urdf/ur10_sim.urdf.xacro`
- `ur10_description/config/ros2_controllers.yaml`

如果你要修改规划行为，优先查看：

- `ur10_moveit_config/launch/ur_moveit.launch.py`
- `ur10_moveit_config/config/ompl_planning.yaml`
- `ur10_examples/src/move_group_interface_demo.cpp`
- `ur10_examples_py/ur10_examples_py/moveit_py_demo.py`

如果你要修改障碍物感知和 PCD 导入，优先查看：

- `ur10_perception/src/synthetic_overhead_camera_node.cpp`
- `ur10_perception/src/pcd_capture_node.cpp`
- `ur10_perception/src/pcd_to_collision_scene_node.cpp`
- `ur10_perception/worlds/obstacle_scene.world`

下一篇建议阅读：[代码讲解](05_code_walkthrough.md)
