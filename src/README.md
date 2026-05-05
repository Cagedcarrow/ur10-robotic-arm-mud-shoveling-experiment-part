# UR10 工作区 `src` 总览（当前主线）

## 1. 项目定位与当前主线

本目录是当前有效开发路线，仅保留以下 4 条主线：

- `ur_base_xarco_model`
- `experiment_data_recorder`
- `ur10_ft300_monitor`
- `intel_realsense`

历史 `ur10_*` 旧路线已归档为参考材料，不再作为当前开发依赖与启动入口。

---

## 2. 目录与职责总览

| 目录 | 主要用途 | 主要输入 | 主要输出 | 是否 ROS2 包 |
|---|---|---|---|---|
| `ur_base_xarco_model` | UR10 仿真、MoveIt2 规划、参数化轨迹后端、RViz 参数面板 | xacro/urdf/srdf、MoveIt 配置、控制器配置、实验参数 YAML | Gazebo/MoveIt 节点、规划与执行服务、可视化面板 | 是（含多个 package） |
| `experiment_data_recorder` | 实验数据采集与记录 GUI，组织原始实验数据与分析脚本 | UR/FT 运行数据、相机数据、实验参数 | CSV/日志、分析结果、数据管理 GUI | 否（Python 应用为主） |
| `ur10_ft300_monitor` | FT300 力传感采集、监控、分析 GUI 与相关脚本 | FT300 串口数据、机器人状态 | 力数据流、监控图表、分析输出 | 部分是（含 ROS2 节点与 Python 脚本） |
| `intel_realsense` | RealSense 学习资料、工作区与 `realsense-ros` 封装 | RealSense 设备与驱动依赖 | 相机图像/深度/点云话题、标定与测试结果 | 是（`realsense_ros2_ws` 内） |

---

## 3. 核心依赖关系（重点）

1. `experiment_data_recorder -> ur10_ft300_monitor/scripts`  
当前为硬依赖：`experiment_data_recorder/core/ur_ft_adapter.py` 直接导入 `ur10_ft300_monitor/scripts` 下模块。

2. `experiment_data_recorder -> intel_realsense/work_place + realsense_ros2_ws`  
实验记录流程会用到 RealSense 设备、学习脚本和 ROS2 wrapper 运行环境。

3. `experiment_data_recorder/analysis -> ur_base_xarco_model`  
数据分析和坐标链解释依赖 UR10 模型结构（xacro/urdf）与 TF 语义一致性。

4. `ur_base_xarco_model` 为独立仿真/规划链路  
可在不启动记录 GUI 的情况下独立完成 Gazebo + MoveIt2 + ros2_control 的参数化规划和执行。

---

## 4. 各子系统启动入口

### 4.1 参数化仿真链（主入口）

从工作区根目录执行：

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch assembly_description assembly_bringup.launch.py mode:=parametric_gui gazebo_gui:=false launch_rviz:=true
```

### 4.2 实验记录 GUI

```bash
cd /root/ur10_ws/src/experiment_data_recorder
python3 run_gui.py
```

### 4.3 FT300 采集与分析 GUI

采集/监控：

```bash
cd /root/ur10_ws/src/ur10_ft300_monitor
python3 run_gui.py
```

分析：

```bash
cd /root/ur10_ws/src/ur10_ft300_monitor/analysis
python3 run_analysis_gui.py
```

### 4.4 RealSense 学习与 ROS2 wrapper

学习脚本：

```bash
cd /root/ur10_ws/src/intel_realsense/realsense_learning
```

ROS2 wrapper（`realsense-ros`）：

```bash
cd /root/ur10_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch realsense2_camera rs_launch.py
```

---

## 5. 标准工作流（建议顺序）

1. 数据采集  
通过 `ur10_ft300_monitor` + `experiment_data_recorder` 完成力/位姿/实验元数据采集与归档。

2. 数据分析  
在 `experiment_data_recorder` 与 `ur10_ft300_monitor/analysis` 中完成清洗、统计、可视化和参数提取。

3. 参数化复现与仿真验证  
将分析得到的参数写入 `ur_base_xarco_model` 的配置，通过 `mode:=parametric_gui` 进行规划、预览和执行验证。

---

## 6. 构建与环境建议

### 6.1 推荐构建范围（仅当前四条主线）

从 `/root/ur10_ws` 执行：

```bash
colcon build --symlink-install --base-paths \
  src/ur_base_xarco_model \
  src/ur10_ft300_monitor \
  src/experiment_data_recorder \
  src/intel_realsense/realsense_ros2_ws/src/realsense-ros
```

### 6.2 `source` 顺序建议

```bash
source /opt/ros/humble/setup.bash
source /root/ur10_ws/install/setup.bash
```

### 6.3 Python venv 约定

- 需要 GUI/数据分析依赖时，优先在各目录使用项目级 venv。
- 进入 venv 后再执行 GUI 脚本，避免系统 Python 与 pip 包冲突。

---

## 7. 边界与禁区

1. 不再依赖 `ur10_*` 旧链路作为运行主路径。  
2. 不在 `src` 根目录放置构建产物（`build/ install/ log/`）与临时旧文档。  
3. 新功能优先落在上述四条主线中，避免再创建平行“第二套流程”。

---

## 8. 常见故障排查

1. RealSense 设备不可见  
- 先用 `lsusb` 检查设备识别，再确认 `realsense2_camera` 节点是否正常启动。

2. FT300 串口打不开  
- 检查串口号、权限（`dialout` 组）和设备占用，确认监控 GUI 配置一致。

3. UR 通讯异常  
- 检查机器人 IP、网络连通性、驱动节点日志，确认控制模式与当前任务匹配。

4. MoveIt 控制器未激活  
- 使用 `ros2 control list_controllers` 确认 `joint_state_broadcaster` 与 `joint_trajectory_controller` 为 `active`。

5. 规划有轨迹但不执行  
- 检查 FollowJointTrajectory action 是否存在：`ros2 action list | grep follow_joint_trajectory`，并确认执行链路没有被其他节点占用。

