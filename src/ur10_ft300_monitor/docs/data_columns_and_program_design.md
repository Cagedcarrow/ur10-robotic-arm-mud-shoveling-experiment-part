# UR10 + FT300 监控程序数据列与实现说明

## 1. 数据保存位置

程序每次点击“开始采集”后，会创建一个时间目录：

```text
ur10_ft300_monitor/data/YYYYMMDD_HHMMSS/
```

目录内包含：

- `ur10_ft300_realtime_data.csv`：融合后的实时数据
- `metadata.txt`：本次采集参数与统计信息

---

## 2. CSV 列总览（`ur10_ft300_realtime_data.csv`）

CSV 列顺序由 `fusion_logger_gui.py` 中 `self.header` 固定定义为：

```text
epoch_time
+ UR字段(Time + Act_q* + Act_qd* + Act_I* + TCP + Tgt_q* + 状态量)
+ FT字段(Fx,Fy,Fz,Mx,My,Mz)
+ Label
+ ur_fresh
+ ft_fresh
```

### 2.1 时间列

- `epoch_time`
  - 含义：当前融合行写入时的绝对时间（Unix Epoch 秒）
  - 类型：`float`
  - 来源：`time.time()`

### 2.2 UR 字段（来自 30003 实时包）

- `Time`
- `Act_q0` ~ `Act_q5`
- `Act_qd0` ~ `Act_qd5`
- `Act_I0` ~ `Act_I5`
- `Act_X`, `Act_Y`, `Act_Z`, `Act_RX`, `Act_RY`, `Act_RZ`
- `Act_dX`, `Act_dY`, `Act_dZ`, `Act_dRX`, `Act_dRY`, `Act_dRZ`
- `Tgt_q0` ~ `Tgt_q5`
- `Robot_Mode`
- `Safety_Mode`
- `Main_Voltage`
- `Robot_Voltage`
- `Robot_Current`

说明：
- 这些列由 `scripts/ur_reader.py` 解析 UR `30003` 数据包得到。
- 若某一行触发自 FT300 线程、UR 暂无新样本，会沿用最近一次 UR 值；如果还没有任何 UR 值则是 `NaN`。

### 2.3 FT300 字段（来自串口流）

- `Fx`, `Fy`, `Fz`（力）
- `Mx`, `My`, `Mz`（力矩）

说明：
- 由 `scripts/ft300_reader.py` 读取串口帧，经过帧头+CRC 校验后解码。
- 缩放规则：
  - 力：原始值 / 100.0
  - 力矩：原始值 / 1000.0

### 2.4 标记与新鲜度列

- `Label`
  - 含义：实验段标记位
  - 取值：`0` 或 `1`
  - 控制方式：GUI 按钮或 `Space` 键切换

- `ur_fresh`
  - 含义：该行是否包含 UR 新样本触发
  - 取值：`0` 或 `1`

- `ft_fresh`
  - 含义：该行是否包含 FT300 新样本触发
  - 取值：`0` 或 `1`

---

## 3. 总监控程序怎么写的（架构说明）

## 3.1 文件分工

- `run_gui.py`
  - Python 启动入口，加载并运行 GUI 主程序

- `scripts/fusion_logger_gui.py`
  - 主界面与融合逻辑
  - 线程管理、曲线刷新、CSV 与 metadata 写入

- `scripts/ur_reader.py`
  - UR10 实时 socket 读取与解析（仅数据读取，不含控制）

- `scripts/ft300_reader.py`
  - FT300 串口读取、帧同步、CRC 校验、六维数据解析

## 3.2 线程模型

- `URWorker(QThread)`
  - 连接 UR `ip:port`（默认 `10.160.9.21:30003`）
  - 持续读包并解析为 `dict`，通过 Qt signal 发回 GUI 主线程

- `FTWorker(QThread)`
  - 连接 FT300 串口（默认 `/dev/ttyUSB0`, `19200`, `slave_id=9`）
  - 持续读帧并解析为 `dict`，通过 Qt signal 发回 GUI 主线程

- GUI 主线程
  - 接收两个线程的数据
  - 更新最新值缓存
  - 生成融合行写 CSV
  - 更新 pyqtgraph 曲线

## 3.3 融合写入策略

1. 任意线程到达新样本（UR 或 FT300）即触发写一行。  
2. 行内字段由“最新缓存值”拼接：
   - UR 部分取 `latest_ur`
   - FT 部分取 `latest_ft`
3. 当前触发源的 fresh 标志置为 1，另一源无新数据为 0。  
4. `epoch_time` 使用写行时刻绝对时间。  
5. 每 20 行 `flush`，降低异常中断时数据丢失。

## 3.4 GUI 展示布局（单页面）

中部 6 个图窗，每个图窗多曲线：

- UR关节角：`Act_q0~Act_q5`
- UR关节速度：`Act_qd0~Act_qd5`
- UR关节电流：`Act_I0~Act_I5`
- FT300力：`Fx,Fy,Fz`
- FT300力矩：`Mx,My,Mz`
- TCP位姿：`Act_X,Act_Y,Act_Z,Act_RX,Act_RY,Act_RZ`

所有曲线默认仅保留最近 300 个点用于滚动显示。

---

## 4. metadata.txt 内容

`metadata.txt` 主要记录：

- UR 参数（IP/端口）
- FT 参数（串口/波特率/slave_id）
- 开始时间、停止时间
- CSV 路径
- 样本总数
- 是否正常停止（`normal_stop`）
- 采集过程错误摘要（`errors`）

---

## 5. 运行方式

```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
python3 run_gui.py
```
