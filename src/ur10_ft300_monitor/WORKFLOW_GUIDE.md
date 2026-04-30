# UR10_FT300 总流程说明（精简版）

## 1. 采集

启动采集 GUI：

```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
/root/ur10_ws/.venv/bin/python run_gui.py
```

每次采集生成：
- `data/YYYYMMDD_HHMMSS/ur10_ft300_realtime_data.csv`
- `data/YYYYMMDD_HHMMSS/metadata.txt`

## 2. 分析（唯一入口）

启动分析 GUI：

```bash
/root/ur10_ws/.venv/bin/python analysis/run_analysis_gui.py
```

操作步骤：
1. 点击 `读取数据文件夹`，选择一个 `data/YYYYMMDD_HHMMSS`
2. 点击 `测试DeepSeek连接`（建议先测）
3. 点击 `执行分析`

## 3. 分析输出位置

每次分析都会在 `results/` 下创建同名结果目录：

- `results/<数据文件夹名>_analysis_result/`

例如：
- 读取 `data/20260430_212937`
- 输出到 `results/20260430_212937_analysis_result/`

## 4. 输出内容

结果目录内包含：
- `processed_metrics.csv`
- `processed_summary.txt`
- `figures/*.png`
- `*_report.md`（DeepSeek 报告）
- `*_raw.json`（DeepSeek 原始返回）

## 5. 目录结构（当前）

```text
ur10_ft300_monitor/
├── run_gui.py
├── scripts/
│   ├── fusion_logger_gui.py
│   ├── ur_reader.py
│   └── ft300_reader.py
├── analysis/
│   ├── run_analysis_gui.py
│   ├── analysis_gui.py
│   ├── deepseek_reporter.py
│   ├── metrics_utils.py
│   └── README_analysis.md
├── config/
│   ├── llm_config.yaml
│   └── test_deepseek_api.py
├── data/
└── results/
```
