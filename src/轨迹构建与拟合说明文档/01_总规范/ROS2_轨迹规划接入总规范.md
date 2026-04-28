# shovel_bucket_ros2_trajectory_integration_spec

## 1. 目标与前置条件

本文是给“ROS2 编码 AI”的单一实施规范，目标是在你已具备的环境中补齐“铲子末端轨迹规划与拟合”功能层。

你已完成的前置环境：

1. 机械臂 + 末端铲子运动控制链路可用。
2. RViz2 / Gazebo / MoveIt2 龙门架与机械臂联动仿真可用。

本文只关注：

- 如何生成末端轨迹（几何 + 姿态）
- 如何将轨迹变为关节可执行路径
- 如何用 ROS2 节点/接口落地并联调

不包含：底层驱动、硬件急停电气设计、控制器厂商私有协议。

---

## 2. 坐标系与变换定义（必须统一）

## 2.1 坐标系命名

- `world`：仿真世界系（Gazebo/RViz2 全局）
- `base_link`：机械臂基座系
- `tool0`：机械臂法兰标准工具系
- `shovel_tip`：铲子末端 TCP（本任务控制对象）

约定：右手系，长度单位 `m`，角度内部计算 `rad`（外部配置可用 `deg`）。

## 2.2 关键变换关系

- `T_world_base`：世界到基座
- `T_base_tip`：基座到铲尖
- `T_world_tip = T_world_base * T_base_tip`

任务轨迹默认在“任务局部系”先生成，再映射到 `world`。若你直接在 `world` 生成轨迹，必须保证等价关系一致。

## 2.3 姿态误差定义

采用旋转矩阵测地角误差（与 MATLAB `rotm_geodesic_deg` 一致）：

```text
R_rel = R_a * R_b^T
theta = acos((trace(R_rel)-1)/2)
err_deg = rad2deg(theta)
```

---

## 3. 任务输入与输出契约

## 3.1 输入类型

### `BucketFeatures`

- `topPoint[3]`
- `topRadius`
- `bottomRadius`
- `depth`
- `maxRadius`
- `digDirection[3]`
- `cloudPoints`（可选）

### `TrajectoryParams`

- `entrySpanFactor`
- `midSpanFactor`
- `exitSpanFactor`
- `entryDepthRatio`
- `targetDeepDepthRatio`
- `midSlopeAtKnot1`
- `maxCutAngleDeg`
- `topOuterOffsetRatio`
- `startFinishLiftRatio`
- `localYOffset`
- `execFirstMode`
- `forceBaseXDir`
- `reverseFitZAxis`
- `nPts`

### `PostureParams`

- `attackDeg`
- `assemblyDeg`
- `flipToolZ`

### `ExecutionParams`

- `ikWeights`
- `posTol`
- `oriTolDeg`
- `localRrtEnabled`
- `localRrtMaxIter`
- `maxConsecutiveLocalFail`
- `maxTotalLocalFail`

## 3.2 输出类型

### `TrajectoryOutput`

- `pathBase (N x 3)`
- `T_target_seq (4 x 4 x N)`
- `keyPts(start,knot1,deep,finish)`
- `fitInfo`

### `PlanningOutput`

- `qApproach (M x J)`
- `plannerInfo(success,numNodes,pathLength,elapsedSec,algorithm)`

### `ExecutionOutput`

- `qExec (K x J)`
- `runInfo(posErr/oriErr/fallback/hold/timeout/localRrtFailTotal)`

---

## 4. 末端轨迹拟合方式（核心）

本任务采用“局部平面三段轨迹拟合”，本质是可约束的三段函数拼接（入桶-中段-出桶）。

## 4.1 局部坐标构造

- `xAxis`：
  - `forceBaseXDir=true` 时固定世界 X 方向
  - 否则取 `digDirection` 的水平分量并归一化
- `zAxis`：
  - 默认 `[0,0,1]`
  - `reverseFitZAxis=true` 时 `[0,0,-1]`
- `yAxis = normalize(cross(zAxis, xAxis))`

## 4.2 四个关键横坐标

```text
x0 = -entrySpanFactor * startFinishRadius
x1 = -midSpanFactor   * maxRadius
x2 = 0
x3 =  exitSpanFactor  * startFinishRadius
```

其中：

```text
outerOffset = topOuterOffsetRatio * topRadius
startFinishRadius = topRadius + outerOffset
```

## 4.3 四个关键高度

```text
zLift = topZ + startFinishLiftRatio * depth
z0 = zLift
z1 = topZ - entryDepthRatio * depth
z2 = topZ - targetDeepDepthRatio * depth
z3 = zLift
```

## 4.4 分段函数求解

每段默认二次函数：

`z(x)=ax^2+bx+c`

通过“端点 + 斜率”线性方程求解系数：

- `seg1`：`(x0,z0)->(x1,z1)`，约束 `slope@x1`
- `seg2`：`(x1,z1)->(x2,z2)`，可选二次/直线
- `seg3`：`(x2,z2)->(x3,z3)`，约束起点斜率

执行优先模式 `execFirstMode=true`：

- `seg2` 优先线性（降低深点附近曲率波动）
- `seg3` 斜率可按出段弦斜率钳制

## 4.5 最小二乘轮廓融合（可选）

若 `cloudPoints` 有效：

1. 投影点云到局部 `x-z`。
2. 拟合 `z=ax^2+bx+c`。
3. 用拟合结果修正关键高度（主要修正 `z1`），与规则几何混合。

目的：让轨迹更贴实际桶剖面。

---

## 5. 轨迹安全约束

## 5.1 最大切削角约束

```text
slope = dz/dx
|slope| <= tan(maxCutAngleDeg)
```

## 5.2 最深点固定

深点必须固定在：

```text
z_deep_target = topZ - targetDeepDepthRatio * depth
```

## 5.3 斜率前后向限幅迭代

对离散轨迹执行前向/后向两遍迭代，避免局部过陡：

```text
for i=2..N:
  dz = z[i]-z[i-1]
  dz = clamp(dz, -maxSlope*dx, +maxSlope*dx)

for i=N-1..1:
  dz = z[i]-z[i+1]
  dz = clamp(dz, -maxSlope*dx, +maxSlope*dx)
```

每轮后重置锚点：`z[1]=z0, z[end]=z3, z[deep]=z_deep_target`。

## 5.4 执行优先放宽规则

当可执行性不足时，按顺序放宽：

1. 中段二次改线性
2. 降低中段深度梯度（减小 `midSlopeAtKnot1` 绝对值）
3. 增大 `topOuterOffsetRatio` 或 `startFinishLiftRatio`

不允许放宽：`targetDeepDepthRatio` 的目标语义（除非明确切换任务等级）。

---

## 6. 姿态生成算法

对 `pathBase` 每个点 `p_i`：

1. 切向量差分：

```text
t_i = p_{i+1}-p_{i-1} (边界点使用单边差分)
yAxis = normalize(t_i)
```

2. 正交基重建：

```text
zAxis = normalize(cross(xRef, yAxis))
xAxis = normalize(cross(yAxis, zAxis))
```

3. `flipToolZ`：若启用则 `zAxis=-zAxis`。

4. 连续性防翻转：若与上一帧轴点积为负，则整体翻转 `x/z` 轴符号。

5. 攻角补偿：

```text
thetaComp = attackDeg + assemblyDeg
Rcomp = Rot(axis=yAxis, thetaComp)
Rtar = Rnom * Rcomp
```

最终生成 `T_target_seq[:,:,i] = [Rtar, p_i]`。

---

## 7. 关节规划算法接入

## 7.1 职责边界

- 轨迹层：输出 `T_target_seq`（任务空间）
- 规划层：负责 `qCurrent -> qEntry` 接近段
- 执行层：负责 `T_target_seq` 跟踪

## 7.2 RRT*（基线）

流程：采样 -> 最近邻 -> steer -> 碰撞边检查 -> 邻域选父 -> rewire -> goal connect -> shortcut。

## 7.3 DP-RRT*（增强）

动态机制：

```text
Pg = max(Pg_min, Pg_init * exp(-decayRate*failCount))
rho = clamp(rho_init * exp(-decayRate*failCount), 0, 1)
v_new = normalize((1-rho)*v_rand + rho*v_goal)
lambda = lambdaMin + (lambdaMax-lambdaMin)*ratio(d_min)
```

`d_min` 来自“关节限位余量 + 历史碰撞样本距离”。

## 7.4 GPU 使用原则

- GPU：仅用于 NN/邻域距离计算
- CPU：碰撞检测

该边界必须保持，避免行为不一致。

---

## 8. IK 跟踪与退化策略

## 8.1 主校验

每目标点 IK 解 `qTry` 必须满足：

1. 无碰撞
2. `posErr <= posTol`
3. `oriErr <= oriTolDeg`

## 8.2 fallback（保持姿态 + 缩短位移）

主解失败时：

- 固定目标姿态 `Rtar`
- 位置采用 `pPrev + alpha*(pTar-pPrev)`，`alpha` 递减尝试
- 选择第一个满足约束的解

## 8.3 段连接

`qA -> qB` 顺序：

1. 直连插值
2. 失败则 local RRT*
3. 再失败则 hold（冲突样本回落到 `qA`）

保持执行连续性优先，避免任务中断。

---

## 9. ROS2 节点与接口设计（可直接编码）

## 9.1 节点拆分

1. `perception_node`
- 输入：点云/桶识别
- 输出：`/bucket/features`

2. `trajectory_node`
- 输入：`/bucket/features` + 轨迹参数
- 输出：`/trajectory/path_base`, `/trajectory/target_pose_seq`

3. `planner_node`
- 输入：`/joint_states`, `/trajectory/target_pose_seq`
- 输出：`/planning/q_approach`, `/planning/info`

4. `executor_node`
- 输入：`/planning/q_approach`, `/trajectory/target_pose_seq`
- 输出：`/execution/feedback`, `/execution/run_info`
- 动作接口：`/execute_shovel_task`（推荐 action）

## 9.2 推荐接口组合（最小可落地）

- Topic:
  - `/bucket/features`
  - `/trajectory/target_pose_seq`
  - `/planning/q_approach`
  - `/execution/feedback`
- Service:
  - `/trajectory/generate`（可选）
- Action:
  - `/shovel_task/execute`

## 9.3 消息字段级模板

### `BucketFeatures.msg`

```text
std_msgs/Header header
geometry_msgs/Point top_point
float32 top_radius
float32 bottom_radius
float32 depth
float32 max_radius
geometry_msgs/Vector3 dig_direction
```

### `TargetPoseSeq.msg`

```text
std_msgs/Header header
geometry_msgs/Pose[] poses
float32[] slope_samples
bool flip_tool_z
float32 attack_deg
float32 assembly_deg
```

### `PlanInfo.msg`

```text
std_msgs/Header header
bool success
string algorithm
uint32 num_nodes
float32 path_length
float32 elapsed_sec
float32 fail_count_final
```

### `ExecutionFeedback.msg`

```text
std_msgs/Header header
uint32 current_index
uint32 total_index
float32 pos_err
float32 ori_err_deg
uint32 fallback_count
uint32 hold_count
bool timeout
string timeout_stage
```

---

## 10. 时序与控制周期

## 10.1 执行时序

1. `perception_node` 发布 `BucketFeatures`
2. `trajectory_node` 生成 `pathBase/T_target_seq`
3. `planner_node` 规划 `qApproach`
4. `executor_node` 跟踪执行并反馈

## 10.2 时间参数化

`T_target_seq` 是离散点序列，必须时间化后再下发控制器：

1. 轨迹重采样（按弧长/关节增量）
2. 速度加速度限幅
3. 输出 `trajectory_msgs/JointTrajectory`

建议优先复用 MoveIt2 time-parameterization，再按实机表现微调。

## 10.3 控制周期建议

- 轨迹执行控制回路：50~200 Hz（按控制器能力）
- 规划/重规划触发：事件驱动，不要固定高频重规划

---

## 11. 调试与验收规范

## 11.1 六类故障与动作

1. 不可达（IK fail）
- 看：`posErr/oriErr/status`
- 调：减小 `targetDeepDepthRatio`、减小 `attackDeg` 绝对值、提高 `startFinishLiftRatio`

2. 碰撞密集
- 看：碰撞 body、localRRT 失败计数
- 调：增大 `topOuterOffsetRatio`、减小切削深度、优化白名单

3. 规划超时
- 看：`nearGoalDist/failCount/lambda/elapsedSec`
- 调：`maxIter/goalBias/lambdaMax/nearRadius`

4. 姿态翻转抖动
- 看：相邻轴点积、关节跳变量
- 调：强化连续性翻转抑制、增大 `nPts`

5. GPU 回退
- 看：`gpu.enabled/gpu.reason`
- 调：先允许 CPU 回退验证流程，再排查 CUDA 环境

6. 执行停滞
- 看：`hold_count/consecutiveNoProgress/timeoutStage`
- 调：放宽 localRRT 配额、降低轨迹激进度

## 11.2 必打日志字段

- 轨迹层：`deepAbs/deepTargetAbs/slopeMaxAfter/scaleUsed`
- 规划层：`algorithm/success/nodes/pathLen/elapsed/Pg/rho/lambda`
- 执行层：`posErr/oriErr/fallbackCount/holdCount/timeoutStage`

## 11.3 验收标准

1. 同参数下，ROS2 轨迹形状与 MATLAB 一致（视觉 + 数值）
2. 执行可完成且无异常大跳变
3. 失败时能回退且反馈字段完整

---

## 12. 给 ROS2 编码 AI 的实施清单（按阶段）

## 阶段A：接口定义

输入：本文第 9 节。  
输出：`.msg/.srv/.action` 文件与 README。  
完成标准：消息可编译，字段与本文一致。

## 阶段B：轨迹节点 `trajectory_node`

输入：`BucketFeatures + TrajectoryParams + PostureParams`。  
输出：`pathBase + T_target_seq + fitInfo`。  
完成标准：能复现三段轨迹、姿态连续、防翻转。

## 阶段C：规划节点 `planner_node`

输入：`joint_states + T_target_seq(first)`。  
输出：`qApproach + PlanInfo`。  
完成标准：可在仿真稳定到达入轨点。

## 阶段D：执行节点 `executor_node`

输入：`qApproach + T_target_seq`。  
输出：执行反馈与 `runInfo`。  
完成标准：支持主 IK + fallback + localRRT + hold 保底。

## 阶段E：联调与验收

输入：完整流水线。  
输出：联调报告（指标 + 问题 + 参数）。  
完成标准：满足第 11.3 节验收标准。

---

## 术语统一表（避免歧义）

- `pathBase`：轨迹离散点（任务/基座参考系）
- `pathWorld`：映射到世界系的轨迹点
- `T_tar`：单点目标位姿
- `T_target_seq`：整段目标位姿序列
- `qApproach`：入轨前关节路径
- `qExec`：完整执行关节路径

实现时必须统一以上命名语义，避免“同名异义”导致联调失败。

---

## 参考来源（整合依据）

- `TRAJECTORY_MATH_GUIDE.md`：数学与算法主依据
- `shovel_bucket_ros2_interface_template.md`：接口模板依据
- `shovel_bucket_trajectory_algorithm.md`：轨迹原理与坐标说明依据

本规范优先保证行为一致迁移，后续实时优化（并行化/算子加速）作为第二阶段处理。

---

## 13. ROS2 单功能包结构模板（轨迹生成与拟合）

目标：将“轨迹生成 + 姿态拟合 + 接近规划 + 执行编排”集中在一个功能包中，便于先跑通闭环，再拆分微服务。

推荐包名：

- `shovel_bucket_trajectory_pkg`

推荐工作区结构（最小可运行）：

```text
<ws_root>/
  src/
    shovel_bucket_trajectory_pkg/
      package.xml
      CMakeLists.txt
      README.md
      launch/
        shovel_bucket_pipeline.launch.py
      config/
        trajectory_params.yaml
        planner_params.yaml
        executor_params.yaml
      msg/
        BucketFeatures.msg
        TargetPoseSeq.msg
        PlanInfo.msg
        ExecutionFeedback.msg
      srv/
        GenerateTrajectory.srv
      action/
        ExecuteShovelTask.action
      include/shovel_bucket_trajectory_pkg/
        types.hpp
        trajectory_fitter.hpp
        pose_builder.hpp
        planner_adapter.hpp
        executor_adapter.hpp
      src/
        trajectory_node.cpp
        planner_node.cpp
        executor_node.cpp
        trajectory_fitter.cpp
        pose_builder.cpp
        planner_adapter.cpp
        executor_adapter.cpp
      scripts/
        quick_test_pipeline.sh
      test/
        test_trajectory_math.cpp
        test_pose_sequence.cpp
        test_interface_smoke.cpp
```

## 13.1 `package.xml` 依赖模板

至少包含：

- `rclcpp`
- `std_msgs`
- `geometry_msgs`
- `sensor_msgs`
- `trajectory_msgs`
- `builtin_interfaces`
- `rosidl_default_generators`
- `rosidl_default_runtime`
- `tf2`
- `tf2_ros`
- `tf2_geometry_msgs`
- `moveit_ros_planning_interface`（若 planner/executor 直接调 MoveIt2）
- `ament_cmake`

若你要在包内做点云直接处理，再加：

- `pcl_ros`
- `pcl_conversions`

## 13.2 `CMakeLists.txt` 核心模板要求

1. `find_package(...)` 对齐 `package.xml` 依赖。  
2. `rosidl_generate_interfaces(...)` 生成 `msg/srv/action`。  
3. 三个节点分别 `add_executable`：`trajectory_node/planner_node/executor_node`。  
4. 节点都链接到共用算法库（`trajectory_fitter`, `pose_builder` 等），避免重复实现。  
5. `install(TARGETS ...)`、`install(DIRECTORY launch config ...)` 完整安装。  

## 13.3 单包内模块职责（必须分层）

1. `trajectory_fitter.*`
- 实现第 4、5 节的三段轨迹拟合与安全约束。
- 输入 `BucketFeatures + TrajectoryParams`，输出 `pathBase + keyPts + fitInfo`。

2. `pose_builder.*`
- 实现第 6 节姿态生成（切向、正交基、flip、防翻转、攻角补偿）。
- 输入 `pathBase + PostureParams`，输出 `T_target_seq`。

3. `planner_adapter.*`
- 封装 RRT*/DP-RRT* 或 MoveIt2 接口，输出 `qApproach + PlanInfo`。

4. `executor_adapter.*`
- 实现 IK 主解、fallback、localRRT、hold 保底，输出 `qExec + runInfo`。

5. `trajectory_node.cpp`
- 负责参数读取、轨迹生成、发布 `TargetPoseSeq`。

6. `planner_node.cpp`
- 负责接近段规划与规划信息发布。

7. `executor_node.cpp`
- 负责执行动作 Action Server 与反馈发布。

## 13.4 参数文件模板（`config/*.yaml`）

`trajectory_params.yaml`（示例键）：

```yaml
trajectory_node:
  ros__parameters:
    entry_span_factor: 1.0
    mid_span_factor: 0.35
    exit_span_factor: 1.0
    entry_depth_ratio: 0.20
    target_deep_depth_ratio: 0.15
    max_cut_angle_deg: 30.0
    top_outer_offset_ratio: 0.125
    start_finish_lift_ratio: 0.25
    exec_first_mode: true
    force_base_x_dir: true
    reverse_fit_z_axis: false
    n_pts: 90
```

`planner_params.yaml`（示例键）：

```yaml
planner_node:
  ros__parameters:
    algorithm: "dp_rrtstar_cuda"
    max_iter: 2400
    goal_bias_init: 0.28
    goal_bias_min: 0.03
    lambda_max: 0.24
    lambda_min: 0.08
    near_radius: 0.65
    goal_thresh: 0.20
    use_gpu: true
```

`executor_params.yaml`（示例键）：

```yaml
executor_node:
  ros__parameters:
    pos_tol: 0.04
    ori_tol_deg: 12.0
    local_rrt_enabled: true
    local_rrt_max_iter: 260
    max_consecutive_local_fail: 8
    max_total_local_fail: 30
```

## 13.5 Launch 模板（`shovel_bucket_pipeline.launch.py`）

最小启动内容：

1. 启动 `trajectory_node`（加载 `trajectory_params.yaml`）  
2. 启动 `planner_node`（加载 `planner_params.yaml`）  
3. 启动 `executor_node`（加载 `executor_params.yaml`）  
4. 可选 remap 到你现有 `/joint_states`、MoveIt2 话题与控制器接口  

建议在 launch 内保留统一命名空间参数：

- `namespace:=shovel_task`

## 13.6 直接交给 ROS2 编码 AI 的开发顺序

1. 先建包骨架 + `msg/srv/action`，确保 `colcon build` 通过。  
2. 先实现 `trajectory_fitter + pose_builder`，发布 `TargetPoseSeq`。  
3. 再接 `planner_adapter` 输出 `qApproach`。  
4. 最后接 `executor_adapter` 和 Action 反馈闭环。  
5. 每阶段用第 11 节验收标准回归。  

## 13.7 单包阶段完成判据

满足以下条件才算“单包可交付”：

1. 一条命令启动 launch 后能从输入参数生成末端位姿序列。  
2. 能产生接近段规划结果并给出规划统计。  
3. 执行动作时可持续发布反馈，失败可回退。  
4. 日志字段覆盖第 11.2 节。  
