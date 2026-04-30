# 本次任务总结

## 1. 任务目标

在 `src/ur10_ft300_monitor` 下新增离线实验数据处理管线，支持：
- 单实验处理（清洗、指标、作图、总结）
- 批量处理（汇总、评分、对比图）
- 不修改原始采集程序与原始 CSV

## 2. 根因分析

- 现有系统只负责采集与可视化，缺少实验后标准化处理闭环。
- 需要统一算法与结果格式，便于不同实验参数横向比较。

## 3. 修改文件清单

- 新增 `src/ur10_ft300_monitor/analysis/metrics_utils.py`
- 新增 `src/ur10_ft300_monitor/analysis/process_experiment_data.py`
- 新增 `src/ur10_ft300_monitor/analysis/batch_process_all.py`
- 新增 `src/ur10_ft300_monitor/analysis/README_analysis.md`
- 新增 `src/docs/task_logs/2026-04-30_ur10_ft300_offline_analysis_pipeline.md`（本文件）

## 4. 新增功能

- 必要列校验与异常提示；
- 时间列回退策略（epoch_time -> Time -> 行号）；
- Label=1 优先实验段提取与自动回退；
- fresh 过滤优先与自动回退；
- FT300 零点修正、滑动平均平滑；
- 核心指标计算：
  - `F_resultant/M_resultant` 的 max/mean/std/rms
  - `path_length`
  - `E_force/E_per_mass`
  - `I_sum` 的 max/mean/std/rms
  - `smoothness_force`
  - `shock_count`
  - `tcp_speed_max/tcp_speed_mean`
- 单实验图像输出（包含 `torque_resultant_curve.png`）；
- 批量汇总 `summary_metrics.csv/.xlsx`；
- Q 评分与 `rank`；
- 批处理错误日志 `results/processing_errors.txt`。

## 5. 核心实现逻辑

- 单实验入口 `process_experiment_data.py`：
  - 接收 `--dir/--csv`，可选 `--mass-g/--force-threshold/--smooth-window`；
  - 调用 `metrics_utils.process_experiment()` 完成处理并落盘。
- 批量入口 `batch_process_all.py`：
  - 扫描 `data/*/ur10_ft300_realtime_data.csv`；
  - 逐目录处理，失败不终止；
  - 汇总评分并输出对比图。
- 特别处理：
  - 为满足“无数据时固定提示”，批处理改为先扫描数据，再延迟导入 `numpy/pandas/matplotlib`，避免环境依赖在无数据场景下提前中断。

## 6. 执行命令

```bash
python3 -m py_compile analysis/process_experiment_data.py analysis/batch_process_all.py analysis/metrics_utils.py
find analysis -maxdepth 2 -type f | sort
python3 analysis/batch_process_all.py
```

## 7. 测试结果

- 语法检查：通过。
- 结构检查：通过，`analysis/` 文件完整。
- 批处理试运行：由于当前 `data/` 下没有可处理 CSV，输出：
  - “未发现可处理的 ur10_ft300_realtime_data.csv，请完成实验采集后运行 batch_process_all.py。”
- 未编造任何实验结果。

## 8. 剩余问题

- 当前尚无真实实验 CSV，无法验证具体指标数值与图像内容。
- 环境中存在 `numpy/matplotlib` 编译兼容风险；但无数据场景已通过延迟导入规避提前崩溃。

## 9. 下一步建议

- 完成一次实际采集后执行：
  - `python analysis/process_experiment_data.py --dir data/<timestamp> --mass-g <value>`
  - `python analysis/batch_process_all.py`
- 若出现 `numpy/matplotlib` 兼容问题，建议在项目虚拟环境中统一安装：
  - `pip install -U numpy pandas scipy matplotlib openpyxl`
