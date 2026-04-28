# 轨迹生成与改进RRT集成总结

## 1. 完成内容

- 在 `shovel_bucket_trajectory_pkg` 内完成可运行实现（不再是占位模板）：
  - `trajectory_node`：三段轨迹拟合 + 姿态序列生成 + 工作空间过滤 + `/trajectory/generate` 服务。
  - `planner_node`：`planner_mode=ompl|dp_rrt` 可切换；DP-RRT 迁移实现（动态 `Pg/rho/lambda`）；发布树与路径 Marker。
  - `executor_node`：接收轨迹并转换 `JointTrajectory`，发布执行反馈，提供 `ExecuteShovelTask` action。
- 在主线新增独立入口：
  - `ur10_simulation_bringup/launch/complete_simulation_with_shovel_trajectory.launch.py`
  - 该入口在原 `complete_simulation` 基础上挂载 `shovel_bucket_pipeline`。
- 新增参数链与接口链：
  - 规划器参数：`planner_mode`, `dp_rrt.*`, `workspace.*`
  - 话题：`/trajectory/target_poses`, `/planning/dp_rrt_*_markers`, `/planning/info`, `/execution/feedback`

## 2. 新增文件

- `ur10_simulation_bringup/launch/complete_simulation_with_shovel_trajectory.launch.py`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/include/shovel_bucket_trajectory_pkg/trajectory_math.hpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/include/shovel_bucket_trajectory_pkg/planner_math.hpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/include/shovel_bucket_trajectory_pkg/executor_math.hpp`

## 3. 修改文件

- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/CMakeLists.txt`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/package.xml`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/trajectory_fitter.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/pose_builder.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/planner_adapter.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/executor_adapter.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/trajectory_node.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/planner_node.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/src/executor_node.cpp`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/config/trajectory_params.yaml`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/config/planner_params.yaml`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/config/executor_params.yaml`
- `轨迹构建与拟合说明文档/04_包结构模板/shovel_bucket_trajectory_pkg/launch/shovel_bucket_pipeline.launch.py`
- `ur10_simulation_bringup/package.xml`

## 4. 算法迁移说明

- 从 `Algo_DP_RRT_3D.m` 迁移的核心机制：
  - 动态目标偏置：`Pg = max(pg_min, pg_init * exp(-decay_rate * fail_count))`
  - 动态引力融合：`rho = clamp(rho_init * exp(-decay_rate * fail_count), 0, 1)`
  - 方向融合：`v_new = normalize((1-rho)*v_rand + rho*v_goal)`
  - 自适应步长：`lambda(d_min)`，靠近边界收缩步长，安全区采用 `lambda_max`
  - 失败恢复：扩展失败累加 `fail_count`，成功时衰减恢复
- 第一版采用 CPU 实现，保留后续 GPU 加速参数入口。

## 5. 轨迹拟合方法

- 三段轨迹（entry/mid/exit）离散生成，锚定深点。
- 执行优先逻辑：中段可线性化，减少深点附近曲率波动。
- 斜率双向迭代限幅（前向+后向）保证 `max_cut_angle_deg` 约束。
- 姿态构造：
  - 切线方向驱动工具轴；
  - 正交基重建；
  - 连续性防翻转；
  - `attack_deg + assembly_deg` 攻角补偿。

## 6. 工作空间约束设计

- 采用“环形可达区 + 高度窗口”硬约束：
  - `workspace.r_min/r_max`
  - `workspace.z_min/z_max`
- 轨迹点生成后逐点过滤，不满足约束的点被剔除；若剔除过多回退到原轨迹，防止空轨迹。
- 参数默认值已按 UR10+铲子保守范围设置，可在 YAML/launch 中调整。

## 7. 测试结果

执行命令（无头）：

```bash
cd /root/ur10_ws
colcon build --symlink-install --packages-select shovel_bucket_trajectory_pkg ur10_simulation_bringup
source install/setup.bash
ros2 launch shovel_bucket_trajectory_pkg shovel_bucket_pipeline.launch.py planner_mode:=dp_rrt
```

接口链验证：

```bash
ros2 node list
ros2 topic list | grep -E '/trajectory|/planning|/execution'
ros2 service list | grep /trajectory/generate
ros2 action list | grep /execution/execute_task
```

结果：

- 新增三节点可启动。
- `/trajectory/generate` 服务、`/execution/execute_task` action 可见。
- DP-RRT 模式下，Python 注入 `BucketFeatures` 后收到：
  - `PLAN ('dp_rrt', 14, 0.7966...)`
  - `FB (90, 2)`
- OMPL 模式下收到：
  - `PLAN ('ompl', 60)`
- 主线入口 `complete_simulation_with_shovel_trajectory.launch.py` 可启动并成功挂载三节点（20s 超时前已完成主要节点拉起）。

## 8. 当前遗留问题

- 当前 `executor_node` 的关节轨迹生成采用“可执行占位映射”（非真实 IK 求解），用于打通链路与稳定发布；下一步应替换为 MoveIt/IK 求解并做碰撞检查。
- DP-RRT 当前在任务空间（3D 点）规划，不是严格关节空间 RRT*；后续需要对接真实 `joint_limits + collision`。
- `Xvfb` 未安装（系统仅有 `ffmpeg`），本轮无法完成离屏 RViz 录制实文件；需要安装 `xvfb` 后执行录制脚本。
- `move_group` 日志仍提示 SRDF 中存在未知链接名“铲子”，建议后续统一 URDF/SRDF link 命名。

## 9. 下一步建议

1. 将 `executor_node` 替换为 MoveIt2 IK/Cartesian 跟踪执行，加入姿态误差与关节跳变阈值检查。
2. 把 DP-RRT 从任务空间扩展为关节空间版本，接入 `robot_state` 与碰撞检测接口。
3. 补充轨迹质量指标话题（最大姿态测地角、最大关节增量、平均曲率等）。
4. 安装 `xvfb` 后补齐无头录屏交付：
   - `sudo apt install xvfb`
   - 使用 `Xvfb :99` + `rviz2` + `ffmpeg -f x11grab` 录制。
