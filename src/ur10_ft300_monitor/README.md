# UR10 + FT300 一体化监控工具包

该工具包用于在同一 GUI 页面同时采集与记录：
- UR10 实时运动数据（`30003` socket）
- FT300 六维力数据（串口 Modbus）

并统一保存到同一份 CSV，主时间字段为 Unix Epoch 秒（`epoch_time`）。

## 目录结构
```text
ur10_ft300_monitor/
├── README.md
├── requirements.txt
├── run_gui.py
├── data/
├── scripts/
│   ├── ur_reader.py
│   ├── ft300_reader.py
│   └── fusion_logger_gui.py
└── docs/
    └── usage.md
```

## 安装依赖
```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
pip install -r requirements.txt
```

## 启动
```bash
python3 run_gui.py
```

## 默认参数
- UR: `10.160.9.21:30003`, timeout `3s`
- FT300: `/dev/ttyUSB0`, `19200`, `slave_id=9`, timeout `0.2s`

## 数据保存
每次点击开始采集会创建：
```text
data/YYYYMMDD_HHMMSS/ur10_ft300_realtime_data.csv
data/YYYYMMDD_HHMMSS/metadata.txt
```

CSV 关键列：
- `epoch_time`（Unix Epoch 秒，float）
- UR 全量字段（q/qd/I/TCP/Tgt_q/状态电气量）
- `Fx,Fy,Fz,Mx,My,Mz`
- `Label`
- `ur_fresh,ft_fresh`

## 连接检查
```bash
ping 10.160.9.21
nc -vz 10.160.9.21 30003
ls /dev/ttyUSB*
```

若没有 `nc`：
```bash
sudo apt install -y netcat-openbsd
```

## 安全说明
- 本工具仅读取数据，不发送任何机械臂运动命令。
- 禁止在本工具中加入 `movej`、`movel`、`servoj` 等控制接口。
- 实验前确认急停可用并保持机器人周围安全空间。
