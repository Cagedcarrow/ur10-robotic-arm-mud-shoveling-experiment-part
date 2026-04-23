# `my_robot_moveit_config` 包分析

## 这篇文档解决什么问题

这篇文档解释 `my_robot_moveit_config` 是干什么的，以及它和 `my_robot` 的边界在哪里。

## 一句话说，这个包是干什么的

`my_robot_moveit_config` 是当前 `my_robot` 整机系统对应的 MoveIt 配置包，负责规划、控制器映射、RViz MotionPlanning 配置和语义描述。

## 标签

`当前主线`

## 它在整个工作区中的位置

如果说：

- `my_robot` 负责“机器人长什么样”

那么：

- `my_robot_moveit_config` 负责“MoveIt 应该怎样理解和规划这台机器人”

所以它是 `my_robot` 主线中的配置层，而不是实体层。

## 主要文件和入口说明

### `launch/my_robot_moveit.launch.py`

这是最关键的入口。

它负责：

- 读取 gantry 配置
- 展开 `my_robot` 的 robot_description
- 展开自己的 SRDF
- 组织 MoveIt 所需的一整套参数
- 启动 `move_group`
- 启动 RViz
- 可选启动 `gantry_rviz_control`

### `srdf/my_robot.srdf.xacro`

这是语义描述层。

它负责：

- 定义规划组
- 指定末端 `tip_link`
- 定义一些预设姿态
- 指定 disable collisions

### `config/kinematics.yaml`

定义逆解求解器和运动学相关参数。

### `config/joint_limits.yaml`

定义规划阶段使用的关节限制。

### `config/ompl_planning.yaml`

定义 OMPL 规划器参数。

### `config/moveit_controllers.yaml`

告诉 MoveIt：

- 执行轨迹时应该对接哪个控制器

### `rviz/view_robot.rviz`

这是 MotionPlanning 视图的 RViz 配置文件。

## 这个包和其他包的关系

### 和 `my_robot` 的关系

这是最直接的一对：

- `my_robot` 提供 robot_description
- `my_robot_moveit_config` 提供 robot_description_semantic 和规划相关配置

两者必须配套理解，不能只看一个。

### 和 `ur10_examples_py` 的关系

这个包的启动过程中，会让 RViz 交互控制工具和 MoveIt 规划链配合。

### 和 `ur10_moveit_config` 的关系

这两个包名字很像，但服务对象不同：

- `ur10_moveit_config` 面向原始 UR10 主线
- `my_robot_moveit_config` 面向 `my_robot` 组合整机主线

## 什么时候应该改这个包

如果你想改：

- 规划组
- 末端 link
- 碰撞豁免
- RViz MotionPlanning 配置
- MoveIt 控制器映射
- 运动学参数
- OMPL 参数

优先看这个包。

## 什么时候不应该先改这个包

如果你想改：

- 铲斗实际安装位置
- 龙门架结构
- robot_description 的 link/joint
- Gazebo 控制器本体定义

优先应该先看 `my_robot`。

## 新手最容易混淆的点

### 1. 以为 MoveIt config 包会生成机器人

不会。

它不会负责在 Gazebo 中生成机器人实体，也不会直接定义 link/joint 本体。

### 2. 以为 SRDF 是“可选附加项”

实际上 SRDF 对 MoveIt 非常关键。没有它，规划组、末端语义、碰撞豁免这些都不完整。

### 3. 以为 `my_robot_moveit_config` 和 `ur10_moveit_config` 可以随便混用

不能直接混用，因为它们面对的机器人结构不是完全一样的。

## 如果你现在只能记住一句话

`my_robot_moveit_config` 不是“机器人本体包”，而是“当前整机主线的 MoveIt 大脑配置包”。
