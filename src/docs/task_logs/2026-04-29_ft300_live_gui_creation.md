# 本次任务总结

## 1. 任务目标

编写一个可直接连接 FT300 串口的 GUI 页面，实时显示 `Fx/Fy/Fz/Mx/My/Mz` 数据，并尽量不依赖 ROS2 话题链路。

## 2. 根因分析

- 当前 FT300 已经验证可以通过 `/dev/ttyUSB0`、`19200`、slave id `9` 读到真实数据。
- 现有仓库里虽然已有 `FT300/ft300_gui_ros2`，但它绑定了 ROS2 节点场景。
- 对于“先把真实数据显示出来”这个目标，更直接稳定的交付方式是提供一个独立串口 GUI 脚本，绕开 ROS2 运行链。

## 3. 修改文件清单

- `robotiq_ft300_sensor-master/tools/ft300_live_gui.py`

## 4. 新增功能

- 新增独立 FT300 GUI 程序：
  - 直接连接 `/dev/ttyUSB0`
  - 发送官方 stream 启动命令
  - 实时显示六维力/力矩数值
  - 显示滚动曲线
  - 显示连接状态、样本数、错误信息
  - 支持命令行参数：`--port` `--baudrate` `--timeout` `--slave-id` `--window-sec`

## 5. 核心实现逻辑

- 内置 FT300 帧解析逻辑：
  - 帧头 `0x20 0x4E`
  - 16 字节固定帧
  - CRC16 校验
  - 力分量按 `/100` 转换，力矩分量按 `/1000` 转换
- 启动时发送官方 `fc16` stream 启动命令。
- 后台线程持续读串口、主线程用 Tkinter + Matplotlib 刷新界面。
- 滚动窗口默认 30 秒，避免曲线无限增长。

## 6. 执行命令

```bash
python3 -m py_compile ~/ur10_ws/src/robotiq_ft300_sensor-master/tools/ft300_live_gui.py

python3 ~/ur10_ws/src/robotiq_ft300_sensor-master/tools/ft300_live_gui.py \
  --port /dev/ttyUSB0 \
  --baudrate 19200 \
  --slave-id 9
```

## 7. 测试结果

- 脚本语法检查通过。
- `--help` 参数解析通过。
- 由于当前会话为终端无桌面验证环境，未实际弹出 GUI 窗口做交互测试。
- 串口协议路径已在前序任务中验证可读真实数据，因此该 GUI 的数据源路径成立。

## 8. 剩余问题

- 若系统没有图形界面转发，Tkinter 窗口无法显示。
- 运行 GUI 时必须保证没有其他程序同时占用 `/dev/ttyUSB0`。
- 若你同时开着 raw test 或 `driverSensor`，GUI 会因为串口抢占失败或读到空数据而异常。

## 9. 下一步建议

1. 先关闭其他 FT300 串口程序，再单独启动 GUI。
2. 如果你希望，我下一步可以把这个独立 GUI 再加上“归零按钮”和“CSV 保存按钮”。
3. 如果你更想统一到 ROS2，我可以把这个独立 GUI 的稳定串口逻辑回填到 `FT300/ft300_gui_ros2`。
