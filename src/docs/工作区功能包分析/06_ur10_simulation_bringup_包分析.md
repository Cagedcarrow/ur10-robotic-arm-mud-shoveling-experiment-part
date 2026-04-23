# `ur10_simulation_bringup` 包分析

## 这篇文档解决什么问题

这篇文档解释 `ur10_simulation_bringup` 为什么不是“普通 launch 包”，而是原始 UR10 主线里的总编排层。

## 一句话说，这个包是干什么的

`ur10_simulation_bringup` 是原始 UR10 仿真主线的总启动编排包，负责把 Gazebo、MoveIt、示例脚本、感知工具和清理逻辑串成一条完整流程。

## 标签

`基础支撑`

## 它在整个工作区中的位置

这个包更像一个“总调度器”：

- 底下真实干活的是描述包、MoveIt 包、感知包、示例包
- 它负责把这些东西按时序组合起来

## 主要文件和入口说明

### `launch/complete_simulation.launch.py`

这是本包最关键的总入口。

它负责：

- 可选清理旧进程
- 延时拉起 Gazebo
- 延时拉起 MoveIt
- 再继续拉起 demo 节点、感知节点和辅助工具

它最大的特点是：

- 已经显式考虑了多进程系统的启动顺序
- 还包含对残留进程的清理逻辑

### `launch/gazebo_sim.launch.py`

负责原始主线里的 Gazebo 仿真部分。

包括：

- 展开 `ur10_description`
- 启动 Gazebo
- `spawn_entity`
- 加载控制器
- 初始化 gantry

### `launch/moveit_planning.launch.py`

负责原始主线里的 MoveIt 规划部分。

它本质上是一个包装层，会去调用 `ur10_moveit_config`。

### `launch/demo_nodes.launch.py`

负责原始主线中的 demo 和辅助节点。

### `launch/real_robot_driver.launch.py`

说明这个包还为真实机器人链路做了准备。

## 这个包和其他包的关系

### 和 `ur10_description` 的关系

它用 `ur10_description` 作为底层机器人描述来源。

### 和 `ur10_moveit_config` 的关系

它用 `ur10_moveit_config` 来完成规划配置层。

### 和 `ur10_examples`、`ur10_examples_py` 的关系

它会调这些示例和工具节点，完成演示或辅助控制。

### 和 `ur10_perception` 的关系

它也会把 perception/world 资源串起来。

## 特别值得记住的一点：它有清理残留进程的逻辑

`complete_simulation.launch.py` 里有专门的进程清理步骤，用来避免：

- 第二次启动时连接到旧 Gazebo
- 连接到旧 controller_manager
- demo 脚本串到旧环境

这说明作者已经意识到：

- 这套系统是多进程、多节点、强时序的
- 如果不先清环境，验证结果很容易被污染

这也是为什么它不像“一个普通 launch 文件”那么简单。

## 什么时候应该改这个包

如果你想改：

- 原始主线的一键启动编排
- 多组件启动顺序
- demo/感知/规划是否一起拉起

就应该看它。

## 什么时候不应该先改这个包

如果你现在只想改：

- 当前 `my_robot` 主线的模型
- 当前 `my_robot` 主线的 MoveIt 配置

那通常不用先改这个包。

## 新手最容易混淆的点

### 1. 以为这个包本身提供机器人模型

实际上它更多是 orchestration，也就是总编排。

### 2. 以为它和 `my_robot` 主线是同一套入口

不是。

它更偏原始主线的总入口，而 `my_robot` 现在有自己的主入口。

## 如果你现在只能记住一句话

`ur10_simulation_bringup` 不是“描述层”，也不是“规划层”，而是原始 UR10 主线的总调度包。
