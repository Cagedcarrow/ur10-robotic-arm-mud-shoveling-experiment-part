# UR10 RViz2 Real Execution Checklist

## 1. 正确启动顺序

1. 只启动一套 UR driver（无头）
```bash
source /root/ur10_ws/install/setup.bash
ros2 launch ur_robot_driver ur_control.launch.py \
  ur_type:=ur10 \
  robot_ip:=10.160.9.21 \
  headless_mode:=true \
  launch_rviz:=false \
  initial_joint_controller:=scaled_joint_trajectory_controller
```
2. 确认控制器 action 在线
```bash
source /root/ur10_ws/install/setup.bash
ros2 action list | grep /scaled_joint_trajectory_controller/follow_joint_trajectory
```
3. 启动 MoveIt + RViz 执行链
```bash
source /root/ur10_ws/install/setup.bash
ros2 launch ur10_real_pose_sync shovel_plan_execute.launch.py \
  execution_mode:=real \
  real_pose_source:=driver
```

## 2. 每一步成功标志

- driver 成功：无 `speed_slider_mask` 报错。
- controller 成功：`ros2 control list_controllers` 中 `joint_state_broadcaster`、`scaled_joint_trajectory_controller` 为 `active`。
- action 成功：存在 `/scaled_joint_trajectory_controller/follow_joint_trajectory`。
- 状态成功：`/joint_states` 能一次读取 6 轴关节。

## 3. RViz2 操作顺序

1. MotionPlanning 中 `Planning Group` 选择 `assembly_manipulator`。
2. Start State 选择 Current。
3. 拖动 Goal，点击 Plan。
4. 计划成功后尽快 Execute。
5. 若执行前手动动过真机，必须重新 Plan。

## 4. 常见失败日志与修复

### A. `Forward action not available: /scaled_joint_trajectory_controller/follow_joint_trajectory`
原因：driver 控制器 action 不在线。
处理：
1. 先只起 driver；
2. 确认 action 在线后再起 MoveIt；
3. 不要并行多套 driver/move_group。

### B. `speed_slider_mask is currently controlled by another RTDE client`
原因：RTDE 输入被其它客户端占用。
处理：
1. 停止本机所有额外 UR/RTDE 脚本；
2. 关闭其它电脑上的 UR 连接程序；
3. 检查示教器 External Control/URCap、Fieldbus(Ethernet-IP/Profinet)占用；
4. 必要时重启控制柜后只保留一条 driver 连接。

### C. `start point deviates from current robot state`
原因：Plan 与 Execute 之间状态变化，或多状态源漂移。
处理：
1. 每次动过真机后重新 Plan；
2. 缩短 Plan 到 Execute 间隔；
3. 执行前不要再动示教器；
4. 保证单一真机状态源参与执行链。

## 5. 真机安全注意事项

- 仅做小幅轨迹验证，低速度低加速度。
- 执行前确认工位无遮挡、人员远离。
- 禁止在不确定控制器状态时反复 Execute。
- 遇到异常立即急停并检查日志。

## 6. 一键诊断

```bash
/root/ur10_ws/scripts/diagnose_ur10_moveit_execution.sh 10.160.9.21 /root/ur10_ws
```

脚本将输出状态码：
- `DRIVER_NOT_RUNNING`
- `RTDE_OCCUPIED`
- `CONTROLLER_NOT_ACTIVE`
- `ACTION_NOT_AVAILABLE`
- `JOINT_STATES_MISSING`
- `MOVEIT_CONTROLLER_MISMATCH`
- `READY_FOR_RVIZ_EXECUTION`
