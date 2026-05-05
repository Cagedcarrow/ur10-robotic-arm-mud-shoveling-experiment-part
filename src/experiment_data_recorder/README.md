# experiment_data_recorder

统一实验数据记录 GUI：同步记录 RealSense 四路视频与 UR10+FT300 融合表格。

## 启动

```bash
python3 experiment_data_recorder/run_gui.py
```

## 输出目录

每次会话写入：

- `experiment_data_recorder/data/YYYY-MM-DD_HH-MM-SS/`
- `rgb.mp4`
- `depth.mp4`
- `ir1.mp4`
- `ir2.mp4`
- `ur10_ft300_realtime_data.csv`
- `camera_intrinsics.json`
- `camera_config.json`
- `meta.csv`（来自 RealSense，作为 `camera_meta.csv` 的语义文件）
- `session_metadata.txt`

## 依赖

- `PyQt5`
- `pyqtgraph`
- `opencv-python`
- `Pillow`
- `numpy`
- `pyserial`
- `pyrealsense2`

## 常见故障

- 无 RealSense 设备：启动后状态区会报设备连接错误。
- FT 串口不存在：会显示 FT300 连接失败，但 GUI 不会崩溃。
- UR IP 不通：会显示 UR 连接失败，可修改参数后重试。
