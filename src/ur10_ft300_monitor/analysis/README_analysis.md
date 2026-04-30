# UR10+FT300 离线分析说明（当前版本）

本目录只保留当前在用的分析能力：
- 单实验本地指标处理（由 GUI 自动调用）
- 单实验 DeepSeek 报告生成（由 GUI 调用）

> 旧的批量脚本与独立 CLI 入口已移除，避免流程混乱。

## 1. 当前入口

分析 GUI：

```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
python3 analysis/run_analysis_gui.py
```

GUI 内流程：
1. 点击 `读取数据文件夹`，选择 `data/YYYYMMDD_HHMMSS`
2. 点击 `执行分析`
3. 若缺 `processed_metrics.csv`，会弹窗确认后自动从原始 CSV 计算
4. 自动调用 DeepSeek，输出报告

## 2. 输入与输出

### 输入目录（单实验）
- `data/YYYYMMDD_HHMMSS/ur10_ft300_realtime_data.csv`
- `data/YYYYMMDD_HHMMSS/metadata.txt`（可选）
- `data/YYYYMMDD_HHMMSS/manual_record.txt`（可选）

### 输出目录（固定命名）
- `results/<实验目录名>_analysis_result/`

输出文件：
- `processed_metrics.csv`
- `processed_summary.txt`
- `figures/*.png`
- `<...>_report.md`（DeepSeek 分析报告）
- `<...>_raw.json`（DeepSeek 原始响应）

## 3. 指标方法（摘要）

核心计算在 `metrics_utils.py`：
- 时间轴：优先 `epoch_time`
- 实验段：优先 `Label=1`，不足时回退全段
- 数据清洗：`to_numeric -> ffill -> bfill`
- FT 零点修正 + 滑动平均（默认 window=5）
- 主要指标：
  - `F_max/F_mean/F_std/F_rms`
  - `M_max/M_mean/M_std/M_rms`
  - `E_force`、`E_per_mass`
  - `I_max/I_mean/I_std/I_rms`
  - `smoothness_force`、`shock_count`
  - `tcp_speed_max/tcp_speed_mean`

## 4. DeepSeek 配置

编辑：`config/llm_config.yaml`

```yaml
base_url: https://api.deepseek.com
api_key: sk-你的key
model: deepseek-v4-pro
timeout_sec: 120
temperature: 0.2
```

建议先执行：
- 分析 GUI 中的 `测试DeepSeek连接`

## 5. 注意事项

- 当前版本以“单实验分析”作为唯一标准流程。
- 若网络不稳定，请设置 `HTTP_PROXY/HTTPS_PROXY` 后再调用 API。
- 本工具链仅采集与分析，不发送机械臂运动控制指令。
