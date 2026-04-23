# `ur10_examples` 与 `ur10_examples_py` 包分析

## 这篇文档解决什么问题

这篇文档把两个容易被低估的包放在一起讲清楚：

- `ur10_examples`
- `ur10_examples_py`

它们名字里都带 `examples`，但实际作用并不只是“看一眼就删”的 demo。

## 一句话说，这两个包是干什么的

- `ur10_examples` 是 C++ 版 MoveGroupInterface 示例包。
- `ur10_examples_py` 是 Python 版示例加实用工具包，当前实际使用价值更高。

## 标签

- `ur10_examples`：`基础支撑`
- `ur10_examples_py`：`当前主线`

## 它们在整个工作区中的位置

这两个包都更偏“使用层”和“工具层”，不负责定义机器人本体，但负责：

- 调规划
- 控控制器
- 做演示
- 提供交互辅助工具

## `ur10_examples`：C++ 示例包

### 核心文件

- `src/move_group_interface_demo.cpp`

### 主要作用

这个程序会：

- 同步 `/move_group` 参数
- 构建 MoveGroupInterface
- 规划并可选执行轨迹
- 可选等待障碍物出现在规划场景中

所以它其实不只是“Hello MoveIt”，而是一个比较完整的 C++ 规划演示。

### 适合什么时候看

当你想看：

- C++ 版本怎么调用 MoveIt
- 如何等待规划场景对象
- 如何通过服务/动作做规划与执行

就应该看它。

## `ur10_examples_py`：Python 示例与实用工具包

这个包的实际价值比包名看起来更高，因为里面不只是 demo，还有很多当前整机主线会直接调用的脚本。

### `moveit_py_demo.py`

作用：

- 用 Python 方式调用 MoveItPy
- 可同时支持原始 UR10 主线和当前 `my_robot` 主线
- 在缺少外部传入参数时，还能自己展开 robot_description 和 SRDF

这说明它不是“死板的演示脚本”，而是一个相对通用的规划演示入口。

### `gantry_control.py`

作用：

- 通过 `FollowJointTrajectory` action 向 gantry 控制器发目标
- 控制 gantry 三轴移动到给定位置

它在启动链路里是有实际用途的，不是只做展示。

### `gantry_rviz_control.py`

作用：

- 在 RViz 中创建 interactive marker
- 让你通过拖动 marker 来控制 gantry 三轴

这个脚本非常适合：

- 交互式调试
- 快速验证 gantry 空间范围

### `capture_and_import_pcd.py`

作用：

- 协调点云采集与障碍物导入流程

它本质上是 perception 流程的 Python 助手。

### `depth_image_viewer.py`

作用：

- 打开深度图查看窗口

适合调试感知链路。

### `env_bootstrap.py`

作用：

- 帮助 Python 脚本在当前工作区环境下更稳地找到 ROS Python 依赖

这是一个“脚本能不能顺利跑起来”的辅助层。

## 这两个包和其他包的关系

### 和 `my_robot` 的关系

`my_robot` 主线会直接使用 `ur10_examples_py` 里的：

- `gantry_control`
- `gantry_rviz_control`

### 和 `ur10_simulation_bringup` 的关系

原始主线也会调这些示例/工具节点。

### 和 `ur10_perception` 的关系

`capture_and_import_pcd.py`、`depth_image_viewer.py` 与 `ur10_perception` 形成配套。

## 什么时候应该改这两个包

如果你想改：

- 演示脚本
- Python 规划流程
- gantry 交互控制方式
- PCD 辅助流程

优先看这里。

## 什么时候不应该先改这两个包

如果你想改：

- 机器人结构
- MoveIt 配置
- Gazebo 世界

就不该先从这里下手。

## 新手最容易混淆的点

### 1. 以为 examples 包不重要

实际上 `ur10_examples_py` 已经承担了当前主线中的真实辅助功能。

### 2. 以为 Python 包只是 demo，而 C++ 包才是正式实现

在这个工作区里并不是这样。

当前实际使用频率更高、和主线耦合更深的，反而是 `ur10_examples_py`。

## 如果你现在只能记住一句话

`ur10_examples` 更像基础 C++ 示例，`ur10_examples_py` 则已经成长成当前主线里的“工具脚本包”。
