# `ur10_perception` 包分析

## 这篇文档解决什么问题

这篇文档解释 `ur10_perception` 为什么不只是“感知节点包”，而是同时承担了 world、点云和场景障碍物相关职责。

## 一句话说，这个包是干什么的

`ur10_perception` 是当前工作区里的环境与感知支撑包，负责 overhead camera、点云处理、PCD 导入碰撞场景，以及 Gazebo world 资源。

## 标签

`基础支撑`

## 它在整个工作区中的位置

它既服务原始 UR10 主线，也服务当前 `my_robot` 主线。

换句话说，它不是某一条单独主线的私有包，而是共享环境能力包。

## 主要文件和入口说明

### `src/pcd_capture_node.cpp`

这个节点负责：

- 订阅点云 topic
- 对点云做简单降采样
- 保存成 PCD 文件

它适合做“先抓一帧点云保存下来”的工作。

### `src/pcd_to_collision_scene_node.cpp`

这个节点负责：

- 读取 PCD 文件
- 做 ROI 过滤
- 做体素降采样
- 尝试去掉主平面
- 抽取最大聚类
- 最后把结果转成 MoveIt 的 collision object

它的作用不是“做复杂视觉识别”，而是把点云障碍物快速注入规划场景。

### `src/synthetic_overhead_camera_node.cpp`

这个节点负责发布一个合成的 overhead 点云。

它更像：

- 一个便于联调的伪传感器

适合在没有真实点云链路时，仍然验证后续 PCD/碰撞场景流程。

### `urdf/overhead_depth_camera.xacro`

定义 overhead camera 相关的模型描述。

### `worlds/gantry_only.world`

这是当前 `my_robot` 主线里非常关键的 world。

它是当前整机启动最常用的基础世界文件。

### `worlds/obstacle_scene.world`

更偏障碍物/感知场景演示。

### `launch/perception_only.launch.py`

提供一个只启动感知链路的入口。

## 这个包和其他包的关系

### 和 `my_robot` 的关系

`my_robot` 当前默认 world 就会用到这里的 `gantry_only.world`。

### 和 `ur10_simulation_bringup` 的关系

原始主线也会把它作为环境和感知能力来源。

### 和 `ur10_examples_py` 的关系

`ur10_examples_py` 中的：

- `capture_and_import_pcd.py`
- `depth_image_viewer.py`

会和这个包的 topic、world 或点云能力配合使用。

## 什么时候应该改这个包

如果你想改：

- Gazebo 世界文件
- overhead 相机
- 点云采集逻辑
- PCD 转碰撞场景逻辑
- 合成感知数据

应该优先看这个包。

## 什么时候不应该先改这个包

如果你想改：

- 机器人本体结构
- 铲斗安装位置
- MoveIt 规划组

那就不该先改这里。

## 新手最容易混淆的点

### 1. 以为它只是“视觉算法包”

其实不是。

它还提供：

- Gazebo world
- 场景支撑资源
- 伪传感器

### 2. 以为它和 Gazebo 世界文件无关

其实当前很多启动链路都直接依赖它的 world 文件。

## 如果你现在只能记住一句话

`ur10_perception` 是“感知 + 环境 + world 资源”三合一的支撑包。
