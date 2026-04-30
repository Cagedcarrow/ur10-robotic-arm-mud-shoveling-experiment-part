# 使用说明

1. 进入目录并安装依赖：
```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
pip install -r requirements.txt
```

2. 检查 UR 网络：
```bash
ping 10.160.9.21
nc -vz 10.160.9.21 30003
```

3. 检查 FT300 串口：
```bash
ls /dev/ttyUSB*
```

4. 启动 GUI：
```bash
python3 run_gui.py
```

5. 在顶部输入 UR 与 FT300 参数，点击“开始采集”。

6. 按“实验标记”或 `Space` 切换 `Label`。

7. 点击“停止采集”后，在 `data/时间戳目录/` 查看：
- `ur10_ft300_realtime_data.csv`
- `metadata.txt`
