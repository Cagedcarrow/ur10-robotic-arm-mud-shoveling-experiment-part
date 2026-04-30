# 本次任务总结

## 1. 任务目标

新建独立纯 Python 功能包 `ur10_ft300_monitor`，在一个 GUI 页面同时采集 UR10 `30003` 运动数据与 FT300 串口六维力数据，并统一按绝对时间（Unix Epoch 秒）保存到同一 CSV。

## 2. 根因分析

- 现有 `ur10_realtime_monitor` 与 FT300 工具是分离的，无法在同一采集会话中融合记录。
- 实验分析需要 UR 与 FT300 的统一时间轴，避免后处理手工对齐。

## 3. 修改文件清单

- 新增 `src/ur10_ft300_monitor/requirements.txt`
- 新增 `src/ur10_ft300_monitor/run_gui.py`
- 新增 `src/ur10_ft300_monitor/README.md`
- 新增 `src/ur10_ft300_monitor/docs/usage.md`
- 新增 `src/ur10_ft300_monitor/scripts/ur_reader.py`
- 新增 `src/ur10_ft300_monitor/scripts/ft300_reader.py`
- 新增 `src/ur10_ft300_monitor/scripts/fusion_logger_gui.py`
- 新增 `src/docs/task_logs/2026-04-30_ur10_ft300_monitor_package.md`（本文件）

## 4. 新增功能

- 双线程采集：UR socket 与 FT300 serial 独立采集，主线程融合。
- 单页面多窗口多曲线显示：
  - UR关节角（6线）
  - UR关节速度（6线）
  - UR关节电流（6线）
  - FT300力（3线）
  - FT300力矩（3线）
  - TCP位姿（6线）
- CSV 融合行结构：`epoch_time + UR字段 + FT字段 + Label + ur_fresh + ft_fresh`。
- 每次启动自动创建 `data/YYYYMMDD_HHMMSS/`，保存 CSV 和 metadata。

## 5. 核心实现逻辑

- UR 读取：
  - 先读 4 字节长度头，再循环读取 body，按 UR `30003` 偏移大端解包。
- FT300 读取：
  - 串口发送 start-stream 帧，按 `0x20 0x4E` 帧头同步，CRC16 校验，缩放得到 `Fx..Mz`。
- 融合：
  - 任一源到新样本即写一行 CSV，`epoch_time=time.time()`。
  - 另一源无新数据时沿用最近值，`ur_fresh/ft_fresh` 标识新鲜度。
- 标记：
  - 按钮与 Space 切换 `Label`，写入同一 CSV。

## 6. 执行命令

```bash
mkdir -p /root/ur10_ws/src/ur10_ft300_monitor/{data,scripts,docs}
python3 -m pip install -r requirements.txt
python3 -m py_compile scripts/ur_reader.py scripts/ft300_reader.py scripts/fusion_logger_gui.py run_gui.py
ping -c 1 10.160.9.21
nc -vz 10.160.9.21 30003
ls /dev/ttyUSB*
find . -maxdepth 3 -type f | sort
```

## 7. 测试结果

- 依赖安装：通过。
- Python 语法检查：通过。
- UR 网络：
  - `ping` 失败（100% 丢包）。
  - `nc -vz 10.160.9.21 30003` 成功（端口可达）。
- FT300 串口：
  - 当前环境下无 `/dev/ttyUSB*` 设备，未完成实传感器链路验证。

## 8. 剩余问题

- 需要接入 FT300 对应 USB 串口设备后再做端到端采集验证。
- `ping` 与 `nc` 结果不一致，可能是 ICMP 被屏蔽；建议以 `nc` 和实际采样结果为准复测。

## 9. 下一步建议

- 接入 FT300 后执行 `python3 run_gui.py`，采集 1-2 分钟并检查 CSV 的 `ur_fresh/ft_fresh` 分布。
- 若后续做时序分析，建议追加 `sample_source` 列（ur/ft/both）提升可解释性。
