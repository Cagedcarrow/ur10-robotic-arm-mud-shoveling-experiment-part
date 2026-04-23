# `my_robot` 包分析

## 这篇文档解决什么问题

这篇文档专门解释 `my_robot` 这个包到底负责什么，以及为什么它是你现在最应该优先理解和维护的包。

## 一句话说，这个包是干什么的

`my_robot` 是当前“龙门架 + UR10 + 铲斗末端”整机系统的主模型包，也是 Gazebo 仿真主入口包。

## 标签

`当前主线`

## 它在整个工作区中的位置

如果把当前工作区理解成一个完整的整机仿真系统，那么：

- `my_robot` 负责“机器人实体本身”
- `my_robot_moveit_config` 负责“规划配置”
- `ur10_perception` 负责“世界和感知资源”
- `ur10_examples_py` 负责“辅助脚本和交互工具”

也就是说，`my_robot` 是整条主线里最靠前、最基础的那个包。

## 它主要包含什么

这个包最重要的内容主要分成 5 类。

### 1. 机器人描述

关键文件：

- `urdf/my_robot_macro.urdf.xacro`
- `urdf/my_robot_gantry.urdf.xacro`
- `my_robot.urdf.xacro`

它们分别负责：

- `my_robot_macro.urdf.xacro`
  - 定义 UR10 本体加铲斗的主体结构
  - 包括 link、joint、mesh、惯量、末端 frame、`ros2_control` 相关内容
- `my_robot_gantry.urdf.xacro`
  - 在主体结构外层再加上龙门架
  - 形成整机模型
- `my_robot.urdf.xacro`
  - 更像对主宏的直接入口封装

### 2. Gazebo 启动编排

关键文件：

- `launch/gazebo_gantry.launch.py`
- `launch/sim_planning_gantry.launch.py`

它们分别负责：

- `gazebo_gantry.launch.py`
  - 读取 `gantry_config.json`
  - 展开整机 Xacro
  - 启动 Gazebo
  - `spawn_entity`
  - 依次加载控制器并初始化 gantry
- `sim_planning_gantry.launch.py`
  - 把 Gazebo 仿真和 MoveIt 规划一起拉起来
  - 是当前最接近日常使用的一键入口

### 3. 控制器配置

关键文件：

- `config/ros2_controllers.yaml`
- `config/gantry_config.json`

作用分别是：

- `ros2_controllers.yaml`
  - 定义 `controller_manager` 下的控制器
  - 包括关节状态广播器、机械臂轨迹控制器、龙门轨迹控制器
- `gantry_config.json`
  - 定义 gantry 的初始位置和运动范围

### 4. 可视化资源

关键目录：

- `meshes/`
- `rviz/`

其中：

- `meshes/`
  - 提供 DAE 和 Gazebo 视觉 STL
  - 同时包含铲斗 `base_link.STL`
- `rviz/view_my_robot.rviz`
  - 是查看当前模型的 RViz 配置

### 5. 小工具脚本

关键文件：

- `scripts/shovel_tcp_slider.py`

这个脚本主要用来辅助调试铲斗末端相关局部坐标偏移，不是整机启动必需品，但对末端调试有帮助。

## 这个包和其他包的关系

### 和 `my_robot_moveit_config` 的关系

`my_robot` 提供模型本体，`my_robot_moveit_config` 在它之上提供规划配置。

没有 `my_robot`，`my_robot_moveit_config` 就没有可规划的实体模型基础。

### 和 `ur10_perception` 的关系

`my_robot` 默认使用 `ur10_perception` 提供的 world，例如 `gantry_only.world`。

### 和 `ur10_examples_py` 的关系

`my_robot` 启动链里会调用：

- `gantry_control`
- `gantry_rviz_control`

所以它会借助 `ur10_examples_py` 的工具脚本完成辅助动作。

### 和 `ur10_description` 的关系

可以把 `ur10_description` 看成原始 UR10 主线的描述层，而 `my_robot` 是你后续整理出来的当前整机主包。两者都属于“描述层”，但面对的是不同阶段的主线。

## 什么时候应该改这个包

当你想改下面这些内容时，优先看 `my_robot`：

- 机器人外形
- 龙门架结构
- 铲斗位置和末端 frame
- Gazebo 中整机怎么生成
- 控制器配置
- gantry 参数

## 什么时候不应该先改这个包

如果你想改的是：

- MoveIt 规划组
- SRDF 碰撞豁免
- OMPL 参数
- RViz MotionPlanning 配置

那优先应该看 `my_robot_moveit_config`，而不是先改 `my_robot`。

## 新手最容易混淆的点

### 1. 以为 `my_robot` 只是个 URDF 包

其实它不只是模型描述包，还承担了：

- Gazebo 启动编排
- 控制器配置
- gantry 参数入口

### 2. 以为 `my_robot.urdf.xacro` 就是全部

真正关键的逻辑更多在：

- `my_robot_macro.urdf.xacro`
- `my_robot_gantry.urdf.xacro`

### 3. 以为它和 `ur10_with_shovel` 是同一个方向

不是。

- `ur10_with_shovel` 更像铲斗专项线
- `my_robot` 是当前龙门架整机主线

## 如果你现在只能记住一句话

`my_robot` 就是当前整机系统里“最该先看、最该先改”的那个主包。
