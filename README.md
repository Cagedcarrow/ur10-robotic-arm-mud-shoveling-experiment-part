# UR10 ROS 2 Humble 龙门架仿真与实机通信工作区

基于 `ROS 2 Humble + Gazebo Classic + MoveIt2 + ros2_control` 的 UR10 工作区，当前默认提供“倒装龙门架 + UR10”的干净仿真场景，同时保留可选的点云/PCD 障碍物链路，并补充了接入实机 `ur_robot_driver` 的网线通信配置模板与说明文档。

## 项目亮点

- 支持 `ur_description` + `xacro` 方式生成 UR10 仿真模型
- 使用 `Gazebo Classic` 而不是 Ignition / Gazebo Sim
- 使用 `gazebo_ros2_control` 驱动 `joint_state_broadcaster` 和 `joint_trajectory_controller`
- 新增 3 轴龙门平移机构，UR10 倒装挂载在龙门末端
- 集成 `MoveIt2`，默认规划管线为 `OMPL`
- 提供 C++ `MoveGroupInterface` 示例节点
- 提供 Python `moveit_py` 示例节点
- 提供独立的龙门控制命令入口
- 提供 RViz2 中可拖拽的龙门 `X/Y/Z` 交互控制标记
- 提供 Gazebo 深度相机与独立深度图显示窗口
- 保留俯视点云采集、PCD 写盘、PCD 回灌规划场景障碍物的可选链路
- 提供实机网线通信配置模板与 `ur_robot_driver` 启动入口
- 提供一键总入口 `complete_simulation.launch.py`

## 已完成能力

- UR10 模型加载与 Gazebo Classic 仿真
- `ros2_control` 控制器管理
- MoveIt2 运动规划与 RViz 可视化
- C++ 运动规划与执行
- Python 运动规划与执行
- 龙门三轴独立控制
- RViz2 中的龙门三轴交互控制
- 深度相机图像与点云输出
- 实机通信配置模板
- 可选的点云采集生成 PCD
- 可选的 PCD 回灌为规划场景障碍物

## 工作区组成

| 包名 | 作用 |
| --- | --- |
| `ur10_description` | 项目级 UR10/UR10e 描述包装，提供 URDF/xacro 与控制器参数 |
| `ur10_moveit_config` | MoveIt2 配置、SRDF、OMPL 参数、控制器映射与 RViz 配置 |
| `ur10_simulation_bringup` | 顶层启动入口，串联 Gazebo、MoveIt、感知与示例节点 |
| `ur10_perception` | 俯视点云相机、PCD 采集、PCD 回灌碰撞场景 |
| `ur10_examples` | C++ `MoveGroupInterface` 示例 |
| `ur10_examples_py` | Python `moveit_py` 示例与 PCD 辅助工具 |

## 快速开始

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash

ros2 launch ur10_simulation_bringup complete_simulation.launch.py
```

上面这条命令默认会自动完成：

1. 启动 Gazebo Classic 与 UR10
2. 生成“纯龙门架 + 倒装 UR10”的干净场景
3. 启动 `move_group` 与 RViz
4. 激活 `joint_state_broadcaster`、`joint_trajectory_controller`、`gantry_trajectory_controller`
5. 将龙门自动移动到 launch 指定的初始 XYZ
6. 启动 RViz 中的龙门交互标记控制节点
7. 启动龙门内部区域深度相机，以及可选深度图窗口

运行后，如果你想手动移动龙门：

```bash
ros2 run ur10_examples_py gantry_control --ros-args -p x:=0.20 -p y:=0.00 -p z:=-0.70
```

如果要在同一套环境中追加运行 Python 规划示例：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash

ros2 run ur10_examples_py moveit_py_demo
```

更详细的使用方式见 [运行手册](docs/03_runbook.md)。

## 新手阅读顺序

如果你是 ROS 2 / MoveIt2 新手，推荐按下面顺序阅读：

1. [运行手册](docs/03_runbook.md)
2. [工作区结构说明](docs/02_workspace_structure.md)
3. [ROS 2 入门与本项目上手指南](docs/07_ros2_getting_started.md)
4. [代码讲解](docs/05_code_walkthrough.md)
5. [路径规划与避障原理](docs/06_motion_planning_and_obstacle_avoidance.md)
6. [实机网线通信与驱动启动](docs/08_real_robot_ethernet_and_driver.md)

这样可以先学会“怎么跑”，再学“代码在哪”，最后理解“为什么能规划和避障”。

## 系统工作流程

这套系统默认按下面顺序运行：

1. `complete_simulation.launch.py` 先清理旧的 Gazebo / MoveIt 残留进程
2. 启动 Gazebo Classic，并在世界里生成 UR10 机器人
3. `gazebo_ros2_control` 启动控制器，激活 `joint_state_broadcaster`、`joint_trajectory_controller` 和 `gantry_trajectory_controller`
4. 龙门初始化节点把 XYZ 移动到 launch 指定的初始位置
5. 启动 `move_group`，让 MoveIt 可以读取当前关节状态并准备规划
6. 如果你显式启用点云链路，再启动相机、PCD 采集和障碍物导入

## 典型使用链路

### 默认干净场景

`complete_simulation.launch.py` 的默认行为是：

1. 启动 Gazebo 与 UR10 模型
2. 启动龙门三轴和 UR 六轴控制器
3. 启动 `move_group`
4. 保持场景里只有地面、龙门架和 UR10

### 可选障碍物链路

如果要回到旧的点云/PCD 障碍物模式，可以在启动时显式开启：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py \
  world:=/root/ur10_ws/src/ur10_perception/worlds/obstacle_scene.world \
  enable_overhead_camera:=true \
  capture_pcd_on_start:=true \
  import_pcd_obstacle:=true
```

### 实机通信链路

如果你要连真实 UR10 控制器，请看：

- [实机网线通信与驱动启动](docs/08_real_robot_ethernet_and_driver.md)

## 手动链路

如果要分步骤调试，可以：

- 单独启动仿真
- 单独启动 MoveIt
- 单独运行 C++ 示例
- 单独运行 Python 示例
- 单独运行 `capture_and_import_pcd`

具体命令见 [运行手册](docs/03_runbook.md)。

## 窗口与进程排障

如果你遇到下面这些情况：

- Gazebo 窗口关不掉
- RViz 卡住不退出
- 深度图窗口还在
- 再次启动时提示 `Entity already exists`
- 再次启动时提示 `Controller already loaded`

请直接看：

- [运行手册](docs/03_runbook.md)
- [ROS 2 入门与本项目上手指南](docs/07_ros2_getting_started.md)

里面已经补了：

- 如何用 `ps` / `pgrep` / `ros2 node list` 查进程
- 如何安全结束当前 launch
- 如何用 `pkill` 精确关闭 Gazebo、RViz、深度窗口和示例节点

## 验收结果摘要

当前工作区已经完成并验证通过以下链路：

- `complete_simulation.launch.py` 自动启动 Gazebo、MoveIt、PCD 导入与 C++ 规划执行
- C++ 示例节点能够在障碍物存在时完成规划并执行
- Python `moveit_py_demo` 能够在已启动环境中完成规划并执行，退出码为 `0`
- PCD 文件成功生成于 `/root/ur10_ws/data/latest_obstacle.pcd`
- PCD 能成功导入为 `work_table` 与 `pcd_obstacle_box` 两个规划场景对象
- 龙门三轴可通过 `gantry_trajectory_controller` 独立控制
- 已补充实机网线通信配置模板与 `ur_robot_driver` 包装 launch

## 文档导航

- [编译与重编指南](docs/01_build_and_rebuild_guide.md)
- [Docs 导航](docs/README.md)
- [工作区结构说明](docs/02_workspace_structure.md)
- [运行手册](docs/03_runbook.md)
- [节点与 Launch 清单](docs/04_nodes_and_launches.md)
- [代码讲解](docs/05_code_walkthrough.md)
- [路径规划与避障原理](docs/06_motion_planning_and_obstacle_avoidance.md)
- [ROS 2 入门与本项目上手指南](docs/07_ros2_getting_started.md)
- [实机网线通信与驱动启动](docs/08_real_robot_ethernet_and_driver.md)

## 目录预览

```text
ur10_ws/
├── README.md
├── docs/
├── data/
├── src/
│   ├── ur10_description/
│   ├── ur10_examples/
│   ├── ur10_examples_py/
│   ├── ur10_moveit_config/
│   ├── ur10_perception/
│   └── ur10_simulation_bringup/
├── build/
├── install/
└── log/
```

## 许可

项目内自定义代码与文档按各包内 `package.xml` 标记的 `Apache-2.0` 组织。
