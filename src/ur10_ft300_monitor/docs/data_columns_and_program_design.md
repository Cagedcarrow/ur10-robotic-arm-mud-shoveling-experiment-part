# UR10 + FT300 数据列与程序设计说明（当前版本）

本文档使用当前版本术语：
- `run_gui.py`：采集 GUI（只采集）
- `analysis/run_analysis_gui.py`：分析 GUI（只分析）
- 单入口分析：`读取数据文件夹 -> 执行分析`
- 分析输出目录：`results/<数据文件夹名>_analysis_result/`

---

## 1. 数据保存位置

每次点击“开始采集”后，会创建时间目录：

```text
ur10_ft300_monitor/data/YYYYMMDD_HHMMSS/
```

目录内包含：
- `ur10_ft300_realtime_data.csv`：融合后的实时数据
- `metadata.txt`：本次采集参数与统计信息

---

## 2. CSV 列总览（`ur10_ft300_realtime_data.csv`）

CSV 列顺序由 `scripts/fusion_logger_gui.py` 中 `self.header` 固定定义：

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
  - 含义：融合行写入时的绝对时间（Unix Epoch 秒）
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
- 由 `scripts/ur_reader.py` 解析 UR `30003` 数据包得到。
- 若当前行由 FT 触发且 UR 没有新样本，UR 字段沿用最近值；若还未收到 UR 则为 `NaN`。

### 2.3 FT300 字段（来自串口流）
- `Fx`, `Fy`, `Fz`（力）
- `Mx`, `My`, `Mz`（力矩）

说明：
- 由 `scripts/ft300_reader.py` 读取串口帧，执行帧头 + CRC 校验后解码。
- 缩放：
  - 力：原始值 / 100.0
  - 力矩：原始值 / 1000.0

### 2.4 标记与新鲜度列
- `Label`
  - 含义：实验段标记位
  - 取值：`0` 或 `1`
  - 控制：GUI 按钮或 `Space`

- `ur_fresh`
  - 含义：该行是否由 UR 新样本触发
  - 取值：`0` 或 `1`

- `ft_fresh`
  - 含义：该行是否由 FT300 新样本触发
  - 取值：`0` 或 `1`

---

## 3. 程序架构（当前）

### 3.1 文件分工
- `run_gui.py`
  - 采集 GUI 启动入口

- `scripts/fusion_logger_gui.py`
  - 采集主界面
  - 线程管理、曲线刷新、CSV 与 metadata 写入

- `scripts/ur_reader.py`
  - UR10 socket 数据读取与解析（只读）

- `scripts/ft300_reader.py`
  - FT300 串口读取、CRC 校验、六维数据解析

- `analysis/run_analysis_gui.py`
  - 分析 GUI 启动入口

- `analysis/analysis_gui.py`
  - 分析页面逻辑（目录选择、执行分析、报告预览）

- `analysis/metrics_utils.py`
  - 本地指标计算核心

- `analysis/deepseek_reporter.py`
  - DeepSeek API 调用与报告生成

### 3.2 采集线程模型
- `URWorker(QThread)`：持续读取 UR 数据并回传 GUI
- `FTWorker(QThread)`：持续读取 FT 数据并回传 GUI
- GUI 主线程：融合数据、写 CSV、刷新曲线

### 3.3 融合写入策略
1. UR/FT 任一新样本到达即写一行。
2. 行字段由最新缓存拼接：`latest_ur + latest_ft`。
3. 触发源 fresh=1，另一路 fresh=0。
4. `epoch_time` 取写行瞬间绝对时间。
5. 每 20 行 flush 一次。

---

## 4. 分析流程（当前单接口）

分析 GUI 启动：

```bash
python3 analysis/run_analysis_gui.py
```

步骤：
1. 点击 `读取数据文件夹`（选 `data/YYYYMMDD_HHMMSS`）
2. 点击 `执行分析`
3. 若缺 `processed_metrics.csv`，弹窗确认后自动处理原始 CSV
4. 调用 DeepSeek 输出分析报告

输出目录固定：

```text
results/<数据文件夹名>_analysis_result/
```

主要输出：
- `processed_metrics.csv`
- `processed_summary.txt`
- `figures/*.png`
- `*_report.md`
- `*_raw.json`

---

## 5. metadata.txt 内容

`metadata.txt` 记录：
- UR 参数（IP/端口）
- FT 参数（串口/波特率/slave_id）
- 开始/停止时间
- CSV 路径
- 样本总数
- 是否正常停止（`normal_stop`）
- 错误摘要（`errors`）

---

## 6. 启动命令（速查）

采集：
```bash
python3 run_gui.py
```

分析：
```bash
python3 analysis/run_analysis_gui.py
```
