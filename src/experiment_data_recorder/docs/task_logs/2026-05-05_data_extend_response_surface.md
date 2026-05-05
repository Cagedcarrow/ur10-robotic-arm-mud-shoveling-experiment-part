# 本次任务总结

## 1. 任务目标

在不修改原始 `data/` 实验目录的前提下，新建 `data_extend/`，构建一套用于“真实实验基础样本 + synthetic 合成扩展样本”的二次响应面回归分析流程，用于研究 `speed_setting`、`penetration_depth`、`entry_angle` 对 `scooped_mass` 的影响趋势，并输出模型、图表、最优参数和说明文档。

## 2. 根因分析

- 原始 `data/` 中不存在统一的实验设计总表，未直接包含 `speed_setting / penetration_depth / entry_angle / scooped_mass` 这四个字段。
- 现有真实实验数据以 8 个会话目录形式分散保存，能够直接利用的重量结果来自既有重量分析输出，而不是原始 CSV 中的单列标签。
- `speed_setting` 在真实数据中没有显式记录，因此只能依据 `Act_qd0..Act_qd5` 与 TCP 速度强度构造会话级速度代理变量。
- 由于真实样本只有 8 条，无法直接支撑稳定的三因素二次响应面拟合，因此需要明确标记的 synthetic 扩展数据辅助趋势建模。

## 3. 修改文件清单

- [data_extend/generate_synthetic_data.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/generate_synthetic_data.py)
- [data_extend/response_surface_regression.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/response_surface_regression.py)
- [data_extend/optimize_response_surface.py](/root/ur10_ws/src/experiment_data_recorder/data_extend/optimize_response_surface.py)
- [data_extend/README.md](/root/ur10_ws/src/experiment_data_recorder/data_extend/README.md)
- [data_extend/base_data_clean.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/base_data_clean.csv)
- [data_extend/synthetic_shovel_data_100.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/synthetic_shovel_data_100.csv)
- [data_extend/combined_data_with_flag.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/combined_data_with_flag.csv)
- [data_extend/model_outputs/response_surface_model_metrics.json](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/response_surface_model_metrics.json)
- [data_extend/model_outputs/response_surface_coefficients.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/response_surface_coefficients.csv)
- [data_extend/model_outputs/anova_or_term_importance.csv](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/anova_or_term_importance.csv)
- [data_extend/model_outputs/predicted_optimum.json](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/predicted_optimum.json)
- [data_extend/model_outputs/fitted_model_summary.txt](/root/ur10_ws/src/experiment_data_recorder/data_extend/model_outputs/fitted_model_summary.txt)
- `data_extend/plots/*.png`

## 4. 新增功能

- 递归扫描 `data/` 下的 `.csv/.xlsx/.xls` 文件并识别潜在设计字段。
- 从 8 个真实会话中整理会话级基础表 `base_data_clean.csv`。
- 基于 `Act_qd*` 与 TCP 运动强度推算 `speed_setting` 代理变量并归一化到 `0.2~1.0`。
- 生成 100 条明确标记为 `synthetic` 的合成扩展样本。
- 建立三因素二次响应面回归模型，输出系数、显著性、拟合指标和论文风格解释文本。
- 执行密集网格搜索，得到预测最优切入角、下潜深度、速度设置和最大预测铲泥重量。
- 生成原始散点、synthetic 分布、三张响应面图、预测对比图、残差图和敏感性图。

## 5. 核心实现逻辑

- 真实基础表构造：
  - 按时间顺序将 8 个会话映射到用户给出的 8 组 `group / penetration_depth / entry_angle` 设定。
  - `scooped_mass` 取自现有重量分析结果。
  - `speed_setting` 由活动段关节速度强度与 TCP 线速度活动强度混合构成代理量。
- synthetic 数据生成：
  - 采用“全局 Latin Hypercube + 真实点附近局部扰动”组合采样。
  - 以约 `35°`、中等速度、适中深度为中心构造二次响应面趋势。
  - 加入有限噪声并做非负裁剪，保证既有随机波动又不破坏主趋势。
- 模型拟合：
  - 使用 `PolynomialFeatures(degree=2)` + `LinearRegression` 得到二次项与交互项拟合。
  - 使用 `statsmodels.OLS` 输出摘要、p-value 和置信区间。
- 参数优化：
  - 在 `speed_setting 0.2~1.0`、`penetration_depth 20~40`、`entry_angle 20~60` 范围内做三维网格搜索。
  - 选择预测 `scooped_mass` 最大的参数组合作为最优点。

## 6. 执行命令

```bash
python3 -m py_compile data_extend/generate_synthetic_data.py data_extend/response_surface_regression.py data_extend/optimize_response_surface.py
python3 data_extend/generate_synthetic_data.py
python3 data_extend/response_surface_regression.py
python3 data_extend/optimize_response_surface.py
```

## 7. 测试结果

- 脚本语法检查通过。
- `base_data_clean.csv` 成功生成，包含 8 条真实会话样本。
- `synthetic_shovel_data_100.csv` 成功生成，包含 100 条 synthetic 样本，并带有 `data_source="synthetic"` 与 `is_synthetic=1` 标记。
- `combined_data_with_flag.csv` 成功生成，包含 108 条联合样本。
- 二次响应面模型成功拟合，主要指标如下：
  - `R² = 0.6674`
  - `Adjusted R² = 0.6369`
  - `RMSE = 66.3002`
  - `MAE = 32.8335`
- 预测最优参数组合如下：
  - `optimal_entry_angle = 34.694 deg`
  - `optimal_penetration_depth = 29.796 mm`
  - `optimal_speed_setting = 0.543`
  - `predicted_max_scooped_mass = 417.640 g`
- 所有目标图像成功输出到 `data_extend/plots/`。

## 8. 剩余问题

- 当前环境中 `scipy` 对系统 `numpy` 版本给出兼容性警告，但未阻塞本次 `sklearn / statsmodels` 建模流程。
- 真实实验样本仅有 8 条，因此模型趋势仍然强依赖 synthetic 扩展设计，不能被等同解释为充分真实实验结论。
- `speed_setting` 为派生代理变量，而非实验表单原始设定值，这会限制参数物理解释的精确性。

## 9. 下一步建议

- 后续真实实验应显式记录 `speed_setting / penetration_depth / entry_angle / scooped_mass` 设计表，避免再做会话级反推。
- 建议增加更多真实实验点，特别是在 `entry_angle 30~40°`、`penetration_depth 25~35 mm`、中等速度区域进行加密采样。
- 可进一步加入交叉验证、留一验证或 bootstrap 置信区间，以提高响应面结论的稳健性描述。
- 若论文需要更强的统计解释，可补充标准化系数图、偏效应图和真实数据/合成数据分层拟合对比。
