# 使用说明

1. 启动虚拟环境（如使用）：
```bash
source ~/.venv/bin/activate
```

2. 安装依赖：
```bash
cd ~/ur10_ws/src/ur10_realtime_monitor
pip install -r requirements.txt
```

3. 检查网络：
```bash
ping 10.160.9.21
nc -vz 10.160.9.21 30003
```

4. 运行连接测试：
```bash
python scripts/test_ur_connection.py --ip 10.160.9.21 --port 30003
```

5. 启动 GUI：
```bash
./run_gui.sh
```

6. 点击“开始监控”。

7. 点击“实验标记”或按 `Space` 切换 `Label`。

8. 点击“停止监控”结束采集。

9. 查看 `data/时间戳目录/` 下的 `ur10_realtime_data.csv` 与 `metadata.txt`。
