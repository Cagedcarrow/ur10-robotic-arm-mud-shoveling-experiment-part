# 路径规划与避障原理

适合谁看：已经会启动系统，但还想知道“为什么机械臂会动、为什么会避障”的新手。

这篇文档不只讲怎么运行，还讲本项目中的路径规划和避障是怎么工作的。

相关文档：

- [Docs 导航](README.md)
- [运行手册](03_runbook.md)
- [节点与 Launch 清单](04_nodes_and_launches.md)
- [代码讲解](05_code_walkthrough.md)
- [ROS 2 入门与本项目上手指南](07_ros2_getting_started.md)

## 1. 路径规划整体原理

本项目里的路径规划可以理解成四层协作：

1. Gazebo 提供仿真世界和机器人当前状态
2. `ros2_control` 负责把轨迹命令交给控制器执行
3. MoveIt 根据当前状态和障碍物计算一条无碰撞轨迹
4. 控制器执行这条轨迹，所以你会在 Gazebo 里看到机械臂运动

也就是说：

- Gazebo 负责“世界和机器人”
- MoveIt 负责“算路”
- 控制器负责“按算好的路去动”

## 2. 本项目里的规划组和控制器

### 规划组

本项目默认规划组是：

```text
ur_manipulator
```

这个规划组定义了：

- 哪些关节参与规划
- MoveIt 在给谁算轨迹

### 控制器

本项目默认执行控制器是：

```text
joint_trajectory_controller
```

它的作用是：

- 接收关节轨迹
- 按时间把每个关节移动到对应位置

### 规划器

本项目默认使用：

```text
OMPL
```

更具体地说，常用默认规划器是 `RRTConnect`。

## 3. 规划是如何真正运行起来的

你可以把整个过程理解为“谁发目标、谁算路径、谁执行”。

### 谁发起目标

通常是这两个示例节点之一：

- C++：`move_group_interface_demo`
- Python：`moveit_py_demo`

它们会告诉 MoveIt：

- 现在机械臂在哪
- 目标关节或目标姿态是什么
- 使用哪个规划组

### 谁计算轨迹

是 `move_group`。

`move_group` 是 MoveIt 的规划执行核心节点。它会：

- 读取当前关节状态
- 读取规划场景里的障碍物
- 调用 OMPL 规划器
- 生成一条轨迹

### 谁执行轨迹

是 `joint_trajectory_controller`。

`move_group` 生成轨迹后，会把轨迹交给这个控制器。控制器再把轨迹发到 Gazebo 仿真关节上执行。

### 为什么 Gazebo 里会看到机械臂运动

因为 Gazebo 中的 UR10 已经接入了 `gazebo_ros2_control`，而 `joint_trajectory_controller` 正是通过这条链路驱动 Gazebo 里的关节。

## 4. 你应该在哪里输入参数

### launch 参数示例

如果你运行：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py start_rviz:=false ur_type:=ur10
```

这里的：

- `start_rviz:=false`
- `ur_type:=ur10`

就是 launch 参数。

### C++ 节点参数示例

如果你运行：

```bash
ros2 run ur10_examples move_group_interface_demo --ros-args -p use_sim_time:=true
```

这里的：

- `use_sim_time:=true`

就是节点参数。

### Python 节点参数示例

如果你运行某个 Python 节点时写：

```bash
ros2 run ur10_perception pcd_to_collision_scene_node --ros-args -p pcd_file:=/root/ur10_ws/data/latest_obstacle.pcd
```

这里的：

- `pcd_file:=...`

也是节点参数。

### 代码默认值与命令行参数的优先关系

优先关系可以简单理解为：

1. 命令行传入的参数优先
2. 如果命令行没传，就用 launch 里的默认值
3. 如果 launch 也没传，就用源码里写好的默认值

## 5. 点云障碍物是如何导入的

### 点云从哪里来

点云来自：

```text
/overhead_camera/points
```

在本项目里，这个点云由 `synthetic_overhead_camera_node` 发布。

### 为什么先写成 PCD

因为这样做更适合调试和复现：

- 你可以把点云保存下来
- 之后可以重复导入同一份 PCD
- 更容易验证“这份障碍物数据到底是不是同一份”

### `pcd_to_collision_scene_node` 做了什么

它会：

1. 读入 PCD 文件
2. 从点云中识别工作台和平面以上的障碍物
3. 生成一个简化的障碍物盒
4. 把它发布成 MoveIt 可识别的 `CollisionObject`

### 障碍物如何进入 MoveIt Planning Scene

当 `pcd_to_collision_scene_node` 发布后，MoveIt 的 Planning Scene 中就会出现：

- `work_table`
- `pcd_obstacle_box`

从这一步开始，MoveIt 才真正“知道场景里有障碍物”。

这也是一个常见误区：

- 看见点云不代表 MoveIt 已经拿到障碍物
- 必须等 `CollisionObject` 导入成功才算真正进入规划场景

## 6. 机械臂是如何避障的

当 `pcd_obstacle_box` 已经进入 Planning Scene 后：

1. 示例节点向 MoveIt 提交目标
2. MoveIt 在规划时会检查轨迹是否与 `pcd_obstacle_box` 碰撞
3. 如果某条轨迹穿过障碍物，这条轨迹会被判为无效
4. 规划器会继续寻找一条不碰撞的替代轨迹
5. 找到后再交给 `joint_trajectory_controller` 执行

所以“避障”的本质不是控制器自己绕开障碍物，而是：

- MoveIt 在规划阶段就已经排除了碰撞轨迹

## 7. 典型运行场景

### 自动模式

直接运行：

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py
```

适合：

- 一次性看完整流程

### 手动采集 PCD 后再规划

适合：

- 你想先保存点云，再自己决定什么时候导入障碍物

典型流程：

1. 启动总环境但不自动运行示例
2. 手动运行 `pcd_capture_node`
3. 手动运行 `pcd_to_collision_scene_node`
4. 手动运行 C++ 或 Python 示例

### 替换目标点后重复规划

适合：

- 你想多次测试不同目标

做法：

- 修改 C++ / Python 示例中的默认目标
- 或者给节点传新的参数
- 在同一套 MoveIt 环境中重复执行

## 8. 常见误区

### “看见点云不等于已经进入 MoveIt 场景”

正确理解：

- 点云只是原始数据
- 必须经过 `pcd_to_collision_scene_node`
- 变成 `CollisionObject` 之后，MoveIt 才会拿它做碰撞检测

### “生成 PCD 不等于已经避障”

正确理解：

- PCD 只是中间文件
- 还要导入规划场景
- 还要重新规划轨迹

### “MoveGroup 起了不等于控制器正常”

正确理解：

- `move_group` 负责规划
- 真正执行还依赖 `joint_trajectory_controller`
- 所以还要检查控制器是否 `active`

### “Gazebo 里有机器人不等于当前这套启动是干净的”

正确理解：

- 旧的 Gazebo 残留也可能让你看到机器人
- 如果同时存在多套旧进程，就可能出现 `Entity already exists`、`Controller already loaded` 或 `PREEMPTED`

下一篇建议阅读：[运行手册](03_runbook.md)
