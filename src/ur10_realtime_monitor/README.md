# UR10 Realtime Monitor (WSL2)

一个用于 UR10/CB3 `30003` 实时端口的数据接收验证工具包（纯 Python）。  
本工具只读取状态数据、实时可视化并落盘 CSV/metadata，不发送任何运动控制命令。

## 功能说明
- TCP 连接 UR10 实时数据端口（默认 `10.160.9.21:30003`）。
- 解析关键字段：关节角、关节速度、关节电流、TCP 位姿、TCP 速度、目标关节角、状态电气量。
- PyQt5 + pyqtgraph 多页面多小窗实时曲线显示。
- `Label` 实验段标记（按钮或 `Space`）。
- 每次采集生成独立时间目录并保存：
  - `ur10_realtime_data.csv`
  - `metadata.txt`

## 目录结构
```text
ur10_realtime_monitor/
├── README.md
├── requirements.txt
├── run_gui.sh
├── data/
├── scripts/
│   ├── main_gui.py
│   ├── ur_full_monitor.py
│   └── test_ur_connection.py
└── docs/
    └── usage.md
```

## 安装依赖
```bash
cd ~/ur10_ws/src/ur10_realtime_monitor
pip install -r requirements.txt
```

如果 `PyQt5` pip 安装失败，可尝试：
```bash
sudo apt update
sudo apt install -y python3-pyqt5 python3-pyqtgraph
```

## 连接 UR10 前网络检查
```bash
ping 10.160.9.21
nc -vz 10.160.9.21 30003
```

如果没有 `nc`：
```bash
sudo apt install -y netcat-openbsd
```

## 连接测试
```bash
python scripts/test_ur_connection.py --ip 10.160.9.21 --port 30003
```

## 运行 GUI
```bash
./run_gui.sh
```

## CSV 保存位置
每次点击“开始监控”会创建：
```text
data/YYYYMMDD_HHMMSS/ur10_realtime_data.csv
data/YYYYMMDD_HHMMSS/metadata.txt
```

## WSL2 GUI 显示问题
如果 GUI 无法显示，请检查：
- 是否启用 WSLg（Windows 11 常见默认支持）
- `DISPLAY` 环境变量是否正确
- 若使用 X11 Server，确认 X Server 已启动且允许连接

## 安全注意事项
- 本工具只读取数据，不发送运动指令。
- 不要在本工具中加入 `movej`、`movel`、`servoj` 等控制命令。
- UR10 周围必须保持安全空间。
- 实验前确认急停可用。
- 若需要控制机械臂，应另建控制模块，不要与监控 GUI 混合。
