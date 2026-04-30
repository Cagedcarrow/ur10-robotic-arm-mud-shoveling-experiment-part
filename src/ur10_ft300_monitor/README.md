# UR10 + FT300 一体化监控工具包

该工具包用于：
- 采集 UR10 + FT300 实时数据
- 对单次实验目录执行本地指标处理 + DeepSeek 报告分析

## 总流程总览
- 见 `WORKFLOW_GUIDE.md`

## 目录结构（当前）
```text
ur10_ft300_monitor/
├── README.md
├── WORKFLOW_GUIDE.md
├── requirements.txt
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
├── results/
└── docs/
    └── usage.md
```

## 安装依赖
```bash
cd ~/ur10_ws/src/ur10_ft300_monitor
pip install -r requirements.txt
```

## 启动采集 GUI
```bash
python3 run_gui.py
```

## 启动分析 GUI
```bash
python3 analysis/run_analysis_gui.py
```

## 安全说明
- 本工具仅读取和分析数据，不发送机械臂运动控制命令。
- 实验前确认急停可用并保持机器人周围安全空间。
