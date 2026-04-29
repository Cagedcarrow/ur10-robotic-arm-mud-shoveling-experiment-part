# 本次任务总结

## 1. 任务目标
在你的 WSL2 + ROS2 环境中，针对 FT300 无数据问题做实测排查，判断是否为协议/参数不匹配，并输出结论文档。

## 2. 已执行检查与结果

### 2.1 串口设备与权限
- `/dev/ttyUSB0` 存在，权限为 `crw-rw---- root:dialout`
- 当前用户为 `root`，不存在权限不足问题
- `stty` 显示串口当前为 `19200`, `8N1`（`cs8`, `-parenb`, `-cstopb`）

结论：端口可用，权限不是当前阻塞点。

### 2.2 被动监听测试（不发命令）
执行：
```bash
python3 FT300/tools/test_ft300_connection.py --port /dev/ttyUSB0 --baudrate 19200 --duration 5 --debug-hex
```
结果：
- 串口可成功打开
- 5 秒内接收字节数为 `0`
- 无任何原始字节/十六进制输出

结论：传感器未被动上报，或链路层未形成有效通信。

### 2.3 主动 Modbus 启动命令测试（与节点一致）
发送命令（slave=9，FC16，写 `0x019A <- 0x0200`）：
- `09 10 01 9a 00 01 02 02 00 cd ca`

在 `9600/19200/38400/57600/115200` 五个波特率下测试结果一致：
- 写入成功（11 字节）
- 即时回包 `0` 字节
- 后续 2 秒接收总字节数 `0`

结论：不仅无流数据，连 FC16 回显也没有，问题不只是 GUI 逻辑。

### 2.4 内核日志与 USBIP 稳定性
`dmesg` 关键事实：
- 已识别 FTDI 并挂载到 `ttyUSB0`：
  - `FTDI USB Serial Device converter detected`
  - `... now attached to ttyUSB0`
- 同时持续出现大量：
  - `vhci_hcd: urb->status -104`
  - 频繁 `unlink->seqnum ...`

结论：WSL2 USBIP 虚拟主机链路存在明显不稳定/中断迹象，这会直接导致串口收发异常或丢失。

## 3. 根因判断（按概率排序）

1. **USBIP 链路不稳定（高概率）**
- 证据：`dmesg` 大量 `vhci_hcd urb->status -104`。
- 影响：即便设备枚举成功，也可能读不到任何稳定数据帧或应答。

2. **物理电气层不匹配（高概率）**
- 你当前识别为 FTDI UART 桥（`0403:6015`），但 FT300 通常走 Modbus/RS485 链路。
- 若当前仅 TTL/UART 级别而非正确 RS485 收发链路（含方向控制/接线正确性），会表现为“能发但永不回”。

3. **从站地址或协议状态不一致（中概率）**
- 代码默认 `slave_id=9`，与 Robotiq 示例一致，但若设备被改地址、未进对应模式，亦会无应答。

4. **波特率不匹配（中低概率）**
- 已尝试 5 种常见波特率均 0 字节，单纯波特率错误概率下降，但不能完全排除特殊配置。

## 4. 本次结论
- 当前问题**不是**你 ROS2 节点是否能打开串口的问题（它可以）。
- 当前问题也**不太像**单纯 GUI 代码 bug（主动/被动独立测试均 0 字节）。
- 关键阻塞在“设备通信链路层”：优先怀疑 **WSL2 USBIP 稳定性 + RS485/接线/适配器链路**。

## 5. 建议的下一步验证（按顺序）

1. **先稳定 USBIP**
- 在 Windows 侧重新 `usbipd detach/attach` 设备。
- 重新挂载后立即在 WSL2 执行：
  ```bash
  dmesg | tail -n 50
  ```
  确认不再持续出现 `urb->status -104`。

2. **验证适配器与接线是否为 RS485 通道**
- 确认当前 FTDI 设备是否为 RS485 转换器（不是普通 TTL-UART）。
- 确认 A/B 线、GND、终端电阻、供电与传感器文档一致。

3. **做最小主动轮询验证（非 GUI）**
- 保持当前脚本被动监听默认不变。
- 如你同意，我下一步可加 `--send-start-command` / `--slave-id` 开关，专门做 A/B 协议探测并输出每包日志。

4. **必要时在非 WSL 环境交叉验证**
- 在原生 Linux 或 Windows 串口工具上直接验证是否可收到 Modbus 回包，排除 WSL2 虚拟 USB 栈影响。

## 6. 相关命令记录
```bash
ls -l /dev/ttyUSB0
id && groups
stty -F /dev/ttyUSB0 -a
fuser -v /dev/ttyUSB0
```

```bash
python3 FT300/tools/test_ft300_connection.py --port /dev/ttyUSB0 --baudrate 19200 --duration 5 --debug-hex
```

```bash
# 主动 FC16 命令 + 多波特率探测（临时脚本执行）
# 结论：9600/19200/38400/57600/115200 均 0 字节回包
```

```bash
dmesg | rg "ttyUSB0|FTDI|vhci_hcd|urb->status" 
```

## 7. 测试结论状态
- ROS2 包构建：通过
- 串口打开：通过
- 被动收数：失败（0 字节）
- 主动命令应答：失败（0 字节）
- 内核链路稳定性：异常（大量 `urb->status -104`）

## 8. 剩余问题
- 传感器当前是否通过正确 RS485 通道接入尚未被硬件层面确认。
- WSL2 USBIP 链路是否可稳定长时间收发尚未恢复。

## 9. 下一步建议
1. 先处理 USBIP 稳定性并复测。
2. 确认 FTDI 设备型号是否确实支持 RS485 且接线正确。
3. 若你要，我可以立即把测试脚本加上 `--send-start-command --slave-id` 主动轮询模式，专门做地址/命令诊断（不改 GUI 主节点）。
