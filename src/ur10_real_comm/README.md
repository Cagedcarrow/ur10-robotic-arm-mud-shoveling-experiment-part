# ur10_real_comm

用于 UR10 实机通信 + MoveIt2 规划闭环验证的独立功能包。

## 一次性快速启动

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10_real_comm real_comm_moveit_verify.launch.py \
  robot_ip:=192.168.56.101 \
  reverse_ip:=192.168.56.1 \
  wrist3_delta_deg:=0.5
```

默认流程：

1. 启动 `ur_robot_driver/ur_control.launch.py` 实机通信；
2. 启动 MoveIt2 (`use_sim_time=false`)；
3. `motion_verify_node` 检查控制器与 `/joint_states`；
4. 让 MoveIt 规划只改动 `wrist_3_joint` 的微小位移；
5. 等待人工确认（`/ur10_real_comm/confirm_execute`）后执行一次；
6. 验证执行后关节变化并通过 `/ur10_real_comm/status` 发布 PASS/FAIL。

## 人工确认接口（固定）

```bash
ros2 service call /ur10_real_comm/confirm_execute std_srvs/srv/Trigger "{}"
```

当 launch 参数 `confirm_execute:=true` 时，只有收到上述服务调用才会执行一次微动。

## 状态话题格式

话题：`/ur10_real_comm/status`，消息类型：`std_msgs/msg/String`，内容为 JSON 字符串。

常见字段：

- `state`: `PASS|FAIL|WAIT_CONFIRM|PLAN|PLAN_OK|EXECUTE|CONFIRM|WARN|INFO`
- `reason`: 人类可读原因
- `wrist3_delta_deg`: 当前微动目标角度（度）
- 可能附加诊断字段，如 `actual_delta_deg`、`planned_delta_deg`、`plan_point_count`

示例：

```json
{"state":"PASS","reason":"Micro-move verified.","wrist3_delta_deg":0.5,"planned_delta_deg":0.5,"actual_delta_deg":0.48}
```

## 一键脚本

```bash
cd ur10_real_comm/scripts
chmod +x run_full_verify.sh
./run_full_verify.sh
```

默认会从 `config/real_robot_network.yaml` 风格的参数进行示例环境初始化，你可修改脚本最上方环境变量或直接传递 launch 参数。

脚本判定规则：

- 并行监听 `/ur10_real_comm/status`
- 首次出现终态 `PASS` 或 `FAIL` 即结束并输出摘要
- 超时或未收到终态按 `FAIL` 处理

## 失败排查入口

1. 网络问题（`robot_ip/reverse_ip`）：
   - 检查 `config/real_robot_network.yaml` 与现场网段配置
   - 确认机器人侧 External Control URCap 回连地址与 `reverse_ip` 一致
2. 控制器未激活：
   - `ros2 control list_controllers` 检查 `joint_state_broadcaster` 与 `initial_joint_controller` 是否为 `active`
3. 规划或执行失败：
   - 查看状态话题中的 `reason`
   - 查看脚本输出日志 `/tmp/ur10_real_comm_launch.log`
