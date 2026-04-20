# 实机网线通信与驱动启动

适合谁看：已经把仿真跑起来，下一步想通过网线把电脑接到真实 UR10 控制器的人。

本文档说明两件事：

1. PC 和 UR10 控制柜之间的网线通信应该怎么配
2. 在本工作区里应该如何启动 `ur_robot_driver`

相关文件：

- `/root/ur10_ws/src/ur10_simulation_bringup/config/real_robot_network.yaml`
- `/root/ur10_ws/src/ur10_simulation_bringup/config/netplan_ur10_pc.yaml.example`
- `/root/ur10_ws/src/ur10_simulation_bringup/config/real_robot.env.example`
- `/root/ur10_ws/src/ur10_simulation_bringup/launch/real_robot_driver.launch.py`

## 1. 你要准备什么

- 一台运行 Ubuntu / ROS 2 Humble 的 PC
- 一台真实 UR10 控制柜
- 一根网线
- `ur_robot_driver`
- 机器人端已经安装 `External Control` URCap

如果没有安装 `External Control` URCap，ROS 2 驱动即使网络是通的，也无法正常接管机器人执行轨迹。

## 2. 推荐的网络规划

推荐直接使用一条独立网线，把 PC 和 UR 控制柜放在同一个小网段中：

- 机器人 IP：`192.168.56.101`
- PC IP：`192.168.56.1`
- 子网掩码：`255.255.255.0`

这套默认值已经写进：

```text
/root/ur10_ws/src/ur10_simulation_bringup/config/real_robot_network.yaml
```

## 3. 电脑端网卡怎么配

### 3.1 找到你的网卡名

先在电脑上查看网卡名：

```bash
ip a
```

常见网卡名例如：

- `eno1`
- `enp3s0`
- `eth0`

### 3.2 配置静态 IP

本项目提供了一个 Netplan 模板：

```text
/root/ur10_ws/src/ur10_simulation_bringup/config/netplan_ur10_pc.yaml.example
```

核心意思就是：

- 关闭 DHCP
- 给你的物理网卡一个固定地址
- 让它和机器人在同一网段

模板内容类似：

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1:
      dhcp4: false
      addresses:
        - 192.168.56.1/24
      mtu: 1500
```

你需要做的是：

1. 把 `eno1` 改成你的真实网卡名
2. 把文件放到 `/etc/netplan/` 下
3. 执行：

```bash
sudo netplan apply
```

### 3.3 验证 PC IP

配置好后执行：

```bash
ip a show eno1
```

你应该能看到类似：

```text
inet 192.168.56.1/24
```

## 4. 机器人端怎么配

在 UR 控制柜或示教器中，把机器人网络设置为：

- IP：`192.168.56.101`
- Netmask：`255.255.255.0`
- Gateway：可留空或与现场网络规划一致

如果你现场已经有固定网段，不一定必须用 `192.168.56.x`，但必须保证：

- PC 和机器人在同一个二层网络里
- `robot_ip` 是机器人自己的 IP
- `reverse_ip` 是 PC 网卡的静态 IP

## 5. 先做最基础连通性检查

网线接好、两边 IP 配好后，在 PC 上执行：

```bash
ping 192.168.56.101
```

如果 `ping` 不通，先不要启动驱动。优先检查：

- 网线是否接对
- 网卡名是否写错
- PC 是否真的拿到了静态 IP
- 机器人 IP 是否设置正确
- 防火墙或交换机是否拦截

## 6. UR 驱动会用到哪些端口

本项目默认沿用 `ur_robot_driver` 的常用端口：

- Dashboard：`29999`
- Reverse：`50001`
- Script sender：`50002`
- Trajectory：`50003`
- Script command：`50004`

这些值也已经写进：

```text
/root/ur10_ws/src/ur10_simulation_bringup/config/real_robot_network.yaml
```

如果你的现场网络策略比较严格，需要确保这些端口没有被占用、也没有被防火墙拦截。

## 7. 本项目里提供了什么实机配置模板

### `real_robot_network.yaml`

这是给人看的总配置模板，集中写了：

- PC 网卡名
- PC IP
- 机器人 IP
- 子网掩码
- ROS 驱动要用的端口

### `real_robot.env.example`

这是环境变量风格的模板，适合你以后做：

- shell 脚本
- `.env` 文件
- CI 或部署脚本

### `real_robot_driver.launch.py`

这是本项目对 `ur_robot_driver/launch/ur_control.launch.py` 的一层包装。

它的目的不是替代官方驱动，而是给你一个更直接的本项目入口。

## 8. 如何启动真实 UR10 驱动

先开一个新终端：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
```

然后启动实机驱动：

```bash
ros2 launch ur10_simulation_bringup real_robot_driver.launch.py \
  ur_type:=ur10 \
  robot_ip:=192.168.56.101 \
  reverse_ip:=192.168.56.1
```

如果你不想开 RViz：

```bash
ros2 launch ur10_simulation_bringup real_robot_driver.launch.py \
  ur_type:=ur10 \
  robot_ip:=192.168.56.101 \
  reverse_ip:=192.168.56.1 \
  launch_rviz:=false
```

## 9. 这个 launch 实际做了什么

`real_robot_driver.launch.py` 内部会继续调用官方的：

```text
ur_robot_driver/launch/ur_control.launch.py
```

它只是提前把你最常需要改的参数整理成了统一入口，例如：

- `ur_type`
- `robot_ip`
- `reverse_ip`
- `launch_rviz`
- `launch_dashboard_client`
- `initial_joint_controller`

## 10. 首次接真机时建议的顺序

建议按下面顺序做，不要一上来就直接下轨迹：

1. 先确认 PC 网卡是静态 IP
2. 先确认 `ping robot_ip` 能通
3. 先确认机器人端已经安装并启动 `External Control` URCap
4. 再运行 `real_robot_driver.launch.py`
5. 确认 `/joint_states` 正常更新
6. 再考虑接 MoveIt 或上层控制

## 11. 连接成功后你应该看到什么

成功时，通常会出现这些特征：

- 驱动节点正常启动
- `joint_states` 持续刷新
- Dashboard 客户端可连接
- 控制器可以正常加载

你可以开新终端检查：

```bash
source /opt/ros/humble/setup.bash
source /root/moveit_ws/install/setup.bash
source /root/ur10_ws/install/setup.bash
ros2 topic echo /joint_states --once
```

## 12. 常见问题

### `ping` 不通

优先检查：

- 机器人和 PC 是否在同一子网
- 网卡名是否填错
- 网线和交换机是否正常

### 驱动起了，但机器人不执行

优先检查：

- `External Control` URCap 是否已安装
- 示教器程序是否已进入 External Control
- `reverse_ip` 是否写成了 PC 网卡 IP，而不是机器人 IP

### `robot_ip` 和 `reverse_ip` 容易混

记住：

- `robot_ip`：机器人控制柜自己的 IP
- `reverse_ip`：机器人回连 PC 时要连接的 PC IP

## 13. 你最常需要改哪几个值

以后你最常改的是这几个：

- `robot_ip`
- `reverse_ip`
- `pc_nic_name`
- `ur_type`

如果你换了一台电脑，最先检查的是 `pc_nic_name` 和 `reverse_ip`。

## 14. 推荐下一步阅读

下一篇建议阅读：[运行手册](03_runbook.md)
