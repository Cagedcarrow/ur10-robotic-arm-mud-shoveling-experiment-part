# UR10 CB3 示教器开启外部连接操作指南

本文说明在 UR10 CB3 示教器上，如何开启并运行与外部 ROS2 (`ur_robot_driver`) 的连接。

## 1. 前置条件

- 机器人与上位机通过网线直连或同一交换机互联。
- 已在上位机准备好 ROS2 Humble 与 `ur_robot_driver`。
- 已获取并安装 `externalcontrol` URCap（官方驱动配套）。

## 2. 示教器网络设置（CB3）

1. 进入 `Setup Robot` -> `Network`。
2. 设置机器人 IP（例如 `192.168.0.10`），并与上位机网段一致。
3. 保存并确认上位机可 `ping` 通机器人 IP。

## 3. 安装并启用 External Control URCap

1. 将 `externalcontrol-*.urcap` 拷贝到 U 盘。
2. 在示教器进入 `Setup Robot` -> `URCaps`。
3. 选择 `+` 安装 URCap，安装后按提示重启控制器。
4. 重启后确认 Program 节点中可添加 `External Control`。

## 4. 创建并运行 External Control 程序

1. 新建一个 Program。
2. 在 Program Tree 中添加 `External Control` 节点。
3. 在 External Control 节点里填写上位机 IP（运行 ROS2 driver 的主机 IP）。
4. 端口保持与 driver 默认一致（通常无需改动，按 URCap 默认）。
5. 保存程序，例如 `external_control.urp`。
6. 点击 `Play` 运行该程序，保持程序处于运行状态。

## 5. 与 ROS2 驱动建立连接

1. 上位机启动：
   ```bash
   ros2 launch ur10_assembly_real_control ur10_assembly_real.launch.py robot_ip:=<机器人IP> ur_type:=ur10
   ```
2. 确保示教器程序仍在 `External Control` 节点运行。
3. 在上位机检查：
   - `/joint_states` 有数据
   - `scaled_joint_trajectory_controller` 为 `active`
   - `/scaled_joint_trajectory_controller/follow_joint_trajectory` action 在线

## 6. 常见问题

- 示教器未运行 External Control 程序：driver 会连接失败或无运动。
- IP 配置错误：无法建立通信。
- 控制器未激活：MoveIt 能规划但 Execute 失败。
- 同时存在自定义 RTDE 写入程序：可能与官方 driver 冲突，必须停用。

## 7. 安全建议

- 首次联调仅执行小幅、低速轨迹。
- 先在 RViz2 将 `Start State` 设为 `Current` 再规划执行。
- 现场预留急停与人工监护。
