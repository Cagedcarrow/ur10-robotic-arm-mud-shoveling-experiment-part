# UR10 + ROS2 Humble + WSL2 每次启动检查步骤

## 固定配置

| 项目 | 值 |
|---|---|
| UR10 机器人 IP | `10.160.9.21` |
| Windows 有线网卡 IP | `10.160.9.100` |
| WSL2 IP | `172.17.201.231` |
| Driver reverse 端口 | `50001` |
| External Control script sender 端口 | `50002` |
| Driver trajectory 端口 | `50003` |
| Driver script command 端口 | `50004` |
| Windows portproxy | `10.160.9.100:50001-50004 -> WSL2_IP:50001-50004` |
| RTDE 端口 | `30004` |
| Dashboard 端口 | `29999` |

> 注意：如果 WSL2 IP 变了，必须重新设置 portproxy。当前文档默认 WSL2 IP 不变。

---

## 1. Windows 端检查机器人网络

在 Windows PowerShell 执行：

```powershell
ping 10.160.9.21
Test-NetConnection 10.160.9.21 -Port 29999
Test-NetConnection 10.160.9.21 -Port 30004
```

正常结果：

```text
TcpTestSucceeded : True
```

如果 `29999` 或 `30004` 不通，先不要启动 ROS2，优先检查：

- Windows 有线网卡是否仍是 `10.160.9.100`
- UR10 机器人 IP 是否仍是 `10.160.9.21`
- 网线/交换机是否正常
- 是否接错网卡

---

## 2. 示教器端检查

在 UR10 示教器中确认：

```text
Installation / 安装设置
→ URCaps
→ External Control
```

应设置为：

```text
Host IP: 10.160.9.100
Custom port: 50002
```

同时确认：

```text
EtherNet/IP: Disabled
```

> EtherNet/IP 是 PLC/Fieldbus 通信用的，不是普通 TCP/IP 网络。关闭它不会断开 ROS2 与机械臂的网络连接。它之前会导致 `speed_slider_mask` 被占用。

---

## 3. WSL2 启动前清理旧进程

在 WSL2 终端执行：

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

检查是否清理干净：

```bash
ps aux | grep -E "ur_|ros2|rtde|dashboard|controller_manager|urscript|move_group" | grep -v grep
```

理想情况：没有输出。

---

## 4. WSL2 启动 UR driver

在 WSL2 终端 1 执行：

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

正常启动时应看到：

```text
System successfully started!
Successful 'configure' of hardware 'ur10'
Successful 'activate' of hardware 'ur10'
Configured and activated scaled_joint_trajectory_controller
```

如果出现：

```text
speed_slider_mask is currently controlled by another RTDE client
```

优先检查：

- EtherNet/IP 是否关闭
- 是否还有其他 RTDE/Python/MATLAB/ROS2 程序连接机器人
- 交换机上是否还有其他电脑/PLC/工控机
- 是否需要重启 UR 控制柜

---

## 5. WSL2 检查 50001-50004 是否监听

另开 WSL2 终端 2，执行：

```bash
ss -lntp | grep -E ':(50001|50002|50003|50004)'
```

至少应看到 driver 对 External Control 和运动通道的监听。`50002` 只负责示教器请求程序；真实运动还依赖 `50001/50003/50004`。

```text
LISTEN 0 1 0.0.0.0:50002 0.0.0.0:* users:(("ur_ros2_control",pid=xxxx,fd=xx))
```

如果没有输出，说明 `ur_robot_driver` 没有成功监听 External Control 端口，示教器点击运行一定失败。

---

## 6. Windows 检查 portproxy 是否生效

在 Windows PowerShell 执行：

```powershell
netsh interface portproxy show all
netstat -ano | Select-String '50001|50002|50003|50004'
```

`portproxy show all` 应看到：

```text
10.160.9.100    50001       172.17.201.231  50001
10.160.9.100    50002       172.17.201.231  50002
10.160.9.100    50003       172.17.201.231  50003
10.160.9.100    50004       172.17.201.231  50004
```

`netstat` 必须看到 `10.160.9.100:50001-50004` 的监听。只看到 `50002` 不够，因为机器人可以成功请求程序，但轨迹命令无法走完整运动通道。

```text
TCP    10.160.9.100:50001     0.0.0.0:0     LISTENING     xxxx
TCP    10.160.9.100:50002     0.0.0.0:0     LISTENING     xxxx
TCP    10.160.9.100:50003     0.0.0.0:0     LISTENING     xxxx
TCP    10.160.9.100:50004     0.0.0.0:0     LISTENING     xxxx
```

只看到下面这个不够：

```text
TCP    127.0.0.1:50002        0.0.0.0:0     LISTENING     xxxx
```

因为 UR10 连接的是 `10.160.9.100:50002`，不是 `127.0.0.1:50002`。

---

## 7. 如果 Windows 没有监听 10.160.9.100:50002

### 7.1 先重启 IP Helper 服务

用管理员 PowerShell 执行：

```powershell
Restart-Service iphlpsvc -Force
```

然后检查：

```powershell
netstat -ano | Select-String '50001|50002|50003|50004'
```

如果看到：

```text
TCP    10.160.9.100:50002     0.0.0.0:0     LISTENING     xxxx
```

即可继续。

### 7.2 如果仍然没有，重建 portproxy

管理员 PowerShell 执行：

```powershell
netsh interface portproxy delete v4tov4 listenaddress=10.160.9.100 listenport=50001
netsh interface portproxy delete v4tov4 listenaddress=10.160.9.100 listenport=50002
netsh interface portproxy delete v4tov4 listenaddress=10.160.9.100 listenport=50003
netsh interface portproxy delete v4tov4 listenaddress=10.160.9.100 listenport=50004

netsh interface portproxy add v4tov4 listenaddress=10.160.9.100 listenport=50001 connectaddress=172.17.201.231 connectport=50001
netsh interface portproxy add v4tov4 listenaddress=10.160.9.100 listenport=50002 connectaddress=172.17.201.231 connectport=50002
netsh interface portproxy add v4tov4 listenaddress=10.160.9.100 listenport=50003 connectaddress=172.17.201.231 connectport=50003
netsh interface portproxy add v4tov4 listenaddress=10.160.9.100 listenport=50004 connectaddress=172.17.201.231 connectport=50004

Restart-Service iphlpsvc -Force

netsh interface portproxy show all
netstat -ano | Select-String '50001|50002|50003|50004'
```

---

## 8. 示教器运行 External Control

确认以下条件全部满足：

```text
1. WSL2 ur_robot_driver 终端仍在运行
2. WSL2: `ss -lntp | grep -E ':(50001|50002|50003|50004)'` 有监听
3. Windows: `netstat -ano | Select-String '50001|50002|50003|50004'` 有 `10.160.9.100:50001-50004 LISTENING`
4. 示教器 External Control Host IP = 10.160.9.100
5. 示教器 External Control Port = 50002
6. 机器人无急停、无保护停止
7. 机器人已上电、刹车释放
```

然后在示教器点击运行 External Control 程序。

成功后，WSL2 driver 终端应出现：

```text
Robot requested program
Sent program to robot
```

---

## 9. 检查 ROS2 控制器

在 WSL2 终端 2 执行：

```bash
cd ~/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 control list_controllers
```

应确认：

```text
joint_state_broadcaster                active
io_and_status_controller               active
speed_scaling_state_broadcaster        active
force_torque_sensor_broadcaster        active
tcp_pose_broadcaster                   active
ur_configuration_controller            active
scaled_joint_trajectory_controller     active
```

如果 `scaled_joint_trajectory_controller` 不是 active，执行：

```bash
ros2 control switch_controllers \
  --activate scaled_joint_trajectory_controller \
  --strict
```

再检查：

```bash
ros2 control list_controllers
```

---

## 10. 检查 joint_states

```bash
ros2 topic echo /joint_states --once
```

正常应看到 6 个 UR10 关节：

```text
shoulder_pan_joint
shoulder_lift_joint
elbow_joint
wrist_1_joint
wrist_2_joint
wrist_3_joint
```

如果能读到 `/joint_states`，说明 ROS2 已经能读取真机状态。

同时检查速度缩放：

```bash
ros2 topic echo /speed_scaling_state_broadcaster/speed_scaling --once
```

`data` 必须大于 `0.01`。如果为 `0.0`，controller 可能接受轨迹 goal，但真实机械臂不会运动，MoveIt 后续会报：

```text
Cannot push a new trajectory while another is being executed
```

此时检查示教器 External Control 程序是否仍在运行、速度滑块是否大于 0%、机器人是否处于保护停止或暂停状态。

---

## 11. 启动 MoveIt2 + RViz2

当前工作空间没有 `ur_moveit_config`，应使用：

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

检查 MoveIt 是否起来：

```bash
ros2 node list | grep move_group
ros2 topic list | grep monitored_planning_scene
```

正常应看到：

```text
/move_group
/monitored_planning_scene
```

---

## 12. 第一次小范围运动测试

在示教器上：

```text
速度滑块调到 10%~20%
人站在急停旁边
机械臂周围清空
```

在 RViz2 MotionPlanning 面板：

```text
Start State: Current
Goal State: Current
Planning Group: UR10 对应机械臂规划组
```

操作顺序：

```text
1. 只拖动末端一点点
2. 先点 Plan
3. 确认轨迹很短且不绕大圈
4. 再点 Execute
```

不要第一次就大范围拖动末端。

---

## 13. 常见错误速查

### 13.1 示教器显示 Connection refused

原因通常是：

```text
Windows 没有监听 10.160.9.100:50002
```

检查：

```powershell
netstat -ano | findstr 50002
```

必须看到：

```text
10.160.9.100:50002 LISTENING
```

如果没有：

```powershell
Restart-Service iphlpsvc -Force
```

---

### 13.2 示教器显示 No route to host

原因通常是 Host IP 填错，例如填成：

```text
10.169.9.100
192.168.xxx.xxx
```

正确应为：

```text
10.160.9.100
```

---

### 13.3 driver 报 speed_slider_mask

原因通常是 RTDE 写入资源被占用：

```text
speed_slider_mask is currently controlled by another RTDE client
```

处理：

```text
1. 关闭 EtherNet/IP
2. 停止所有 Python/MATLAB/RTDE/ROS2 程序
3. 检查交换机上是否还有其他电脑/PLC/工控机
4. 重启 UR 控制柜
5. 重新启动 ur_robot_driver
```

---

### 13.4 只看到 127.0.0.1:50002

不够。UR10 无法连接 `127.0.0.1`。

必须看到：

```text
10.160.9.100:50002 LISTENING
```

处理：

```powershell
Restart-Service iphlpsvc -Force
```

必要时重建 portproxy。

---

### 13.5 WSL2 终端关闭后示教器掉线

正常。External Control 依赖 WSL2 中运行的 `ur_robot_driver`。

如果关闭 driver 终端，示教器会出现：

```text
Connection reset
```

建议以后使用 `tmux` 保持 driver 运行：

```bash
tmux new -s ur_driver
```

在 tmux 中启动 driver。

离开 tmux：

```text
Ctrl+B，然后按 D
```

恢复 tmux：

```bash
tmux attach -t ur_driver
```

---

## 14. 每次最短启动流程

如果 IP 都没变，按这个顺序：

```text
1. Windows 确认 ping 10.160.9.21 通
2. WSL2 启动 ur_robot_driver
3. WSL2 检查 ss -lntp | grep 50002
4. Windows 检查 `netstat -ano | Select-String '50001|50002|50003|50004'`
5. 如果没有 10.160.9.100:50001-50004，执行 Restart-Service iphlpsvc -Force 或重建四个 portproxy
6. 示教器点击运行 External Control
7. 检查 driver 终端出现 Robot requested program / Sent program to robot
8. ros2 control list_controllers
9. 必要时激活 scaled_joint_trajectory_controller
10. 启动 assembly_moveit_config
11. RViz2 小范围 Plan → Execute
```
