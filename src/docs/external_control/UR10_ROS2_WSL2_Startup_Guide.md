# UR10 + ROS2 Humble + WSL2 每次开机连接操作步骤

本文档用于记录：每次重新打开电脑、WSL2 和 UR10 示教器后，如何重新建立 **UR10 真机 ↔ Windows ↔ WSL2 ↔ ROS2 driver ↔ MoveIt2/RViz2** 的连接。

当前已验证可用配置：

| 项目 | 值 |
|---|---|
| UR10 / 示教器 IP | `10.160.9.21` |
| Windows 有线网卡 IP | `10.160.9.100` |
| 子网掩码 | `255.255.255.0` |
| External Control Host IP | `10.160.9.100` |
| External Control Port | `50002` |
| ROS2 工作空间 | `~/ur10_ws` |
| ROS2 版本 | Humble |
| 真机 driver | `ur_robot_driver` |
| MoveIt 配置包 | `assembly_moveit_config` |
| MoveIt 启动文件 | `assembly_moveit.launch.py` |
| 轨迹控制器 | `scaled_joint_trajectory_controller` |

---

## 0. 总体逻辑

UR10 真机控制链路不是单纯的 `ping` 通就可以。完整链路是：

```text
UR10 示教器 External Control
→ 连接 Windows 有线网卡 10.160.9.100:50002
→ Windows portproxy 转发到 WSL2_IP:50002
→ WSL2 中的 ur_robot_driver / ur_ros2_control_node
→ ROS2 controller_manager
→ scaled_joint_trajectory_controller
→ MoveIt2 / RViz2 发送轨迹
```

因此每次重启后要重点确认三件事：

```text
1. Windows ↔ UR10 网络正常
2. Windows 10.160.9.100:50002 正确转发到当前 WSL2 IP:50002
3. WSL2 里的 ur_robot_driver 已经启动并监听 50002，然后才能在示教器点运行 External Control
```

---

# 一、Windows 端 IP 设置

## 1. 设置 Windows 有线网卡 IP

进入：

```text
控制面板 / 网络和 Internet / 网络连接
→ 以太网
→ 属性
→ Internet 协议版本 4 TCP/IPv4
```

设置为：

```text
IP 地址：10.160.9.100
子网掩码：255.255.255.0
默认网关：留空
DNS：留空
```

UR10 示教器/控制柜 IP 保持：

```text
IP 地址：10.160.9.21
子网掩码：255.255.255.0
```

注意：电脑 IP 和机器人 IP **不能一样**，但要在同一个网段。

正确：

```text
电脑：10.160.9.100
UR10：10.160.9.21
```

错误：

```text
电脑：10.160.9.21
UR10：10.160.9.21
```

---

## 2. Windows PowerShell 测试 UR10 网络

打开 PowerShell，执行：

```powershell
ping 10.160.9.21
Test-NetConnection 10.160.9.21 -Port 29999
Test-NetConnection 10.160.9.21 -Port 30004
```

正常结果：

```text
TcpTestSucceeded : True
```

说明：

```text
29999：Dashboard 端口
30004：RTDE 端口
```

如果 `ping` 不通或端口不通，先检查：

```text
1. 网线
2. 交换机
3. Windows 有线网卡 IP
4. UR10 示教器 IP
5. 是否插错网口
```

---

# 二、示教器端设置

## 1. 确认 External Control 配置

示教器进入：

```text
Installation / 安装设置
→ URCaps
→ External Control
```

设置：

```text
Host IP: 10.160.9.100
Custom port: 50002
```

不要填错成：

```text
10.169.9.100      # 错误
192.168.140.122   # 错误
10.160.9.21       # 错误，这是机器人自己的 IP
```

设置后保存 Installation。

---

## 2. 确认 EtherNet/IP 已关闭

示教器进入：

```text
Installation / 安装设置
→ Fieldbus / Ethernet/IP
```

确认：

```text
EtherNet/IP：Disabled / 已禁用
```

说明：关闭 EtherNet/IP 不会断开普通网络通信。它只是关闭 PLC/现场总线功能。

如果 EtherNet/IP 开着，可能导致：

```text
speed_slider_mask is currently controlled by another RTDE client
```

该错误会导致 `ur_robot_driver` 启动失败，进而导致 `50002` 不监听。

---

# 三、WSL2 端确认当前 IP

每次重新打开 WSL2 后，先查当前 WSL2 IP：

```bash
hostname -I
```

例如输出：

```text
172.17.201.231
```

这个 IP 可能会变化。如果变化，Windows 的端口转发规则也必须更新。

---

# 四、Windows portproxy 映射到 WSL2

UR10 连接的是：

```text
10.160.9.100:50002
```

但 ROS2 driver 实际运行在 WSL2 内部，所以必须配置 Windows 端口转发：

```text
10.160.9.100:50002 → WSL2_IP:50002
```

---

## 1. 查看当前 portproxy

Windows 管理员 PowerShell：

```powershell
netsh interface portproxy show all
```

正确示例：

```text
侦听 ipv4:                 连接到 ipv4:
地址            端口        地址            端口
--------------- ----------  --------------- ----------
10.160.9.100    50002       172.17.201.231  50002
```

如果 WSL2 当前 IP 不是 `172.17.201.231`，需要删除旧规则并重新添加。

---

## 2. 删除旧转发规则

Windows 管理员 PowerShell：

```powershell
netsh interface portproxy delete v4tov4 listenaddress=10.160.9.100 listenport=50002
```

如果提示：

```text
系统找不到指定的文件。
```

说明之前没有这条规则，不是问题。

---

## 3. 添加新转发规则

把 `172.17.201.231` 换成你当前 `hostname -I` 查到的 WSL2 IP：

```powershell
netsh interface portproxy add v4tov4 listenaddress=10.160.9.100 listenport=50002 connectaddress=172.17.201.231 connectport=50002
```

---

## 4. 放行 Windows 防火墙

Windows 管理员 PowerShell：

```powershell
New-NetFirewallRule -DisplayName "UR ROS2 External Control 50002" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 50002
```

如果提示规则已存在，可以忽略。

---

# 五、启动 ROS2 driver

## 1. 清理旧进程

WSL2 终端执行：

```bash
cd ~/ur10_ws

pkill -f ur_ros2_control_node
pkill -f ur_robot_driver
pkill -f dashboard_client
pkill -f controller_stopper_node
pkill -f robot_state_helper
pkill -f urscript_interface
pkill -f robot_state_publisher
pkill -f trajectory_until_node
pkill -f rviz2
pkill -f move_group
pkill -f "ros2 control"
```

检查是否清干净：

```bash
ps aux | grep -E "ur_|ros2|rtde|dashboard|controller_manager|urscript" | grep -v grep
```

最好没有输出。

---

## 2. 启动 UR driver

WSL2 终端 1：

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch ur_robot_driver ur_control.launch.py \
  ur_type:=ur10 \
  robot_ip:=10.160.9.21 \
  use_mock_hardware:=false \
  launch_rviz:=false
```

这个终端必须保持运行，不能关闭，不能 `Ctrl+C`，不能 `Ctrl+Z`。

---

## 3. 确认 WSL2 中监听 50002

另开 WSL2 终端：

```bash
ss -lntp | grep 50002
```

正常应看到：

```text
LISTEN 0 1 0.0.0.0:50002 0.0.0.0:* users:(("ur_ros2_control",pid=...,fd=...))
```

---

## 4. 确认 Windows 有线网卡监听 50002

Windows PowerShell：

```powershell
netstat -ano | findstr 50002
```

正常应看到：

```text
TCP    10.160.9.100:50002     0.0.0.0:0     LISTENING     xxxx
```

如果只看到：

```text
TCP    127.0.0.1:50002        0.0.0.0:0     LISTENING     xxxx
```

不够。UR10 不能连接 `127.0.0.1`，必须看到 `10.160.9.100:50002`。

---

# 六、示教器运行 External Control

只有满足以下条件后，才在示教器点运行：

```text
1. WSL2 ur_robot_driver 正在运行
2. WSL2 中 ss -lntp 能看到 0.0.0.0:50002
3. Windows netstat 能看到 10.160.9.100:50002 LISTENING
4. 示教器 External Control Host IP = 10.160.9.100
5. 示教器 External Control Port = 50002
6. 机器人无急停、无保护停止、刹车释放、速度滑块不是 0%
```

然后示教器按运行按钮。

成功时，WSL2 driver 终端会出现类似：

```text
Robot requested program
Sent program to robot
```

这说明示教器已经成功连接 ROS2 driver。

---

# 七、激活轨迹控制器

WSL2 终端 2：

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 control switch_controllers \
  --activate scaled_joint_trajectory_controller \
  --strict

ros2 control list_controllers
```

确认：

```text
scaled_joint_trajectory_controller    active
joint_state_broadcaster               active
io_and_status_controller              active
speed_scaling_state_broadcaster       active
force_torque_sensor_broadcaster       active
tcp_pose_broadcaster                  active
ur_configuration_controller           active
```

检查 action：

```bash
ros2 action list | grep follow_joint_trajectory
```

应看到：

```text
/scaled_joint_trajectory_controller/follow_joint_trajectory
```

---

# 八、检查真机关节状态

WSL2 终端：

```bash
ros2 topic echo /joint_states --once
```

能看到 6 个关节的位置即可。

例如：

```text
shoulder_lift_joint
elbow_joint
wrist_1_joint
wrist_2_joint
wrist_3_joint
shoulder_pan_joint
```

---

# 九、启动 MoveIt2 + RViz2

当前工作空间没有 `ur_moveit_config`，使用的是：

```text
assembly_moveit_config
```

启动：

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch assembly_moveit_config assembly_moveit.launch.py
```

启动后检查：

```bash
ros2 node list | grep move_group
ros2 topic list | grep monitored_planning_scene
```

正常应看到：

```text
/move_group
/monitored_planning_scene
```

如果 RViz2 的 MotionPlanning 显示：

```text
No Planning Scene Loaded
```

通常说明 `move_group` 没有启动或 RViz 没连接到正确的 MoveIt 配置。

---

# 十、RViz2 小范围运动测试

首次真机运动测试必须保守：

```text
1. 示教器速度滑块调到 10%~20%
2. 人站在急停旁边
3. Start State 设为 Current
4. Goal State 不要拉太远，只移动末端一点点
5. 先点 Plan
6. 确认轨迹很短、平滑、没有绕大圈
7. 再点 Execute
```

不要第一次就用大范围目标或复杂路径。

---

# 十一、常见故障判断

## 1. 示教器报 Connection refused

含义：

```text
10.160.9.100:50002 可达，但没有服务监听
```

检查：

```bash
ss -lntp | grep 50002
```

Windows：

```powershell
netstat -ano | findstr 50002
```

---

## 2. 示教器报 No route to host

含义：Host IP 填错或不在同一网段。

检查 External Control Host IP 必须是：

```text
10.160.9.100
```

不要填成：

```text
10.169.9.100
192.168.xxx.xxx
10.160.9.21
```

---

## 3. 示教器报 Connection reset

含义：之前连接上了，但电脑端 driver 被关掉或中断。

处理：重新启动 `ur_robot_driver`，然后示教器重新运行 External Control。

---

## 4. `speed_slider_mask is currently controlled by another RTDE client`

原因通常是 EtherNet/IP、Fieldbus、PLC 或其他 RTDE 写入客户端占用了 RTDE input fields。

处理：

```text
1. 关闭 EtherNet/IP
2. 保存 Installation
3. 重启 UR 控制柜
4. 断开交换机上其他可能连接 UR10 的设备
5. 不运行任何 Python/MATLAB/RTDE 脚本
6. 重新启动 ur_robot_driver
```

---

## 5. `Pipeline producer overflowed! <RTDE Data Pipeline>`

通常与 WSL2 性能、RViz2 占资源、系统时间跳变有关。

如果频繁出现：

```text
1. driver 启动时使用 launch_rviz:=false
2. 减少同时运行的程序
3. 尽量不要在 WSL2 中开太多图形界面
4. 正式实验建议使用原生 Ubuntu 或工控机
```

---

# 十二、推荐启动顺序速查

## Windows PowerShell

```powershell
ping 10.160.9.21
Test-NetConnection 10.160.9.21 -Port 29999
Test-NetConnection 10.160.9.21 -Port 30004
netsh interface portproxy show all
netstat -ano | findstr 50002
```

## WSL2 终端 1：启动 driver

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch ur_robot_driver ur_control.launch.py \
  ur_type:=ur10 \
  robot_ip:=10.160.9.21 \
  use_mock_hardware:=false \
  launch_rviz:=false
```

## WSL2 终端 2：检查并激活控制器

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ss -lntp | grep 50002

ros2 control switch_controllers \
  --activate scaled_joint_trajectory_controller \
  --strict

ros2 control list_controllers
ros2 topic echo /joint_states --once
```

## WSL2 终端 3：启动 MoveIt2/RViz2

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch assembly_moveit_config assembly_moveit.launch.py
```

---

# 十三、关键注意事项

1. `ur_robot_driver` 终端不能关闭。关闭后示教器会报 `Connection reset`。
2. WSL2 IP 可能变化，变化后必须更新 `portproxy`。
3. EtherNet/IP 保持关闭，否则可能再次出现 `speed_slider_mask`。
4. External Control Host IP 永远填 Windows 有线网卡 IP：`10.160.9.100`。
5. `10.160.9.21` 是机器人 IP，不要填到 Host IP。
6. 正式实验前建议用 `ur_calibration` 提取真实 UR10 标定，否则 TCP 精度有风险。
7. 真机第一次运动必须低速、小范围、有人看急停。

