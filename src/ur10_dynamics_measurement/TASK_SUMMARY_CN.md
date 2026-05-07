# ur10_dynamics_measurement ROS2 包 — 任务完成总结

## 概述

新建了 `ur10_dynamics_measurement` ROS2 Python 包，用于实时采集 UR10 机器人动力学数据，包含 PyQt5 GUI 可视化界面。包通过 ROS2 原生协议（非 TCP/串口）订阅 `/joint_states` 和 `io_and_status_controller/ft_data` 主题，实现关节扭矩估算、FT300 力传感器数据映射、CSV 记录等功能。

## 包结构

```
ur10_dynamics_measurement/
├── package.xml                        # ROS2 包描述
├── setup.py                           # Python 包安装配置
├── setup.cfg                          # setuptools 配置
├── launch/
│   └── measurement_gui.launch.py      # ROS2 启动文件
├── ur10_dynamics_measurement/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  # MeasurementConfig 数据类
│   │   ├── kinematics.py              # UR10 运动学正解 + 几何雅可比
│   │   ├── dynamics_estimator.py      # 扭矩估算 + FT→关节映射
│   │   ├── robot_data_listener.py     # ROS2 订阅节点
│   │   └── data_recorder.py           # CSV 记录 + 元数据
│   └── gui/
│       ├── __init__.py
│       └── main_window.py             # PyQt5 主窗口
```

## 功能模块

### 1. 运动学模块 (`kinematics.py`)
- 基于 URDF 原始 DH 参数构建 6-DOF 运动学链
- `forward_kinematics(q)` — 计算 TCP 位姿（4×4 齐次变换矩阵）
- `compute_jacobian(q)` — 6×6 几何雅可比矩阵（基坐标系下）
- FT300 安装偏移：平移 [0, 0.09, 0]m, RPY [-π/2, 0, 0]
- **注意事项**：雅可比中关节轴原点位置需准确包含 URDF 子关节平移，经修复后可在非奇异位姿达到满秩 6

### 2. 动力学估算器 (`dynamics_estimator.py`)
- `estimate_joint_torques(currents)` — 电机电流→关节扭矩：τ = K × I
- `compute_ft_joint_torques(q, force, torque)` — FT300 力/力矩通过雅可比转置映射到关节空间
- `compute_residual(tau_est, tau_ft)` — 扭矩残差计算

### 3. ROS2 数据监听器 (`robot_data_listener.py`)
- 订阅 `/joint_states`（位置、速度、电机电流）
- 订阅 `io_and_status_controller/ft_data`（FT300 六维力/力矩）
- 线程安全数据缓存（`threading.Lock` 保护）
- FT300 清零（Tare）：采集 N=100 帧运行平均值作为零偏

### 4. 数据记录器 (`data_recorder.py`)
- 每次记录创建独立会话目录（`YYYYMMDD_HHMMSS/`）
- CSV 文件：42 列，包含时间戳、关节位置/速度/电流、估算扭矩、FT300 六维数据、映射扭矩、清零标记等
- 每 20 行 flush 一次，防止数据丢失
- 自动生成 `session_metadata.txt` 记录实验上下文

### 5. GUI 主窗口 (`main_window.py`)
- ROS2 订阅数据实时曲线显示（2×3 网格）：
  - 关节角度 q₀–q₅
  - 关节速度 dq₀–dq₅
  - 电机电流 I₀–I₅
  - 估算扭矩 τ_est = K·I
  - FT300 力/力矩 (Fx, Fy, Fz, Mx, My, Mz)
  - FT 映射扭矩 τ_ft = Jᵀ·F
- 开始/停止记录、力传感器清零按钮
- 定时器架构：ROS 50Hz 轮询，绘图 20Hz 刷新，状态 4Hz 更新

### 6. 节点列表

| 节点名 | 类型 | 功能 |
|--------|------|------|
| `ur10_dynamics_measurement_gui` | `measurement_gui` | 主节点，内嵌 ROS2 订阅 + GUI |

## 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 电机增益 K₁–K₆ | [13.5841, 14.2959, 11.3716, 11.2408, 11.7681, 11.7682] Nm/A | 源自 codeocean 项目 |
| 关节命名 | `shoulder_pan/lift/elbow/wrist_1/2/3_joint` | UR 官方 Driver 命名 |
| FT300 安装 | [0, 0.09, 0]m, RPY[-π/2, 0, 0] | wrist_3 末端固定连接 |
| ROS 轮询频率 | 50 Hz | QTimer(20ms) + spin_once |
| 绘图刷新频率 | 20 Hz | pyqtgraph |
| 数据订阅主题 | `/joint_states`, `io_and_status_controller/ft_data` | |

## 使用方法

```bash
# 启动 GUI（需先启动 UR Driver）
ros2 launch ur10_dynamics_measurement measurement_gui.launch.py

# 或直接运行
ros2 run ur10_dynamics_measurement measurement_gui

# 启停参数设置
ros2 launch ur10_dynamics_measurement measurement_gui.launch.py \
    joint_states_topic:=/joint_states \
    ft_data_topic:=io_and_status_controller/ft_data \
    data_root:=~/.ros/ur10_measurement_data
```

## 数据流

```
UR Driver (RTDE)          measurement_gui (PyQt5 + rclpy)
================          ==================================
/joint_states ───────→ RobotDataListener (50Hz spin_once)
ft_data ─────────────→        │
                               ├─→ DynamicsEstimator.estimate_joint_torques(currents)
                               ├─→ DynamicsEstimator.compute_ft_joint_torques(q, wrench)
                               │    └─→ UR10Kinematics.compute_jacobian(q)
                               │    └─→ τ_ft = J(q)ᵀ · F_base
                               ├─→ DataRecorder.write_row(data)  [录制中]
                               └─→ MainWindow 更新绘图缓冲区
```

## 修复记录

### 雅可比计算 bug 修复 (`kinematics.py:compute_jacobian`)
- **问题**：关节轴原点位置 `p_i` 错误地使用了前一个关节的输出帧位置（`frames[i][:3,3]`），没有包含子关节的 URDF 平移 `xyz_i`
- **影响**：所有绕 Y 轴旋转的关节（shoulder_lift, elbow, wrist_1）在雅可比中产生相同的列，导致 rank 始终为 5，FT→关节映射结果错误
- **修复**：`p_i = R_i @ xyz_i + frames[i][:3, 3]`
- **验证**：非奇异位姿雅可比 rank=6，奇异值分布合理

## 验证结果

- 包构建：`colcon build` 成功
- 雅可比：非奇异位姿满秩 6（home/伸展位姿 rank=5，属真实运动学奇异点）
- 扭矩估算：K×I 计算正确（已验证 K=[13.58, 14.30, 11.37, 11.24, 11.77, 11.77]）
- FT 映射：10N TCP X 方向力产生物理合理的关节扭矩分布
- 所有模块导入正常（config, kinematics, dynamics_estimator, data_recorder, robot_data_listener）
