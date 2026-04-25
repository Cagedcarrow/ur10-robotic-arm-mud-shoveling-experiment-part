# ft300_gui_ros2

FT300 一体化 ROS 2 GUI 程序（USB测试 + 节点测试 + 实时显示 + 数据保存）。

## 功能

- USB连接测试：打开串口并验证收到有效 FT300 数据帧。
- 实时采集：读取 FT300 数据并发布 `/ft300/wrench`（`geometry_msgs/msg/WrenchStamped`）。
- 实时显示：GUI 显示六轴当前值 + 滚动曲线。
- 会话保存：点击“停止采集并保存”后生成：
  - `wrench_data.csv`
  - `wrench_plot.png`
  - `session_meta.json`

保存目录默认：`~/ft300_sessions/session_YYYYMMDD_HHMMSS`（Asia/Shanghai 本地时间）。

## 依赖

```bash
sudo apt update
sudo apt install -y python3-serial python3-matplotlib python3-numpy
```

## 编译

```bash
cd /root/ur10_ws
colcon build --packages-select ft300_gui_ros2
source install/setup.bash
```

## 启动

```bash
ros2 launch ft300_gui_ros2 ft300_gui.launch.py
```

## 默认参数

- `port`: `/dev/ttyUSB0`
- `baudrate`: `19200`
- `timeout`: `0.1`
- `frame_id`: `ft300_sensor_link`
- `publish_rate`: `100.0`
- `validate_crc`: `true`
- `save_root_dir`: `~/ft300_sessions`
- `plot_window_sec`: `30`
- `slave_id`: `9`

## 使用流程

1. 点击“USB测试连接”。
2. 成功后点击“开始采集”。
3. 观察实时数值与曲线，并可用 `ros2 topic echo /ft300/wrench` 验证话题。
4. 点击“停止采集并保存”，查看会话目录。
