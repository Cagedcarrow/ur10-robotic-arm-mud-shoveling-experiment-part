# 末端铲斗轨迹算法 ROS2 接口模板（大纲版）

## 1. 文档目的

本文给出 `shovel_bucket_parabola_ik_demo_stable.m` 对应的 ROS2 接口化模板，用于后续实机控制落地。

范围：
- 定义节点职责
- 定义输入输出接口
- 定义最小执行流程
- 定义监控与验收字段

不包含具体代码实现与硬件驱动细节。

---

## 2. 推荐节点拆分

建议最小拆分为 3 个节点：

1. `shovel_task_planner_node`
- 职责：接收铲泥任务参数，生成 `pathBase/pathWorld` 与每点目标姿态 `T_tar`。

2. `shovel_ik_solver_node`
- 职责：对每个 `T_tar` 求解关节角，应用连续性评分与 fallback 策略，输出 `qTraj`。

3. `shovel_executor_node`
- 职责：将 `qTraj` 按时间序列发送给控制器并采集执行反馈，形成 `tipTrail` 与误差统计。

可选：合并为单节点 `shovel_pipeline_node`（先保证可运行，再拆分）。

---

## 3. 接口定义模板

## 3.1 任务输入（Planner 输入）

Topic/Service（任选其一）：
- `/shovel/task_request`

字段模板：
```yaml
header:
  stamp: <time>
  frame_id: world_base

robot:
  urdf_name: ur10_world.urdf
  base_frame: world_base
  base_link: ur10
  end_effector: shovel_tip

mount:
  base_xyz: [0.0, 0.0, 1.40]
  base_ypr_rad: [0.0, 0.0, 3.1415926]

traj_param:
  center_x: 1.00
  y_const: 0.00
  z_top: 0.20
  half_span: 0.20
  depth: 0.50
  n_pts: 100

attitude_param:
  flip_tool_z: true
  pitch_bias_deg: -12.0

ik_param:
  ik_weights: [1.0, 1.0, 1.0, 0.6, 0.6, 0.6]
  q_jump_weight: 0.08
  primary_pos_tol: 0.035
  primary_ori_tol_deg: 12.0
  primary_y_align_tol_deg: 12.0
```

## 3.2 规划输出（Planner 输出）

- `/shovel/target_pose_seq`

字段模板：
```yaml
header:
  stamp: <time>
  frame_id: world_base

key_points:
  start: [x, y, z]
  vertex: [x, y, z]
  finish: [x, y, z]

parabola_coeff:
  a: <float>
  b: <float>
  c: <float>

pose_seq:
  - index: 0
    position: [x, y, z]
    orientation_matrix_row_major: [r11, r12, ... r33]
    tangent_slope_k: <float>
  - ...
```

## 3.3 IK 输出

- `/shovel/joint_trajectory_cmd`

字段模板：
```yaml
header:
  stamp: <time>
  frame_id: world_base

joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint]

points:
  - index: 0
    q: [q1, q2, q3, q4, q5, q6]
    dt: 0.03
  - ...

quality:
  fallback_count: <int>
  pos_err_mean: <float>
  pos_err_max: <float>
  ori_err_mean_deg: <float>
  ori_err_max_deg: <float>
  y_align_err_mean_deg: <float>
  y_align_err_max_deg: <float>
  q_jump_mean: <float>
  q_jump_max: <float>
```

## 3.4 执行反馈输出

- `/shovel/execution_feedback`

字段模板：
```yaml
header:
  stamp: <time>
  frame_id: world_base

state: RUNNING | DONE | ABORTED
progress:
  current_index: <int>
  total_points: <int>

current_metrics:
  seed_tag: P | F
  ik_status: <string>
  pos_err: <float>
  ori_err_deg: <float>
  y_align_err_deg: <float>
  q_jump: <float>

final_metrics:
  final_tip_to_end_err: <float>
```

---

## 4. 最小执行时序模板

1. 上位机发送 `/shovel/task_request`。
2. Planner 计算抛物线与姿态序列，发布 `/shovel/target_pose_seq`。
3. IK 节点逐点求解，发布 `/shovel/joint_trajectory_cmd`。
4. Executor 下发关节命令，周期发布 `/shovel/execution_feedback`。
5. 完成后输出 `DONE` 与 `final_tip_to_end_err`。

---

## 5. 参数与默认值建议

建议作为 ROS2 参数服务器参数：
- `center_x, y_const, z_top, half_span, depth, n_pts`
- `flip_tool_z, pitch_bias_deg`
- `ik_weights, q_jump_weight`
- `primary_pos_tol, primary_ori_tol_deg, primary_y_align_tol_deg`
- `frame_pause`

建议默认值保持与 MATLAB 脚本一致，先保证仿真一致性再调参。

---

## 6. 错误处理模板

统一错误码建议：
- `E_URDF_NOT_FOUND`
- `E_FRAME_INVALID`
- `E_IK_NO_SOLUTION`
- `E_TRAJ_OUT_OF_REACH`
- `E_CONTROLLER_REJECT`

统一处理建议：
- 单点 IK 失败先触发 fallback
- 连续失败超过阈值则 ABORT
- 所有失败上报 `/shovel/execution_feedback` 并记录最后一个有效点索引

---

## 7. 验收清单模板（实机前）

1. 默认参数下：末端轨迹形状与 MATLAB 预览一致。
2. `depth` 变化：轨迹顶点高度变化正确。
3. `pitch_bias_deg` 变化：y 轴切线对齐不变，攻角变化明显。
4. `q_jump_max` 无异常尖峰，执行连续无抖动。
5. `final_tip_to_end_err` 在可接受阈值内。

---

## 8. 可直接复用的接口最小集合

若只保留最少接口，建议先实现：
- 输入：`/shovel/task_request`
- 输出1：`/shovel/joint_trajectory_cmd`
- 输出2：`/shovel/execution_feedback`

这样可以最快形成“参数 -> 轨迹 -> IK -> 执行 -> 指标”的闭环。
