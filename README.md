# UR10 工作区总览（最新版）

`ROS 2 Humble + Gazebo Classic + MoveIt 2 + ros2_control`

这是 `ur10_ws` 的最新总入口文档。本文重点解决四件事：

1. 每个功能包是干什么的、彼此关系是什么。
2. 当前“主线 / 历史线 / 专项线”怎么划分。
3. 如何用最短命令快速启动，并理解每条命令在做什么。
4. 如何做测试与验证（自动化测试 / 烟测 / 实机验证）。

---

## 阅读路径（按角色）

### 新手（先跑起来）
1. 看“快速启动命令（含含义）”。
2. 运行“主线一键启动”。
3. 看“测试与验证”做基础烟测。

### 开发者（要改代码）
1. 看“功能包地图（逐包解释）”。
2. 看“三条主线与边界”。
3. 按“常见修改任务入口”定位目录。

### 论文整理
1. 看 [本项目原理详细说明](论文项目/本项目原理详细说明.md)。
2. 看 [本项目节点与调度详解](论文项目/本项目节点与调度详解.md)。
3. 写作时可参考 [Markdown语法说明教学](论文项目/Markdown语法说明教学.md)。

---

## 快速启动命令（含含义）

### 1) 构建工作区

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source /root/ur10_ws/install/setup.bash
```

含义：
- `source /opt/ros/humble/setup.bash`：加载 ROS 2 基础环境。
- `colcon build --symlink-install`：编译 `src` 下所有 ROS 包。
- `source /root/ur10_ws/install/setup.bash`：把本工作区的包注册到当前终端。

### 2) 主线仿真一键启动（推荐）

```bash
ros2 launch my_robot sim_planning_gantry.launch.py gui:=true start_rviz:=true
```

含义：
- 启动 `my_robot` 主线：Gazebo + 机器人实体 + 控制器 + MoveIt + RViz。
- `gui:=true`：打开 Gazebo 客户端窗口。
- `start_rviz:=true`：启动 RViz MotionPlanning 可视化。

### 3) 无 GUI 烟测启动（排障推荐）

```bash
ros2 launch my_robot sim_planning_gantry.launch.py gui:=false start_rviz:=false
```

含义：
- 仅验证核心启动链（模型、控制器、move_group）是否起来。
- 适合服务器环境或快速排查“是否能起系统”。

### 4) 原始总编排链启动（历史通用线）

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false
```

含义：
- 启动原始 UR10 总编排链：Gazebo、MoveIt、可选感知、可选 demo。
- 常用于兼容旧流程、复现实验或对照主线行为。

### 5) 实机验证入口

```bash
cd /root/ur10_ws/src/ur10_real_comm/scripts
chmod +x run_full_verify.sh
./run_full_verify.sh
```

含义：
- 调用实机总流程：UR 驱动 + MoveIt + `motion_verify_node` 微动验证。
- 最终通过 `/ur10_real_comm/status` 收敛 PASS/FAIL，并输出 `[SUMMARY]`。

### 6) 一体化 GUI 入口

```bash
cd /root/ur10_ws/src/ur10_unified_gui
python3 main.py
```

含义：
- 提供 Real/Sim 双模式统一入口。
- 支持快速网络检查、启动/停止流程、日志导出、参数持久化。

### 7) 如果你使用 `moveit_ws` 源码版 MoveIt（overlay）

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

含义：
- 让 `ur10_ws` 的业务包继续可用，同时 MoveIt 核心库优先来自 `moveit_ws` 源码编译版本。

快速确认：

```bash
ros2 pkg prefix moveit_ros_planning
```

期望路径：`/root/moveit_ws/install/moveit_ros_planning`

---

## 三条主线与边界

### A. 当前主线（推荐默认）

```text
my_robot + my_robot_moveit_config + ur10_perception + ur10_examples_py
```

用途：
- 龙门架 + UR10 + 铲斗末端整机仿真。
- Gazebo 执行、MoveIt 规划、RViz 观察、Python 工具交互。

### B. 历史通用线（兼容/对照）

```text
ur10_description + ur10_moveit_config + ur10_simulation_bringup
```

用途：
- 原始 UR10 主线的基础流程与总启动编排。
- 适合做旧流程复现、回归对照、历史配置参考。

### C. 专项线（特定任务）

```text
ur10_with_shovel + ur10_real_comm
```

用途：
- `ur10_with_shovel`：铲斗专项模型与历史启动工具。
- `ur10_real_comm`：实机通信与微动验证闭环。

---

## 功能包地图（逐包解释）

> 说明：以下“包”按 `src/*/package.xml` 的 ROS 包统计。

### 1) `my_robot`（目录：`src/my_robot_xacro/my_robot`）
- 定位：当前整机主包（龙门 + UR10 + 铲斗）
- 主要入口：
  - `launch/sim_planning_gantry.launch.py`
  - `launch/gazebo_gantry.launch.py`
- 依赖关系：被 `my_robot_moveit_config` 和 `ur10_examples_py` 联动使用
- 是否主线：是

### 2) `my_robot_moveit_config`
- 定位：当前主线 MoveIt 配置包
- 主要入口：`launch/my_robot_moveit.launch.py`
- 关键内容：SRDF、OMPL、kinematics、RViz 配置、控制器映射
- 是否主线：是

### 3) `ur10_perception`
- 定位：感知与障碍物处理支撑包
- 主要入口：
  - `launch/perception_only.launch.py`
  - C++ 节点：`pcd_capture_node`、`pcd_to_collision_scene_node`、`synthetic_overhead_camera_node`
- 是否主线：是（支撑层）

### 4) `ur10_examples_py`
- 定位：Python 工具与示例包
- 主要可执行：`gantry_control`、`gantry_rviz_control`、`moveit_py_demo`、`depth_image_viewer`
- 是否主线：是（工具层）

### 5) `ur10_examples`
- 定位：C++ MoveIt 示例包
- 主要可执行：`move_group_interface_demo`
- 是否主线：辅助/基础

### 6) `ur10_description`
- 定位：原始 UR10 描述封装（历史通用线基础）
- 主要入口：`launch/view_description.launch.py`
- 是否主线：历史通用线

### 7) `ur10_moveit_config`
- 定位：原始 UR10 MoveIt 配置包
- 主要入口：`launch/ur_moveit.launch.py`
- 是否主线：历史通用线

### 8) `ur10_simulation_bringup`
- 定位：原始 UR10 总编排包
- 主要入口：
  - `launch/complete_simulation.launch.py`
  - `launch/gazebo_sim.launch.py`
  - `launch/moveit_planning.launch.py`
- 是否主线：历史通用线

### 9) `ur10_real_comm`
- 定位：实机通信 + 微动验证包
- 主要入口：
  - `launch/real_comm_moveit_verify.launch.py`
  - `scripts/run_full_verify.sh`
  - `ur10_real_comm/motion_verify_node.py`
- 是否主线：专项线（实机）

### 10) `ur10_with_shovel`
- 定位：UR10 + 铲斗专项模型和历史启动工具
- 主要入口：`launch/sim_planning_shovel.launch.py` 等
- 是否主线：专项线（历史专项）

---

## `src` 目录中的非 ROS 包目录说明

这些目录不属于“ROS 包地图”，但很重要：

- `src/docs/`：工程文档（功能包分析、Gazebo 排障、模型说明等）
- `src/learn_docs/`：通用学习笔记
- `src/build/`、`src/install/`、`src/log/`：构建与运行产物
- `src/ur10_unified_gui/`：独立 GUI 工具目录（当前未封装成 ROS 包）

---

## 测试与验证

### 1) 自动化测试（GUI）

命令：

```bash
cd /root/ur10_ws/src/ur10_unified_gui
python3 -m py_compile main.py config_schema.py tests/test_unified_gui.py
python3 -m pytest -q tests/test_unified_gui.py
```

用途：
- 验证 GUI 关键逻辑：互斥、停止、配置持久化、summary 解析、脚本回退。

通过判据：
- `pytest` 显示全部用例通过。

### 2) 系统烟测（无可视化）

命令：

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
timeout 45s ros2 launch ur10_simulation_bringup moveit_planning.launch.py start_rviz:=false
```

用途：
- 快速验证 move_group + OMPL 管线是否可起。

通过判据：
- 日志出现 `Using planning interface 'OMPL'`。
- 日志出现 `You can start planning now!`。
- 若 `timeout` 返回 `124` 且上述日志已出现，视为“超时主动停止”而非失败。

### 3) 实机验证

命令：

```bash
cd /root/ur10_ws/src/ur10_real_comm/scripts
./run_full_verify.sh
```

用途：
- 完整实机验证闭环（驱动 + MoveIt + 微动执行 + 状态汇总）。

通过判据：
- `/ur10_real_comm/status` 出现终态。
- 脚本输出 `[SUMMARY] state=PASS|FAIL ...`。

### 4) 测试矩阵

| 目标 | 命令 | 预期信号 | 失败定位入口 |
| --- | --- | --- | --- |
| GUI 逻辑回归 | `python3 -m pytest -q tests/test_unified_gui.py` | 用例全部通过 | `src/ur10_unified_gui/tests/` |
| MoveIt 烟测 | `timeout 45s ros2 launch ... moveit_planning.launch.py start_rviz:=false` | OMPL 启动日志 + 可规划日志 | `src/ur10_simulation_bringup/launch/` |
| 实机微动闭环 | `./run_full_verify.sh` | `[SUMMARY] state=PASS/FAIL` | `/tmp/ur10_real_comm_launch.log` + `ur10_real_comm` |

---

## 常见修改任务入口

| 你想改什么 | 优先目录 |
| --- | --- |
| 机器人几何、关节、末端 | `src/my_robot_xacro/my_robot/urdf/` |
| Gazebo 启动与 spawn 顺序 | `src/my_robot_xacro/my_robot/launch/` |
| MoveIt 规划组、末端、碰撞豁免 | `src/my_robot_moveit_config/` |
| 原始 UR10 主线配置 | `src/ur10_moveit_config/` + `src/ur10_simulation_bringup/` |
| 感知与点云障碍处理 | `src/ur10_perception/` |
| 龙门控制与 Python 示例 | `src/ur10_examples_py/` |
| 实机通信与微动验证 | `src/ur10_real_comm/` |
| 一体化流程 GUI | `src/ur10_unified_gui/` |

---

## 文档导航

### 工程文档
- [src/docs 总入口](src/docs/README.md)
- [工作区功能包分析](src/docs/工作区功能包分析/README.md)
- [Gazebo 显示与启动修复备忘](src/docs/gazebo_显示与启动修复备忘/README.md)
- [机器人描述与 RViz](src/docs/机器人描述与RViz/README.md)
- [my_robot 龙门架构建笔记](src/docs/my_robot_gantry_build_notes/00_总览.md)

### 论文文档
- [本项目原理详细说明](论文项目/本项目原理详细说明.md)
- [本项目节点与调度详解](论文项目/本项目节点与调度详解.md)
- [Markdown语法说明教学](论文项目/Markdown语法说明教学.md)

---

## 环境基线

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic
- MoveIt 2
- ros2_control
- RViz2

---

## License

自定义代码与文档遵循各功能包 `package.xml` 中标注的许可证，当前主要为 `Apache-2.0` / `Apache2.0`。
