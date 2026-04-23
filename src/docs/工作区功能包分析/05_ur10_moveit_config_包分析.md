# `ur10_moveit_config` 包分析

## 这篇文档解决什么问题

这篇文档解释原始 UR10 主线里的 MoveIt 配置层是怎么组织的，以及它和 `my_robot_moveit_config` 有什么区别。

## 一句话说，这个包是干什么的

`ur10_moveit_config` 是原始 UR10 仿真主线对应的 MoveIt 配置包。

## 标签

`基础支撑`

## 它在整个工作区中的位置

这个包和 `ur10_description` 配套，构成原始主线中的：

- 机器人描述层
- MoveIt 配置层

## 主要文件和入口说明

### `launch/ur_moveit.launch.py`

这是本包最重要的入口。

它负责：

- 启动 `move_group`
- 组织 MoveIt 所需参数
- 启动 RViz MotionPlanning

### `srdf/ur.srdf.xacro`

是主 SRDF 入口。

### `srdf/ur_macro.srdf.xacro`

定义语义层细节，例如：

- 规划组
- 末端
- disable collisions

### `config/kinematics.yaml`

定义运动学求解配置。

### `config/joint_limits.yaml`

定义规划时的关节限制。

### `config/ompl_planning.yaml`

定义 OMPL 规划参数。

### `config/moveit_controllers.yaml` 与 `config/controllers.yaml`

定义 MoveIt 与控制器之间的映射关系。

### `config/ur_servo.yaml`

说明这个包还考虑了 MoveIt Servo 相关配置。

## 这个包和其他包的关系

### 和 `ur10_description` 的关系

它依赖 `ur10_description` 提供机器人描述。

### 和 `ur10_simulation_bringup` 的关系

在原始主线里，`ur10_simulation_bringup` 会调用它来完成规划与 RViz 部分。

### 和 `my_robot_moveit_config` 的关系

两者角色类似，但服务对象不同：

- `ur10_moveit_config`
  - 对应原始 UR10 主线
- `my_robot_moveit_config`
  - 对应当前 `my_robot` 整机主线

## 什么时候应该改这个包

如果你在维护：

- 原始 UR10 主线的 MoveIt 配置
- 基础规划参数
- 旧主线的 RViz MotionPlanning 配置

那应该看这个包。

## 什么时候不应该先改这个包

如果你现在主要跑的是 `my_robot` 组合整机，就不要先在这里改规划组或末端配置，除非你明确知道自己在回修旧主线。

## 新手最容易混淆的点

### 1. 以为它和 `my_robot_moveit_config` 只是包名不同

不是。

它们虽然都叫 MoveIt config package，但面向的机器人结构和主线不同。

### 2. 以为原始主线配置就一定能直接套到当前整机主线

不一定，因为当前整机主线包含了你后续整理出来的 `my_robot` 结构和约定。

## 如果你现在只能记住一句话

`ur10_moveit_config` 是原始 UR10 路线的 MoveIt 配置基础，不是当前 `my_robot` 主线的首选修改点。
