# UR10 龙门架铲斗机器人 ROS 2 仿真工作区

`ROS 2 Humble + Gazebo Classic + MoveIt 2 + ros2_control`

这是一个围绕 **UR10 机械臂、三轴龙门架、铲斗末端执行器** 搭建的 ROS 2 仿真工作区。当前主线已经整理为 `my_robot` 系统：在 Gazebo Classic 中生成“龙门架 + UR10 + 铲斗”的整机模型，通过 `ros2_control` 加载控制器，并使用 MoveIt 2 与 RViz2 完成运动规划、状态观察和交互控制。

这个仓库不只是能跑的代码，也包含了大量中文说明文档，适合以后回顾“这个包是干什么的”“为什么 Gazebo 显示不出来”“应该从哪里改”。

## 项目亮点

- **整机仿真主线清晰**：当前推荐入口是 `my_robot`，对应“龙门架 + UR10 + 铲斗末端”组合机器人。
- **Gazebo Classic 快速启动**：已修复模型显示慢、mesh 路径异常、中文 link 名导致 Gazebo 卡住等问题。
- **完整模型显示**：Gazebo 中可以看到龙门架、UR10 本体和铲斗末端。
- **MoveIt 2 规划链路**：提供 `my_robot_moveit_config`，支持 RViz MotionPlanning 与 `move_group`。
- **ros2_control 控制器链路**：整机使用 `joint_state_broadcaster`、机械臂轨迹控制器和 gantry 三轴轨迹控制器。
- **龙门三轴控制**：支持启动时初始化 gantry，也支持脚本和 RViz interactive marker 交互控制。
- **感知与环境支撑**：保留 depth camera、点云、PCD、collision scene 相关工具和 world 资源。
- **中文文档体系完善**：包含功能包地图、Gazebo 显示修复备忘、机器人描述与 RViz 整理、龙门架构建笔记。

## 当前推荐启动方式

进入工作区后，先加载 ROS 2 和本工作空间环境：

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
```

启动当前主线完整系统：

```bash
ros2 launch my_robot sim_planning_gantry.launch.py gui:=true start_rviz:=true
```

这条命令会启动：

- Gazebo Classic 与整机模型
- `robot_state_publisher`
- `spawn_entity`
- `gazebo_ros2_control`
- `joint_state_broadcaster`
- `joint_trajectory_controller`
- `gantry_trajectory_controller`
- MoveIt `move_group`
- RViz2 MotionPlanning
- gantry RViz 交互控制工具

如果你只是想排查核心启动链路，可以先不开 GUI：

```bash
ros2 launch my_robot sim_planning_gantry.launch.py gui:=false start_rviz:=false
```

## 系统架构速览

可以把当前工程理解成下面这条链：

```text
my_robot
  ├── Xacro / URDF：描述龙门架、UR10、铲斗、关节和控制接口
  ├── Gazebo launch：启动仿真、生成机器人、加载控制器
  └── ros2_control：提供机械臂与 gantry 三轴控制接口

my_robot_moveit_config
  ├── SRDF：规划组、末端 link、碰撞豁免
  ├── OMPL / kinematics / joint limits：MoveIt 规划参数
  └── RViz config：MotionPlanning 可视化入口

ur10_perception
  ├── Gazebo world：基础世界和障碍物世界
  ├── depth camera / point cloud：感知数据来源
  └── PCD -> collision object：把点云障碍物导入 MoveIt 场景

ur10_examples_py
  ├── gantry_control：命令式控制 gantry 三轴
  ├── gantry_rviz_control：RViz 中拖拽控制 gantry
  └── moveit_py_demo / PCD tools：Python 示例与辅助工具
```

一句话理解：

> `my_robot` 负责“机器人实体和仿真”，`my_robot_moveit_config` 负责“规划大脑”，`ur10_perception` 负责“环境和感知”，`ur10_examples_py` 负责“操作工具”。

## 工作区功能包地图

当前 `src/` 下共有 9 个 ROS 2 功能包。

| 包名 | 当前定位 | 主要作用 | 推荐状态 |
| --- | --- | --- | --- |
| `my_robot` | 当前整机主包 | 龙门架 + UR10 + 铲斗模型、Gazebo 启动、控制器配置 | 当前主线 |
| `my_robot_moveit_config` | 当前 MoveIt 配置包 | `my_robot` 对应的 SRDF、OMPL、kinematics、RViz MotionPlanning | 当前主线 |
| `ur10_perception` | 环境与感知支撑包 | Gazebo world、depth camera、点云、PCD、collision scene | 基础支撑 |
| `ur10_examples_py` | Python 工具包 | gantry 控制、RViz 交互、MoveItPy 示例、PCD 辅助工具 | 当前主线 |
| `ur10_examples` | C++ 示例包 | C++ MoveGroupInterface 规划与执行示例 | 基础支撑 |
| `ur10_description` | 原始描述包 | 原始 UR10 + gantry 描述封装 | 基础支撑 / 历史主线 |
| `ur10_moveit_config` | 原始 MoveIt 配置包 | 原始 UR10 主线对应的 MoveIt 配置 | 基础支撑 / 历史主线 |
| `ur10_simulation_bringup` | 原始总启动包 | 原始 UR10 主线的 Gazebo、MoveIt、感知和示例编排 | 基础支撑 / 历史主线 |
| `ur10_with_shovel` | 铲斗专项包 | UR10 + 铲斗末端专项模型和 runbook | 历史 / 专项分支 |

如果你忘了某个包具体做什么，优先看：

- [工作区功能包分析](src/docs/工作区功能包分析/README.md)

## 三条工程主线

这个工作区经历过多轮演化，所以现在可以按 3 条线来理解。

## 1. 当前主线：`my_robot`

这是现在最推荐维护和使用的主线：

```text
my_robot + my_robot_moveit_config + ur10_perception + ur10_examples_py
```

它面向：

- 龙门架整机仿真
- UR10 倒装挂载
- 铲斗末端
- Gazebo + MoveIt + RViz 联动

## 2. 原始 UR10 仿真主线

这条线更偏基础和历史参考：

```text
ur10_description + ur10_moveit_config + ur10_simulation_bringup
```

它仍然有参考价值，尤其适合理解早期 UR10、gantry、MoveIt 和 perception 是怎么串起来的，但不再作为 GitHub 首页的默认推荐启动入口。

## 3. 铲斗专项线：`ur10_with_shovel`

这条线围绕“UR10 + 铲斗末端”展开，保留了铲斗接入、`shovel_tip`、专项 runbook 等历史信息。

它不是当前龙门架整机主线，但对理解铲斗末端演化非常有用。

## 文档导航

项目文档集中在 `src/docs/` 下：

- [Docs 总入口](src/docs/README.md)
- [工作区功能包分析](src/docs/工作区功能包分析/README.md)
- [Gazebo 显示与启动修复备忘](src/docs/gazebo_显示与启动修复备忘/README.md)
- [机器人描述与 RViz](src/docs/机器人描述与RViz/README.md)
- [my_robot 龙门架构建笔记](src/docs/my_robot_gantry_build_notes/00_总览.md)

推荐阅读顺序：

1. 如果你不知道包是干什么的，看 [工作区功能包分析](src/docs/工作区功能包分析/README.md)
2. 如果 Gazebo 启动慢、模型不显示、控制器不起来，看 [Gazebo 显示与启动修复备忘](src/docs/gazebo_显示与启动修复备忘/README.md)
3. 如果你想理解模型、mesh、RViz、末端坐标系，看 [机器人描述与 RViz](src/docs/机器人描述与RViz/README.md)
4. 如果你想理解龙门架怎么搭起来，看 [my_robot 龙门架构建笔记](src/docs/my_robot_gantry_build_notes/00_总览.md)

## 常见任务应该看哪里

| 你想做什么 | 优先看哪里 |
| --- | --- |
| 改机器人外形、link、joint、mesh | `src/my_robot_xacro/my_robot/urdf/` |
| 改 Gazebo 启动、spawn、控制器加载 | `src/my_robot_xacro/my_robot/launch/` |
| 改 gantry 初始位置和范围 | `src/my_robot_xacro/my_robot/config/gantry_config.json` |
| 改控制器配置 | `src/my_robot_xacro/my_robot/config/ros2_controllers.yaml` |
| 改 MoveIt 规划组、末端、碰撞豁免 | `src/my_robot_moveit_config/` |
| 改 world、depth camera、点云、PCD | `src/ur10_perception/` |
| 改 gantry 控制脚本或 RViz 交互工具 | `src/ur10_examples_py/` |
| 回顾旧 UR10 主线 | `src/ur10_description/`、`src/ur10_moveit_config/`、`src/ur10_simulation_bringup/` |
| 回顾铲斗专项历史 | `src/ur10_with_shovel/` |

更详细的维护指南见：

- [应该从哪里开始看，修改哪一层](src/docs/工作区功能包分析/10_应该从哪里开始看_修改哪一层.md)

## Gazebo 显示问题已经修复了什么

本仓库曾经遇到过 Gazebo 启动很慢、机械臂显示不完整、控制器不起来等问题，目前已经完成排查和修复。关键修复包括：

- 把中文 link 名 `铲子` 改成 Gazebo Classic 更稳定的 `shovel_link`
- 把铲斗 mesh URI 改成 Gazebo 更稳定的 `file://...`
- 把 world 中的 `ground_plane` 和 `sun` 改成内联定义，避免模型数据库等待
- 合并整机 `ros2_control` system，消除重复声明问题
- 总结了旧进程、旧服务、旧 launch 对排障的干扰方式

详细记录见：

- [Gazebo 显示与启动修复备忘](src/docs/gazebo_显示与启动修复备忘/README.md)

## 目录预览

```text
ur10_ws/
├── README.md
├── .gitignore
├── data/
├── src/
│   ├── docs/
│   ├── my_robot_moveit_config/
│   ├── my_robot_xacro/
│   │   └── my_robot/
│   ├── ur10_description/
│   ├── ur10_examples/
│   ├── ur10_examples_py/
│   ├── ur10_moveit_config/
│   ├── ur10_perception/
│   ├── ur10_simulation_bringup/
│   └── ur10_with_shovel/
```

`build/`、`install/`、`log/` 是 ROS 2/colcon 生成目录，已在 `.gitignore` 中忽略，通常不作为 GitHub 展示重点。

## 环境说明

当前工作区主要面向：

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic
- MoveIt 2
- ros2_control
- RViz2

如果你要重新构建，常用命令是：

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source /root/ur10_ws/install/setup.bash
```

## 维护建议

- 当前主线优先维护 `my_robot` 和 `my_robot_moveit_config`。
- 不确定某个包用途时，先看 [工作区功能包分析](src/docs/工作区功能包分析/README.md)。
- 遇到 Gazebo 显示或启动问题时，先看 [Gazebo 显示与启动修复备忘](src/docs/gazebo_显示与启动修复备忘/README.md)，不要直接盲改模型。
- 修改模型命名、mesh URI、world 文件、控制器配置时，建议同时做一次无 GUI 启动验证。
- 旧主线和专项线仍有参考价值，但不要把它们误认为当前默认入口。

## License

项目内自定义代码与文档按各 ROS 2 包 `package.xml` 中标记的许可证组织，当前主要为 `Apache-2.0` / `Apache2.0`。
