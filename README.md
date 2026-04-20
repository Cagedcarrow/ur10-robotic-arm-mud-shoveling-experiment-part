# UR10 ROS 2 Humble 仿真与避障工作区

基于 `ROS 2 Humble + Gazebo Classic + MoveIt2 + ros2_control` 的 UR10 仿真工作区，支持机械臂运动规划、C++ / Python 二次开发、俯视点云采集生成 PCD，以及将 PCD 回灌为 MoveIt 规划场景障碍物后继续执行避障规划。

## 项目亮点

- 支持 `ur_description` + `xacro` 方式生成 UR10 仿真模型
- 使用 `Gazebo Classic` 而不是 Ignition / Gazebo Sim
- 使用 `gazebo_ros2_control` 驱动 `joint_state_broadcaster` 和 `joint_trajectory_controller`
- 集成 `MoveIt2`，默认规划管线为 `OMPL`
- 提供 C++ `MoveGroupInterface` 示例节点
- 提供 Python `moveit_py` 示例节点
- 提供俯视点云采集、PCD 写盘、PCD 回灌规划场景障碍物的完整链路
- 提供一键总入口 `complete_simulation.launch.py`

## 已完成能力

- UR10 模型加载与 Gazebo Classic 仿真
- `ros2_control` 控制器管理
- MoveIt2 运动规划与 RViz 可视化
- C++ 运动规划与执行
- Python 运动规划与执行
- 点云采集生成 PCD
- PCD 回灌为规划场景障碍物
- 障碍物存在时的轨迹规划与执行

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

上面这条命令会自动完成：

1. 启动 Gazebo Classic 与 UR10
2. 启动 `move_group` 与 RViz
3. 生成 `/root/ur10_ws/data/latest_obstacle.pcd`
4. 将 PCD 回灌为规划场景障碍物
5. 自动运行 C++ 示例节点完成一次避障规划执行

如果要在同一套环境中追加运行 Python 示例：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash

ros2 run ur10_examples_py moveit_py_demo
```

更详细的使用方式见 [运行手册](docs/03_runbook.md)。

## 典型演示链路

### 一键自动链路

`complete_simulation.launch.py` 的默认行为是：

1. 启动 Gazebo 与 UR10 模型
2. 启动 `ros2_control` 控制器
3. 启动 `move_group`
4. 启动俯视点云节点
5. 生成 PCD 文件
6. 把 PCD 转为 `CollisionObject`
7. 自动运行 C++ 示例节点进行避障规划与执行

### 手动链路

如果要分步骤调试，可以：

- 单独启动仿真
- 单独启动 MoveIt
- 单独运行 C++ 示例
- 单独运行 Python 示例
- 单独运行 `capture_and_import_pcd`

具体命令见 [运行手册](docs/03_runbook.md)。

## 验收结果摘要

当前工作区已经完成并验证通过以下链路：

- `complete_simulation.launch.py` 自动启动 Gazebo、MoveIt、PCD 导入与 C++ 规划执行
- C++ 示例节点能够在障碍物存在时完成规划并执行
- Python `moveit_py_demo` 能够在已启动环境中完成规划并执行，退出码为 `0`
- PCD 文件成功生成于 `/root/ur10_ws/data/latest_obstacle.pcd`
- PCD 能成功导入为 `work_table` 与 `pcd_obstacle_box` 两个规划场景对象

## 文档导航

- [编译与重编指南](docs/01_build_and_rebuild_guide.md)
- [工作区结构说明](docs/02_workspace_structure.md)
- [运行手册](docs/03_runbook.md)
- [节点与 Launch 清单](docs/04_nodes_and_launches.md)

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
