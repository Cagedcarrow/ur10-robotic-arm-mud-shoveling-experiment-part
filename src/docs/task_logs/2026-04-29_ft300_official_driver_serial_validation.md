# 本次任务总结

## 1. 任务目标

在 `~/ur10_ws/src/robotiq_ft300_sensor-master` 范围内优先编译和测试官方 FT300 底层驱动，验证 FT300 力传感器是否能通过 `/dev/ttyUSB0` 输出真实 `Fx Fy Fz Mx My Mz` 数据。

## 2. 根因分析

- 官方 Linux 驱动默认波特率为 `19200`，Modbus slave id 硬编码为 `9`。
- 官方驱动原始实现会遍历 `/sys/class/tty` 中的 `ttyS*` 和 `ttyUSB*`，在 WSL2 环境下会反复扫到多个 `ttyS*`，端口选择不稳定。
- 已做最小补丁让驱动优先尝试 `/dev/ttyUSB0`，并支持环境变量 `FT300_PORT` 指定端口。
- 即使固定 `/dev/ttyUSB0`，官方程序仍未打印任何力/力矩数据。
- 使用最小 raw 串口探测脚本在 `/dev/ttyUSB0` 上主动发送官方默认参数下的 Modbus `fc03` 读固件请求，也没有收到任何返回字节。
- 被动监听同样没有收到 stream 数据。
- 进一步做波特率快速扫查 `19200/9600/38400/57600/115200`，全部无响应。
- 当前最可能根因已经收敛到硬件/物理链路或设备配置层：
  - RS485 A/B 线接反
  - 转换器方向控制或接线不匹配
  - FT300 实际 slave id 不是 `9`
  - FT300 当前接口/模式不是该官方串口协议路径
  - 供电虽存在，但通信参考地或接线链路不完整

## 3. 修改文件清单

- `robotiq_ft300_sensor-master/robotiq_ft_sensor_dev_v1.0.1/driver/src/rq_sensor_com.c`
- `robotiq_ft300_sensor-master/tools/ft300_raw_test.py`

## 4. 新增功能

- 新增 `tools/ft300_raw_test.py`
  - 默认端口 `/dev/ttyUSB0`
  - 默认波特率 `19200`
  - 支持 `--port` `--baudrate` `--duration`
  - 发送一次官方默认 Modbus 读请求
  - 打印 raw bytes 和 hex
  - 若无响应，明确打印 `<no response>` / `<timeout>`
- 官方驱动增加端口优先逻辑
  - 优先尝试 `/dev/ttyUSB0`
  - 支持通过 `FT300_PORT` 覆盖端口
  - 再回退扫描其他 `ttyUSB*`，最后才扫 `ttyS*`

## 5. 核心实现逻辑

- 保留官方协议实现不变，只最小修改 Linux 串口选择逻辑，避免 WSL2 下被 `ttyS*` 噪声串口拖住。
- Raw 测试脚本按官方源码的默认假设发送：
  - slave id = `9`
  - function code = `0x03`
  - register = `500`
  - 目标是读固件寄存器并确认设备是否至少有 Modbus 级响应。
- 若连固件读都无返回，则不能声称已经读到 FT300 真数据。

## 6. 执行命令

```bash
cd ~/ur10_ws/src/robotiq_ft300_sensor-master/robotiq_ft_sensor_dev_v1.0.1/driver
make clean
make linux
find . -type f -executable

ls -l /dev/ttyUSB0
fuser /dev/ttyUSB0
stty -F /dev/ttyUSB0 -a

FT300_PORT=/dev/ttyUSB0 timeout 6s ./Linux/bin/driverSensor

python3 ~/ur10_ws/src/robotiq_ft300_sensor-master/tools/ft300_raw_test.py --port /dev/ttyUSB0 --baudrate 19200 --duration 3

for b in 19200 9600 38400 57600 115200; do
  python3 ~/ur10_ws/src/robotiq_ft300_sensor-master/tools/ft300_raw_test.py --port /dev/ttyUSB0 --baudrate $b --duration 1.2
done
```

## 7. 测试结果

- `make linux` 通过。
- 可执行文件已生成：`Linux/bin/driverSensor`
- `/dev/ttyUSB0` 存在，权限正常，可被 Python 打开。
- 官方驱动在固定 `FT300_PORT=/dev/ttyUSB0` 情况下 6 秒内无数据输出，超时退出。
- Raw 脚本发送 Modbus 请求后无任何返回。
- 被动监听无任何 stream 字节。
- 多波特率扫查仍无响应。
- 结论：本次**未能读到真实 FT300 数据**。

## 8. 剩余问题

- 未确认 A/B 线序是否正确。
- 未确认转换器是否需要额外 DE/RE 自动收发支持。
- 未确认 FT300 当前 slave id 是否为 `9`。
- 未确认 FT300 当前是否处于该官方驱动所期望的串口 Modbus/stream 模式。

## 9. 下一步建议

1. 先交换 RS485 A/B 线再复测 `tools/ft300_raw_test.py`。
2. 确认 FT300 官方接线图，补查 GND 参考线是否正确连接。
3. 若有 Windows 官方调试工具，先在原生 Windows 下验证该 USB-RS485 和传感器链路是否能读到数据。
4. 若确认接线无误，下一步可扩展脚本做 slave id 扫描（例如 `1-16`）和有限寄存器探测。
