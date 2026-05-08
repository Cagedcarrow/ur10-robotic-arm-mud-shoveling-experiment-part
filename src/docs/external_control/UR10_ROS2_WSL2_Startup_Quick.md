# UR10 + ROS2 + WSL2 每次启动精简流程

> 适用前提：你的网络地址保持不变。  
> Windows 有线网卡 IP：`10.160.9.100`  
> UR10 机器人 IP：`10.160.9.21`  
> WSL2 IP：`172.17.201.231`  
> 端口映射：`10.160.9.100:50002 -> 172.17.201.231:50002`

---

## 0. 固定配置确认

### Windows 有线网卡

```text
IP 地址：10.160.9.100
子网掩码：255.255.255.0
默认网关：留空
DNS：留空
```

### UR10 示教器网络

```text
机器人 IP：10.160.9.21
子网掩码：255.255.255.0
```

### 示教器 External Control

进入：

```text
Installation / 安装设置
→ URCaps
→ External Control
```

确认：

```text
Host IP：10.160.9.100
Custom port：50002
```

### EtherNet/IP

保持关闭：

```text
Installation / 安装设置
→ Fieldbus / EtherNet/IP
→ Disabled
```

---

## 1. Windows 端确认端口映射

打开 PowerShell，执行：

```powershell
netsh interface portproxy show all
```

应看到：

```text
10.160.9.100    50002    172.17.201.231    50002
```

再检查监听：

```powershell
netstat -ano | findstr 50002
```

如果 ROS2 driver 还没启动，可能暂时看不到 `10.160.9.100:50002 LISTENING`，这是正常的。

---

## 2. WSL2 终端 1：启动 UR ROS2 Driver

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

source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch ur_robot_driver ur_control.launch.py \
  ur_type:=ur10 \
  robot_ip:=10.160.9.21 \
  use_mock_hardware:=false \
  launch_rviz:=false
```

这个终端不要关闭。

---

## 3. WSL2 终端 2：确认 50002 监听

```bash
ss -lntp | grep 50002
```

正常应看到类似：

```text
LISTEN 0 1 0.0.0.0:50002 ... ur_ros2_control
```

然后 Windows PowerShell 再查：

```powershell
netstat -ano | findstr 50002
```

正常应看到：

```text
TCP    10.160.9.100:50002    0.0.0.0:0    LISTENING
```

---

## 4. 示教器运行 External Control

在示教器上：

```text
加载 External Control 程序
确认 Host IP = 10.160.9.100
确认 Port = 50002
确认机器人上电、刹车释放、无保护停止
点击运行 / Play
```

如果成功，WSL2 driver 终端会出现类似：

```text
Robot requested program
Sent program to robot
```

---

## 5. WSL2 终端 2：激活轨迹控制器

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
```

---

## 6. 检查关节状态

```bash
ros2 topic echo /joint_states --once
```

能看到 6 个关节位置即可。

---

## 7. 启动 MoveIt2 / RViz2

你的 MoveIt 配置包是：

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

---

## 8. RViz2 小范围测试

在 RViz2 MotionPlanning 面板中：

```text
Start State：Current
Goal State：Current
Planning Group：选择 UR10 机械臂组
```

第一次测试要求：

```text
1. 示教器速度滑块调到 10%~20%
2. 人站在急停旁边
3. 只拖动末端一点点
4. 先 Plan
5. 确认轨迹很短、无碰撞
6. 再 Execute
```

---

## 常见错误快速判断

### 1. 示教器报 Connection reset

说明 WSL2 里的 `ur_robot_driver` 被关闭或中断。重新执行第 2 步。

### 2. 示教器报 Connection refused

说明 Windows/WSL2 的 `50002` 没有正常监听。检查第 3 步。

### 3. 示教器报 No route to host

Host IP 填错。应为：

```text
10.160.9.100
```

### 4. driver 报 speed_slider_mask

通常是 EtherNet/IP、Fieldbus、其他 RTDE 客户端占用。保持 EtherNet/IP Disabled，并关闭其他 RTDE/Python/MATLAB 程序。

### 5. MoveIt2 里 No Planning Scene Loaded

说明 MoveIt2 没启动或 RViz 没连到 `move_group`。启动：

```bash
ros2 launch assembly_moveit_config assembly_moveit.launch.py
```

---

## 最小启动顺序总结

```text
1. Windows 确认 portproxy
2. WSL2 启动 ur_robot_driver
3. WSL2 确认 50002 监听
4. 示教器运行 External Control
5. 激活 scaled_joint_trajectory_controller
6. 检查 /joint_states
7. 启动 assembly_moveit_config
8. RViz2 小范围 Plan → Execute
```
