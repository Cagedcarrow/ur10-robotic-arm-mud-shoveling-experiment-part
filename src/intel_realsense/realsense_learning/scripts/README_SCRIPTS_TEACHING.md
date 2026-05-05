# RealSense Python Scripts 教学说明

本目录脚本用于在 **WSL2 + D435** 环境下，从“看图像”逐步过渡到“取深度、算三维、服务机械臂”。

## 0. 运行前准备

- 关闭可能占用相机的程序：`realsense-viewer`、其他 Python 脚本、ROS2 相机节点。
- 推荐解释器（你当前环境）：

```bash
~/ur10_ws/.venv/bin/python
```

- 进入目录：

```bash
cd ~/ur10_ws/src/intel_realsense/realsense_learning/scripts
```

## 1. 脚本总览

| 脚本 | 目标 | 你要学会什么 |
| --- | --- | --- |
| `01_rgb_depth_view.py` | 同时显示 RGB 与深度伪彩色 | RealSense 基础流结构（color/depth） |
| `02_mouse_depth_measure.py` | 鼠标位置测距 | `depth_frame.get_distance(u, v)` 的意义 |
| `03_align_depth_to_color.py` | 深度对齐到彩色坐标系 | 为什么视觉检测前要做 `align` |
| `04_pixel_to_3d.py` | 像素反投影为 3D 点 | 内参 + 深度 -> 相机坐标系点 |
| `05_save_pointcloud_ply.py` | 保存彩色点云 PLY | 点云导出与离线可视化 |
| `06_depth_filters.py` | 原始/滤波深度对比 | 滤波对噪声、空洞、边缘的影响 |
| `07_record_depth_stats.py` | 记录深度统计 CSV | 量化深度稳定性（均值/中位数/极值） |

## 2. 推荐学习顺序（务必按顺序）

1. `01_rgb_depth_view.py`
2. `02_mouse_depth_measure.py`
3. `03_align_depth_to_color.py`
4. `04_pixel_to_3d.py`
5. `06_depth_filters.py`
6. `07_record_depth_stats.py`
7. `05_save_pointcloud_ply.py`

说明：先建立“深度值含义 + 坐标系理解”，最后再做点云更容易理解结果。

## 3. 每个脚本的教学要点

## 3.1 `01_rgb_depth_view.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 01_rgb_depth_view.py
```

观察重点：
- 左图 RGB、右图深度伪彩色同步变化。
- 近处通常颜色更“热”，远处更“冷”（由色图映射决定）。

退出：`q` 或 `ESC`。

## 3.2 `02_mouse_depth_measure.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 02_mouse_depth_measure.py
```

观察重点：
- 鼠标移动到不同物体，读数（米）是否符合真实距离。
- 玻璃、反光、黑色材质可能深度不稳定。

退出：`q` 或 `ESC`。

## 3.3 `03_align_depth_to_color.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 03_align_depth_to_color.py
```

观察重点：
- 中心点深度读数来自“对齐后”深度。
- 这一步是后续 YOLO/检测框取深度的前置条件。

退出：`q` 或 `ESC`。

## 3.4 `04_pixel_to_3d.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 04_pixel_to_3d.py
```

观察重点：
- 输出 `X,Y,Z (m)`，这是**相机坐标系**点，不是机械臂基座坐标。
- 鼠标左右移动，`X` 变化明显；上下移动，`Y` 变化明显；远近变化，`Z` 变化明显。

退出：`q` 或 `ESC`。

## 3.5 `05_save_pointcloud_ply.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 05_save_pointcloud_ply.py
```

操作：
- 按 `s` 保存点云到：
  - `~/ur10_ws/src/intel_realsense/realsense_learning/data/d435_pointcloud.ply`

可视化：

```bash
pcl_viewer ~/ur10_ws/src/intel_realsense/realsense_learning/data/d435_pointcloud.ply
```

退出：`q` 或 `ESC`。

## 3.6 `06_depth_filters.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 06_depth_filters.py
```

观察重点：
- 左侧原始深度，右侧滤波后深度。
- 看空洞是否减少、噪声是否平滑、边缘是否被过度抹平。

退出：`q` 或 `ESC`。

## 3.7 `07_record_depth_stats.py`

运行：

```bash
~/ur10_ws/.venv/bin/python 07_record_depth_stats.py
```

输出：
- CSV 文件：
  - `~/ur10_ws/src/intel_realsense/realsense_learning/data/d435_depth_stats.csv`

列含义：
- `mean_m`：均值
- `median_m`：中位数（通常比均值更抗噪）
- `min_m/max_m`：极值
- `valid_count`：有效深度像素数量

教学用途：
- 用于比较不同曝光、光照、角度下深度稳定性。

退出：`q` 或 `ESC`。

## 4. 与 UR10 机械臂任务的连接

你最终要用到的链路是：

```text
目标检测（RGB）
-> 目标像素点/框中心
-> 对齐深度取距离
-> 像素反投影得到相机系3D点
-> 手眼标定变换到UR10 base_link
-> 发送机械臂抓取/避障目标
```

这 7 个脚本就是上面链路的最小可运行分解。

## 5. 常见问题排查

## 5.1 `ModuleNotFoundError: pyrealsense2`

```bash
~/ur10_ws/.venv/bin/python -c "import pyrealsense2 as rs; print('OK')"
```

如果失败，再查：

```bash
find /usr/local -name "pyrealsense2*.so"
```

## 5.2 相机被占用（resource busy）

先关闭：
- `realsense-viewer`
- 其他 Python 采流脚本
- `realsense2_camera` ROS2 节点

## 5.3 WSLg/OpenCV 窗口问题

```bash
echo $DISPLAY
```

若窗口可开但有 Qt 字体警告，通常不影响采流。

## 5.4 保存点云后打不开

先确认文件存在：

```bash
ls -lh ~/ur10_ws/src/intel_realsense/realsense_learning/data/*.ply
```

再尝试 `pcl_viewer` 或用 Open3D 读取。

## 6. 一键教学演示建议

上课/汇报时建议演示顺序：
1. `01` 展示 RGB+Depth 同步
2. `02` 实时鼠标测距
3. `03` 解释对齐
4. `04` 展示 2D->3D
5. `07` 展示可量化数据记录
6. 最后 `05` 导出点云

这样从感性到定量，最容易让同学/老师理解价值。
