# 本次任务总结

## 1. 任务目标

在 `experiment_data_recorder/run_gui.py` 启动的总控 GUI 中新增“力传感器清零”按钮，实现运行中 FT300 软件清零。

## 2. 根因分析

现有 GUI 仅有“开始记录/停止记录”，无 FT300 清零入口；且采集链路直接记录 FT300 原始值，不能在实验前快速归零。

## 3. 修改文件清单

- `ui/main_window.py`
- `core/ur_ft_adapter.py`
- `docs/task_logs/2026-05-06_ft300_tare_button.md`（本日志）

## 4. 新增功能

- GUI 新增按钮：`力传感器清零`
- 仅在采集启动后可点击，避免空会话误操作。
- 若尚未收到 FT300 数据，会弹窗提示稍后重试。
- 清零成功后写入状态栏日志与运行日志。

## 5. 核心实现逻辑

- 在 `URFTAdapter` 增加：
  - `latest_ft_raw`：保存最新原始 FT300 六轴
  - `ft_zero_offset`：保存六轴清零偏置
  - `tare_ft_sensor()`：将当前 `latest_ft_raw` 设为偏置
- 在 `on_ft_data()` 中：
  - 先保存原始值
  - 再执行 `corrected = raw - offset`
  - GUI曲线与CSV写入使用 `corrected` 值
- 在 `MainWindow` 中新增按钮并绑定 `_tare_ft_sensor()` 调用 adapter 接口。

## 6. 执行命令

```bash
cd /root/ur10_ws/src/experiment_data_recorder
python3 -m py_compile run_gui.py ui/main_window.py core/ur_ft_adapter.py core/session_manager.py
```

## 7. 测试结果

- Python 语法编译检查：通过。
- GUI交互逻辑静态检查：通过（按钮状态、空数据提示、成功路径均已接通）。

## 8. 剩余问题

- 当前为“软件清零”（采集侧减偏置），不是 FT300 硬件寄存器级清零。
- 偏置尚未写入 `session_metadata.txt`；如需审计可追加记录。

## 9. 下一步建议

1. 增加“启动后自动清零（延迟N帧取均值）”选项。
2. 将 `ft_zero_offset` 写入 `session_metadata.txt` 便于追溯。
3. 在按钮旁显示当前偏置简报（Fx/Fy/Fz/Mx/My/Mz）。
