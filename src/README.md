# UR10 主线任务总说明（ROS 2 Humble）

## 0. 适用范围与版本

- 工作区：`/root/ur10_ws/src`
- 适用系统：ROS 2 Humble
- 本文主线范围（唯一主线）：
  - UR10 仿真 + MoveIt2 路径规划（`ur10_simulation_bringup`）
  - UR10 实机通信 + MoveIt2 微动验证（`ur10_real_comm`）
  - FT300 力传感器采集与发布（`FT300/ft300_gui_ros2`）
  - 双 GUI 协同：
    - `ur10_unified_gui/main.py`
    - `FT300/ft300_gui_ros2/ft300_gui_ros2/ft300_gui_node.py`

说明：本文不把 `my_robot*` 系列作为主线，`my_robot*` 仍可作为独立分支使用。

---

## 1. 项目主线一图看懂

```text
[场景A 仿真规划链]
ur10_unified_gui(可选) -> ur10_simulation_bringup/complete_simulation.launch.py
                         -> gazebo_sim.launch.py + moveit_planning.launch.py + demo_nodes.launch.py
                         -> Gazebo + MoveIt2 + (可选)示例节点/感知节点

[场景B 实机通信链]
ur10_unified_gui(Real) 或命令行
-> ur10_real_comm/real_comm_moveit_verify.launch.py
-> ur_robot_driver + ur10_moveit_config + motion_verify_node
-> /ur10_real_comm/status + /ur10_real_comm/confirm_execute

[场景C FT300感知链]
FT300/ft300_gui_ros2/ft300_gui.launch.py
-> ft300_gui_node (内置 GUI)
-> 串口读取 FT300 + 发布 /ft300/wrench + 会话保存 CSV/PNG/JSON

[场景D 双GUI协同]
GUI1: ur10_unified_gui/main.py (负责 UR10 Real/Sim 编排)
GUI2: ft300_gui_node.py 对应 GUI (负责 FT300 USB测试/采集/保存)
```

### 非主线/历史参考（保留但不作为当前主链路）

- `FT300/my_robotiq_force_torque_sensor-master`：ROS1 风格 FT300 通信包（历史参考）
- `FT300/robotiq_ft_sensor_dev_v1.0.1_20210317`：Robotiq 底层驱动开发包（参考/调试资料）
- `docs/ur10_real_comm_实机微动验证总结/ur10_server_.py`：实机 TCP 控制脚本（专项工具，不是 ROS2 主线启动入口）

---

## 2. 主线包与核心节点清单

| 包/入口 | 关键节点或进程 | 作用 | 关键话题/服务 |
| --- | --- | --- | --- |
| `ur10_simulation_bringup` (`complete_simulation.launch.py`) | Gazebo、`robot_state_publisher`、控制器 spawner、MoveIt launch、可选 demo/perception | 一键编排仿真规划链路 | 取决于下游节点，核心是 MoveIt 与控制器链路 |
| `ur10_real_comm` (`real_comm_moveit_verify.launch.py`) | `ur_control.launch.py` + MoveIt + `motion_verify_node` | 实机通信与微动验证 | `/ur10_real_comm/status`、`/ur10_real_comm/confirm_execute` |
| `FT300/ft300_gui_ros2` (`ft300_gui.launch.py`) | `ft300_gui_node`（带 tkinter+matplotlib GUI） | FT300 串口采集、可视化、保存与 ROS 发布 | `/ft300/wrench` |
| `ur10_unified_gui/main.py` | GUI 编排进程（Real/Sim） | 一体化启动和状态监控（UR10链路） | 通过脚本/launch 间接驱动，不直接新增固定 ROS 话题 |

### `complete_simulation.launch.py` 编排关系（重点）

`complete_simulation.launch.py` 会按顺序组织：

1. （可选）清理历史残留进程
2. 启动 `gazebo_sim.launch.py`
3. 启动 `moveit_planning.launch.py`
4. （可选）启动 demo/perception/py tools 节点

---

## 3. 启动手册（按场景）

> 所有场景默认先执行：

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
```

### 场景 A：仅仿真（Gazebo + MoveIt2 + 可选 demo）

#### 前置条件
- 已完成编译（至少包含 `ur10_simulation_bringup` 及其依赖包）。
- 本机图形环境可打开 Gazebo/RViz。 

#### 启动命令（推荐最小）

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py \
  start_cpp_demo:=false \
  start_py_demo:=false \
  start_py_tools:=false \
  start_rviz:=true
```

#### 成功判据
- Gazebo 正常打开并加载 UR10/gantry。
- MoveIt2（RViz）可看到模型与规划场景。

#### 停止方式
- 当前终端 `Ctrl+C`。
- 如有残留进程，再次启动时可启用 `cleanup_existing_processes:=true`。

---

### 场景 B：仅实机通信与路径验证（UR 驱动 + MoveIt + 微动验证）

#### 前置条件
- UR 控制器网络连通（`robot_ip`/`reverse_ip` 正确）。
- 机器人端 External Control 配置一致。 

#### 启动命令

```bash
ros2 launch ur10_real_comm real_comm_moveit_verify.launch.py \
  robot_ip:=192.168.56.101 \
  reverse_ip:=192.168.56.1 \
  wrist3_delta_deg:=0.5 \
  confirm_execute:=true
```

#### 执行确认（当 `confirm_execute:=true`）

```bash
ros2 service call /ur10_real_comm/confirm_execute std_srvs/srv/Trigger "{}"
```

#### 成功判据
- `/ur10_real_comm/status` 有状态输出，最终出现 `PASS` 或明确 `FAIL` 原因。 

#### 停止方式
- 启动终端 `Ctrl+C`。

---

### 场景 C：仅 FT300 采集可视化

#### 前置条件
- FT300 通过 USB-RS485 接入，串口可见（如 `/dev/ttyUSB0`）。
- 已安装依赖：`python3-serial`、`python3-matplotlib`、`python3-numpy`。

#### 启动命令

```bash
ros2 launch ft300_gui_ros2 ft300_gui.launch.py
```

#### GUI 使用流程
1. 点击 `USB测试连接`
2. 点击 `开始采集`
3. 观察实时曲线与数值
4. 点击 `停止采集并保存`

#### 成功判据
- GUI 显示 USB 通信正常。
- `ros2 topic echo /ft300/wrench` 能持续看到数据。 
- 保存目录出现 `CSV + PNG + JSON`。

#### 停止方式
- 在 GUI 点击 `退出` 或终端 `Ctrl+C`。

---

### 场景 D：双 GUI 协同（UR10 总编排 GUI + FT300 GUI）

#### 前置条件
- 同时满足场景 A/B 与场景 C 对应前置条件。
- 建议两个终端分别运行，避免日志混杂。

#### 启动步骤

终端 1（UR10 编排 GUI）：

```bash
cd /root/ur10_ws/src/ur10_unified_gui
python3 main.py
```

终端 2（FT300 GUI）：

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
ros2 launch ft300_gui_ros2 ft300_gui.launch.py
```

#### 推荐操作顺序
1. 先在 GUI1（`ur10_unified_gui`）启动你当前需要的 UR10 场景（Real 或 Sim）。
2. 再在 GUI2（FT300）完成 USB 测试并开始采集。
3. 需要保存传感器数据时，先在 GUI2 停止并保存，再停 UR10 任务。

#### 并行注意点
- GUI1 与 GUI2 不共享同一串口，不冲突。
- GUI1 主要调度 UR10 链路；GUI2 只负责 FT300。
- 建议分终端运行，便于独立停止。

---

## 4. 两个 GUI 怎么用（职责边界）

### GUI1：`/root/ur10_ws/src/ur10_unified_gui/main.py`

用途：
- UR10 主线编排入口（Real/Sim）
- 快速网络检查
- 启停流程与日志汇总

不负责：
- FT300 串口采集和传感器曲线显示

### GUI2：`/root/ur10_ws/src/FT300/ft300_gui_ros2/ft300_gui_ros2/ft300_gui_node.py`

用途：
- FT300 USB连接测试
- 实时六维力/力矩曲线
- 发布 `/ft300/wrench`
- 会话保存（CSV/PNG/JSON）

不负责：
- UR10 Real/Sim 全链路编排

---

## 5. 常见混乱点与排查

### 5.1 如何区分“主线包”与“测试包”

主线包判断标准（满足多数即可）：
- 有稳定 launch 入口，并在当前任务长期使用。
- 对应 UR10 主链目标（仿真、实机、规划、FT300采集）。

测试/历史包特征：
- 仅用于协议试验、历史兼容、单点验证。
- ROS1 旧包或仅底层驱动源码资料。

### 5.2 `source` 顺序与 Python 解释器

推荐固定写法：

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
```

若出现 Python 模块找不到：
- 先确认当前解释器：`which python3`
- 再确认依赖安装在该解释器环境。

### 5.3 实机网络参数排查（UR）

- `robot_ip`：UR 控制器地址
- `reverse_ip`：UR 回连到主机的地址
- 快速检查：

```bash
ping -c 1 <robot_ip>
```

### 5.4 `real_comm_moveit_verify.launch.py` 已知兼容问题

在当前环境中，执行：

```bash
ros2 launch ur10_real_comm real_comm_moveit_verify.launch.py ...
```

可能报错：

`ImportError: cannot import name 'ConcatSubstitution' from 'launch.substitutions'`

建议临时替代方式：

1. 使用 GUI1（`ur10_unified_gui/main.py`）的 Real 模式启动。
2. 或直接运行：

```bash
cd /root/ur10_ws/src/ur10_real_comm/scripts
./run_full_verify.sh
```

### 5.5 FT300 串口排查

```bash
ls /dev/ttyUSB*
sudo chmod 666 /dev/ttyUSB0
```

若 USB 测试失败：
- 检查端口号、波特率（默认 19200）与接线。
- 检查串口是否被其它进程占用。

---

## 6. 常用命令模板（复制即用）

### 构建

```bash
cd /root/ur10_ws
colcon build --packages-select ur10_simulation_bringup ur10_real_comm ft300_gui_ros2
```

### 环境

```bash
source /opt/ros/humble/setup.bash && source /root/ur10_ws/install/setup.bash
```

### 仿真主线

```bash
ros2 launch ur10_simulation_bringup complete_simulation.launch.py
```

### 实机验证主线

```bash
ros2 launch ur10_real_comm real_comm_moveit_verify.launch.py robot_ip:=192.168.56.101 reverse_ip:=192.168.56.1
```

### FT300 GUI

```bash
ros2 launch ft300_gui_ros2 ft300_gui.launch.py
```

### UR10 编排 GUI

```bash
python3 /root/ur10_ws/src/ur10_unified_gui/main.py
```

---

## 7. 以后新增包时如何归类（防止再次混乱）

新增包请先归类到以下四类之一：

1. `mainline-core`：主线必需（可进入本 README 主流程）
2. `mainline-optional`：主线可选扩展（可在场景里写“可选”）
3. `tooling`：调试/GUI/脚本工具（独立说明，不混入核心启动链）
4. `archive-test`：历史或实验包（统一放“非主线/历史参考”）

建议每个新增包至少补一条记录：
- 启动入口
- 依赖谁
- 对外话题/服务
- 归类标签

这样你后续看 `src` 时，能快速判断“该启动什么、该忽略什么”。
