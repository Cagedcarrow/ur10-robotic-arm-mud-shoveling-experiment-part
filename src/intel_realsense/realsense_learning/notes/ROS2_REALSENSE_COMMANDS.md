# ROS2 RealSense D435 Commands

## 1. Source 环境

```bash
source /opt/ros/humble/setup.bash
source ~/ur10_ws/src/intel_realsense/realsense_ros2_ws/install/setup.bash
```

## 2. 启动 D435 ROS2 节点

优先使用新参数风格：

```bash
ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=640x480x30 \
  rgb_camera.profile:=640x480x30 \
  enable_color:=true \
  enable_depth:=true \
  pointcloud.enable:=true \
  align_depth.enable:=true
```

说明：

- `depth_module.profile:=640x480x30`：深度流 640x480，30 FPS
- `rgb_camera.profile:=640x480x30`：彩色流 640x480，30 FPS
- `pointcloud.enable:=true`：发布 PointCloud2 点云
- `align_depth.enable:=true`：发布对齐到彩色图的深度图

## 3. 查看话题

```bash
ros2 topic list | grep camera
```

重点话题：

```text
/camera/camera/color/image_raw
/camera/camera/depth/image_rect_raw
/camera/camera/aligned_depth_to_color/image_raw
/camera/camera/depth/color/points
/camera/camera/color/camera_info
/camera/camera/depth/camera_info
```

## 4. 查看图像

彩色图：

```bash
ros2 run image_view image_view \
  --ros-args \
  -r image:=/camera/camera/color/image_raw
```

深度图：

```bash
ros2 run image_view image_view \
  --ros-args \
  -r image:=/camera/camera/depth/image_rect_raw
```

对齐后的深度图：

```bash
ros2 run image_view image_view \
  --ros-args \
  -r image:=/camera/camera/aligned_depth_to_color/image_raw
```

## 5. RViz2 查看点云

```bash
rviz2
```

RViz2 设置：

- Fixed Frame 可先尝试：
  - `camera_link`
  - `camera_color_optical_frame`
  - `camera_depth_optical_frame`
- 添加 `PointCloud2`
- Topic 选择：
  - `/camera/camera/depth/color/points`

## 6. 常见问题

### 问题 1：没有点云话题

检查启动参数是否包含：

```bash
pointcloud.enable:=true
```

### 问题 2：没有 aligned depth 话题

检查启动参数是否包含：

```bash
align_depth.enable:=true
```

### 问题 3：设备被占用

关闭：

- realsense-viewer
- 正在运行的 Python 脚本
- 其他 ROS2 相机节点

然后重新启动。
