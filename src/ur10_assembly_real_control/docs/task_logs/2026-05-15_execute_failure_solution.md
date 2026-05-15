# UR10 Execute 失败总解决方案（Plan 正常、Execute 失败）

## 1. 现象与结论

### 现象

- RViz2 中可以 `Plan`，但 `Execute` 失败；
- 日志反复出现：
  - `Connection to reverse interface dropped`
  - `Connection attempt on port 50003 while maximum number of clients (1) is already connected`
  - `MoveGroupInterface::move() failed or timeout reached`

### 结论

本问题不是 MoveIt 碰撞检测导致，而是 **UR 外部控制执行通道不稳定/被并发客户端抢占**。  
核心故障面在 reverse/trajectory/script command 链路（尤其 `50003`）。

---

## 2. 根因分层

### A. 会话抢占/重复控制客户端

- MATLAB、RoboDK、其他 RTDE 客户端与 ROS2 driver 并行连接；
- 导致 `50003` 端口单客户端限制触发冲突。

### B. External Control 程序状态被打断

- 示教器未保持 `External Control` 程序持续运行；
- 手动操作/jog/切程序导致 reverse 接口断开。

### C. 网络/转发链路抖动

- WSL2 + Windows portproxy 运行真机执行阶段时容易产生频繁重连与 TIME_WAIT 堆积；
- 执行请求虽被接受，但轨迹中途被中断后超时。

---

## 3. 一次性修复步骤（严格顺序）

### Step 1: 示教器侧清理

1. 仅保留一个主程序，程序树中只放一个 `External Control` 节点；
2. URCap 配置 IP=ROS 主机，端口= `50002`（与 driver 一致）；
3. 不运行其他示教器动作节点。

### Step 2: 主机侧清场（防抢占）

```bash
pkill -f ur_control.launch.py
pkill -f ur_ros2_control_node
pkill -f move_group
pkill -f rviz2
pkill -f matlab
```

并确认 MATLAB / RoboDK / 其他 RTDE 工具完全退出。

### Step 3: 按官方链路重启

1. 启动 `ur_robot_driver`；
2. 在示教器点击 `Play` 运行 `External Control`；
3. 运行 GUI 的 `验证连接与控制器`；
4. 验证通过后再启动 RViz2 + MoveIt2。

### Step 4: 执行前核验

```bash
ros2 control list_controllers | grep scaled_joint_trajectory_controller
ros2 action info /scaled_joint_trajectory_controller/follow_joint_trajectory
ros2 topic echo /speed_scaling_state_broadcaster/speed_scaling --once
ss -tnp | grep -E ':50001|:50003|:50004'
```

必须满足：
- `scaled_joint_trajectory_controller` 为 `active`；
- action server 在线；
- `speed_scaling > 0`；
- 50001/50003/50004 连接稳定、无异常抖动。

### Step 5: RViz2 执行策略

- `Start State = Current`；
- 先小位移轨迹；
- 每次只点击一次 `Execute`，等待完成后再发下一条。

---

## 4. 掉线后的恢复动作

当出现 `Connection to reverse interface dropped`：

### Teach Pendant 模式

- 直接在示教器重新 `Play` 当前 External Control 程序。

### Remote Control 模式

```bash
ros2 service call /dashboard_client/play std_srvs/srv/Trigger {}
```

### Headless 模式

```bash
ros2 service call /io_and_status_controller/resend_robot_program std_srvs/srv/Trigger {}
```

---

## 5. 关键工程建议

1. **不要并行 MATLAB 与 ROS2 对同一真机做主动控制**；
2. 真机执行阶段优先使用原生 Ubuntu 主机，减少 WSL2 转发链路风险；
3. 机器人与控制主机尽量同网段直连；
4. 每次执行失败后同步查看：
   - `docs/error_logs/*_session_diagnostics.md`
   - `docs/error_logs/*_execute_capture.md`

---

## 6. 成功判据

- 连续 10 次小轨迹 `Plan + Execute` 无 `reverse interface dropped`；
- 无 `50003 ... maximum number of clients`；
- 无 `MoveGroupInterface::move() failed or timeout reached`；
- 机械臂与 RViz 轨迹一致完成。
