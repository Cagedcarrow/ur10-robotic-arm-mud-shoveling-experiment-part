# 本次任务总结

## 1. 任务目标
在 `ur10_ft300_monitor` 现有 GUI 中集成单实验 DeepSeek 分析流程：选择 `data/<timestamp>` 目录，自动检查/生成 `processed_metrics.csv`，调用 DeepSeek API，输出 Markdown 报告到 `results/llm_reports/`。

## 2. 根因分析
原系统仅提供本地指标分析与批处理，不具备 LLM 报告能力；同时命令行入口 `process_experiment_data.py` 强制参数，日常使用成本高。

## 3. 修改文件清单
- `ur10_ft300_monitor/scripts/fusion_logger_gui.py`
- `ur10_ft300_monitor/analysis/deepseek_reporter.py`（新增）
- `ur10_ft300_monitor/config/llm_config.yaml`（新增）
- `ur10_ft300_monitor/requirements.txt`
- `ur10_ft300_monitor/docs/usage.md`

## 4. 新增功能
- GUI 新增单实验分析区：
  - 选择实验目录
  - 测试 DeepSeek 连接
  - 生成单实验报告
  - 打开最新报告
  - 报告预览框
- 自动化流程：若实验目录缺少 `processed_metrics.csv`，弹窗确认后自动执行本地处理。
- DeepSeek 配置文件：首次运行自动创建模板。

## 5. 核心实现逻辑
- `analysis/deepseek_reporter.py` 提供：
  - `ensure_config_file`
  - `load_llm_config`
  - `build_prompt`
  - `test_connection`
  - `generate_single_experiment_report`
- 报告生成时读取：
  - `analysis/README_analysis.md`
  - `processed_metrics.csv`
  - `metadata.txt`（可选）
  - `manual_record.txt`（可选）
- DeepSeek 调用采用 `requests` 直连 OpenAI 兼容 Chat Completions 接口。

## 6. 执行命令
```bash
/root/ur10_ws/.venv/bin/python -m py_compile \
  ur10_ft300_monitor/scripts/fusion_logger_gui.py \
  ur10_ft300_monitor/analysis/deepseek_reporter.py \
  ur10_ft300_monitor/analysis/process_experiment_data.py \
  ur10_ft300_monitor/analysis/batch_process_all.py \
  ur10_ft300_monitor/analysis/metrics_utils.py

/root/ur10_ws/.venv/bin/python - <<'PY'
from pathlib import Path
import sys
root=Path('/root/ur10_ws/src/ur10_ft300_monitor')
sys.path.insert(0,str(root/'analysis'))
from deepseek_reporter import ensure_config_file, load_llm_config
cfg=root/'config'/'llm_config.yaml'
ensure_config_file(cfg)
print(load_llm_config(cfg).get('model'))
PY
```

## 7. 测试结果
- 语法检查通过。
- 配置模板自动创建/读取通过。
- 未配置 API Key 时能给出明确错误提示（预期行为）。
- 采集主流程代码路径未变更，回归风险可控。

## 8. 剩余问题
- GUI 里 DeepSeek 调用当前为主线程执行，网络较慢时会短暂阻塞界面。
- 报告质量依赖模型与提示词，后续可按业务继续迭代。

## 9. 下一步建议
1. 将 DeepSeek 请求迁移到 `QThread`，避免 GUI 卡顿。
2. 增加“报告模板版本号”和实验标签输入，便于追溯。
3. 增加失败重试和超时可视化进度条。
