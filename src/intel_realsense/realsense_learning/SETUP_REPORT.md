# RealSense D435 Advanced Learning Setup Report

## 1. Environment

- Ubuntu version: Ubuntu 22.04.5 LTS (jammy)
- Kernel version: Linux 6.6.87.2-microsoft-standard-WSL2
- ROS2 version: Humble
- Current user: root

## 2. Existing SDK Status

- `rs-enumerate-devices`：可用
- `realsense-viewer`：可用
- `pyrealsense2`：可用（无 `__version__` 属性属正常差异）
- D435 识别状态：已识别（Serial `250122070158`）

## 3. Installed Dependencies

系统依赖（关键）：
- python3-pip/python3-dev/python3-venv/python3-numpy/python3-opencv
- v4l-utils, ffmpeg, imagemagick, pcl-tools
- ros-humble-cv-bridge
- ros-humble-image-transport / image-transport-plugins / image-view
- ros-humble-rviz2
- ros-humble-diagnostic-updater
- ros-humble-xacro
- ros-humble-rclcpp-components
- ros-humble-compressed-image-transport

Python 包（`~/ur10_ws/.venv`）：
- matplotlib
- open3d
- pandas
- numpy
- cv2
- pyrealsense2

## 4. Python Examples Created

1. `01_rgb_depth_view.py`：RGB + Depth 显示
2. `02_mouse_depth_measure.py`：鼠标测距
3. `03_align_depth_to_color.py`：深度对齐到彩色
4. `04_pixel_to_3d.py`：像素反投影到 3D
5. `05_save_pointcloud_ply.py`：保存点云 PLY
6. `06_depth_filters.py`：深度滤波对比（已修复分辨率不一致拼接问题）
7. `07_record_depth_stats.py`：记录深度统计 CSV

## 5. ROS2 Wrapper Build

- 仓库 URL: `https://github.com/realsenseai/realsense-ros.git`
- 分支: `ros2-master`
- Commit: `6d87b071`
- `colcon build`: 成功
- `ros2 pkg list | grep realsense`: 可见
  - realsense2_camera
  - realsense2_camera_msgs
  - realsense2_description
  - realsense2_ros_mqtt_bridge
  - realsense2_rviz_plugin

## 6. How to Run

Python 示例：

```bash
cd ~/ur10_ws/src/intel_realsense/realsense_learning/scripts
~/ur10_ws/.venv/bin/python 01_rgb_depth_view.py
~/ur10_ws/.venv/bin/python 02_mouse_depth_measure.py
~/ur10_ws/.venv/bin/python 03_align_depth_to_color.py
~/ur10_ws/.venv/bin/python 04_pixel_to_3d.py
~/ur10_ws/.venv/bin/python 05_save_pointcloud_ply.py
~/ur10_ws/.venv/bin/python 06_depth_filters.py
~/ur10_ws/.venv/bin/python 07_record_depth_stats.py
```

ROS2 启动：

```bash
source /opt/ros/humble/setup.bash
source ~/ur10_ws/src/intel_realsense/realsense_ros2_ws/install/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=640x480x30 \
  rgb_camera.profile:=640x480x30 \
  enable_color:=true \
  enable_depth:=true \
  pointcloud.enable:=true \
  align_depth.enable:=true
```

## 7. Known Issues

- 运行脚本时出现 OpenCV Qt 字体告警：
  `QFontDatabase: Cannot find font directory ... cv2/qt/fonts`。
  该告警不阻塞脚本采流，但会影响字体渲染。
- 自动 `rosdep install` 拉入了 `ros-humble-librealsense2`（与“尽量避免 apt RealSense 库”原则冲突）。
  当前检查显示 `/usr/local/lib/librealsense2.so*` 仍存在且未被覆盖，但建议后续按需要评估是否移除该包并在隔离环境重建。
- 超时验证中未手动按键触发 `05` 的 `s` 保存动作，PLY 需手工运行后按 `s` 生成。
