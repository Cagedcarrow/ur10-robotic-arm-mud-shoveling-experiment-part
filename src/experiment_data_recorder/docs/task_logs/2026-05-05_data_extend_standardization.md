# 本次任务总结

## 1. 任务目标

在不修改原始 `data/` 目录的前提下，对现有 `data_extend/` 进行科研规范化重构，使其满足以下目标：

- 保留已有二次响应面建模成果；
- 将文件结构、命名、字段、README 和图表整理成论文可用格式；
- 明确区分 `real_experiment`、`response_surface_augmented`、`model_prediction_grid` 三类数据角色；
- 生成一份基于当前真实样本与模型结果反推得到的后续真实实验设计表。

## 2. 根因分析

- 旧版 `data_extend/` 虽然已经完成合成扩展与响应面回归，但命名仍偏开发临时风格，例如 `base_data_clean.csv`、`synthetic_shovel_data_100.csv`、`combined_data_with_flag.csv`。
- 旧字段采用 `data_source / is_synthetic` 口径，不够适合论文写作和科研数据角色表达。
- 旧目录中脚本位于顶层，输出文件与历史文件混杂，不利于长期维护。
- 当前项目需要进一步把“真实实验样本”“响应面增强样本”“模型预测网格”这三类对象分开讲清楚，避免论文误导。

## 3. 修改文件清单

- 新增脚本：
  - [generate_augmented_response_surface_data.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/scripts/generate_augmented_response_surface_data.py)
  - [response_surface_regression.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/scripts/response_surface_regression.py)
  - [optimize_response_surface.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/scripts/optimize_response_surface.py)
  - [generate_future_experiment_design.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/scripts/generate_future_experiment_design.py)
- 新生成数据：
  - [real_experiment_clean.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/real_experiment_clean.csv)
  - [response_surface_augmented_100.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/response_surface_augmented_100.csv)
  - [combined_modeling_dataset.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/combined_modeling_dataset.csv)
  - [future_real_experiment_design.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/future_real_experiment_design.csv)
  - [prediction_grid.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/prediction_grid.csv)
- 新模型输出：
  - [response_surface_model_metrics.json](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/response_surface_model_metrics.json)
  - [response_surface_coefficients.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/response_surface_coefficients.csv)
  - [term_importance.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/term_importance.csv)
  - [predicted_optimum.json](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/predicted_optimum.json)
  - [fitted_model_summary.txt](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/fitted_model_summary.txt)
- 新文档：
  - [README.md](/root/ur10_ws/src/experiment_data_recorder/data_extend/README.md)
- 旧文件归档：
  - `data_extend/legacy_backup/`

## 4. 新增功能

- 引入新的数据角色字段：
  - `data_role`
  - `source_description`
  - `is_measured`
- 将真实样本、增强样本和预测网格点严格区分。
- 将旧顶层脚本迁移为 `data_extend/scripts/` 下的规范入口脚本。
- 生成后续真实补充实验设计表，共 48 条实验点。
- 生成 `prediction_grid.csv`，用于显式保存 `model_prediction_grid` 角色的数据点。
- 将旧版 CSV、脚本、模型输出和图表归档到 `legacy_backup/`，避免信息丢失。

## 5. 核心实现逻辑

- `real_experiment_clean.csv`
  - 基于 8 个会话级真实样本生成；
  - `penetration_depth` 与 `entry_angle` 按时间顺序映射到用户给出的 8 组实验设定；
  - `speed_setting` 由 `Act_qd*` 与 TCP 速度强度推导得到代理变量。
- `response_surface_augmented_100.csv`
  - 采用二次响应面趋势假设生成；
  - 以约 `35°`、中等速度、约 `30 mm` 深度为最优中心；
  - 包含一次项、二次项、交互项和有限噪声。
- `combined_modeling_dataset.csv`
  - 只包含 measured real experiment + response_surface_augmented 两类建模样本；
  - 不把 prediction grid 混进模型训练主表。
- `prediction_grid.csv`
  - 在三维网格上输出 125000 个模型预测点；
  - 显式标记为 `data_role = model_prediction_grid`。
- `future_real_experiment_design.csv`
  - 围绕最优区域生成 `5 × 3 × 3 = 45` 个基础实验点；
  - 中心点 `(35°, 30 mm, 0.55)` 额外重复 3 次；
  - 共 48 条后续真实实验设计点。

## 6. 执行命令

```bash
python3 -m py_compile data_extend/scripts/*.py
python3 data_extend/scripts/generate_augmented_response_surface_data.py
python3 data_extend/scripts/response_surface_regression.py
python3 data_extend/scripts/optimize_response_surface.py
python3 data_extend/scripts/generate_future_experiment_design.py
```

## 7. 测试结果

- `py_compile` 通过。
- 重新生成的核心数据表状态：
  - `real_experiment_clean.csv`：8 行
  - `response_surface_augmented_100.csv`：100 行
  - `combined_modeling_dataset.csv`：108 行
  - `future_real_experiment_design.csv`：48 行
  - `prediction_grid.csv`：125000 行
- 模型结果：
  - `R² = 0.6674`
  - `Adjusted R² = 0.6369`
  - `RMSE = 66.3002`
  - `MAE = 32.8335`
- 预测最优参数：
  - `optimal_entry_angle = 34.694 deg`
  - `optimal_penetration_depth = 29.796 mm`
  - `optimal_speed_setting = 0.543`
  - `predicted_max_scooped_mass = 417.640 g`
- 图表检查：
  - `plots/` 下成功生成 8 张目标图。
- JSON 检查：
  - `response_surface_model_metrics.json` 合法；
  - `predicted_optimum.json` 合法。

## 8. 剩余问题

- 当前环境仍存在 `SciPy` 对 `NumPy` 版本的兼容性警告，但未阻塞建模流程。
- measured 真实样本仍只有 8 条，增强样本只用于趋势建模和参数寻优参考，不能替代后续真实实验。
- `speed_setting` 是由运动数据推导得到的代理变量，不是实验记录表单中的原始设定值。

## 9. 下一步建议

- 后续真实实验建议直接记录：
  - `speed_setting`
  - `penetration_depth`
  - `entry_angle`
  - `scooped_mass`
  - `energy`
  - `torque_mean`
  - `torque_peak`
- 可优先执行 `future_real_experiment_design.csv` 中的 48 条设计点，特别关注中心点重复和最优区域周围的加密采样。
- 若后续真实样本增加，可进一步改为 CCD、Box-Behnken 或带重复中心点的正式 DOE 方案。
