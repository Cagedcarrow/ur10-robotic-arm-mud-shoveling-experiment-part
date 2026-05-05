# Intel RealSense D435 Learning Workspace

## 1. 当前环境

- WSL2 Ubuntu 22.04
- ROS2 Humble
- Intel RealSense D435
- librealsense 源码安装
- RSUSB 后端
- realsense-viewer 已可显示画面

## 2. 已安装扩展依赖

- Python/OpenCV/NumPy
- matplotlib
- open3d
- pandas
- pcl-tools
- ROS2 cv_bridge/image_transport/image_view/rviz2
- realsense-ros 源码工作空间

## 3. Python 示例列表

| 脚本 | 功能 | 学习重点 |
| --- | --- | --- |
| 01_rgb_depth_view.py | RGB + Depth 显示 | 基础数据流 |
| 02_mouse_depth_measure.py | 鼠标测距 | get_distance |
| 03_align_depth_to_color.py | 深度对齐到彩色 | YOLO 取深度前置步骤 |
| 04_pixel_to_3d.py | 像素反投影三维坐标 | 相机内参与相机坐标系 |
| 05_save_pointcloud_ply.py | 保存点云 PLY | 点云生成 |
| 06_depth_filters.py | 深度滤波对比 | 空洞、噪声、平滑 |
| 07_record_depth_stats.py | 记录深度统计 CSV | 实验数据记录 |

## 4. 推荐学习顺序

1. RealSense Viewer 参数实验
2. 运行 01_rgb_depth_view.py
3. 运行 02_mouse_depth_measure.py
4. 运行 03_align_depth_to_color.py
5. 运行 04_pixel_to_3d.py
6. 运行 05_save_pointcloud_ply.py
7. 运行 06_depth_filters.py
8. 运行 07_record_depth_stats.py
9. 启动 ROS2 wrapper
10. 在 RViz2 中查看点云

## 5. 和 UR10 项目的关系

对于后续 UR10 机械臂视觉定位，关键链路是：

```text
RGB 图像检测目标
→ 得到目标像素点或目标框中心点
→ 查询对齐后的深度
→ 利用相机内参反投影为相机坐标系 3D 点
→ 通过手眼标定转换到 UR10 base_link 坐标系
→ 生成机械臂目标点或避障信息
```

## 6. 运行命令总表

```bash
cd ~/ur10_ws/src/intel_realsense/realsense_learning/scripts

python3 01_rgb_depth_view.py
python3 02_mouse_depth_measure.py
python3 03_align_depth_to_color.py
python3 04_pixel_to_3d.py
python3 05_save_pointcloud_ply.py
python3 06_depth_filters.py
python3 07_record_depth_stats.py
```

ROS2：

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

## 7. 常见错误

### pyrealsense2 找不到

检查：

```bash
python3 -c "import pyrealsense2 as rs; print('OK')"
find /usr/local -name "pyrealsense2*.so"
```

### 相机被占用

关闭：

- realsense-viewer
- Python 示例
- ROS2 相机节点

### OpenCV 窗口打不开

检查 WSLg / DISPLAY：

```bash
echo $DISPLAY
```

### 点云打不开

先确认生成文件：

```bash
ls -lh ~/ur10_ws/src/intel_realsense/realsense_learning/data/*.ply
```

然后尝试：

```bash
pcl_viewer ~/ur10_ws/src/intel_realsense/realsense_learning/data/d435_pointcloud.ply
```

## 8. 说明

- 当前阶段不处理 usbipd 设备挂载（D435 已在 WSL2 内可识别）。
- 本次使用解释器：`~/ur10_ws/.venv/bin/python`。
- 若需在该 `.venv` 中运行示例：`~/ur10_ws/.venv/bin/python <script.py>`。
