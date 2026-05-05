# data_extend

## 1. 数据说明

- `data/`：真实实验数据目录，保留原始会话文件，不在本流程中修改。
- `base_data_clean.csv`：基于 8 个真实实验会话整理出的基础表。
- `synthetic_shovel_data_100.csv`：基于实验趋势假设构造的 synthetic / simulated 合成扩展数据。
- `combined_data_with_flag.csv`：真实实验数据与合成扩展数据的合并表，使用 `is_synthetic` 与 `data_source` 字段区分。
- 递归扫描 `data/` 下的 `.csv/.xlsx/.xls` 后，未发现统一完整的 `speed_setting / penetration_depth / entry_angle / scooped_mass` 原始设计总表，因此当前基础表由 8 个 session 级真实样本构成。

## 2. 建模假设

- 铲泥重量与机器臂速度设置、下潜深度、切入角度之间近似满足二次响应面关系。
- 切入角度存在最优区间，趋势中心设定在约 `35°` 附近。
- 机器臂速度存在中等最优区间，速度过低或过高都可能降低铲泥保持能力。
- 铲子下潜深度存在适中最优区间，而非越深越优。
- 三个因素之间可能存在交互影响，因此模型包含交互项。

## 3. 模型说明

- 主模型：二次响应面回归（quadratic response surface regression）。
- 模型包含一次项、二次项和交互项。
- `speed_setting` 在真实基础表中不是原始实验表单直接记录值，而是由 `Act_qd*` 与 TCP 运动强度推算的代理变量。
- `penetration_depth` 与 `entry_angle` 依据用户提供的 8 组实验设定，按时间顺序映射到对应真实会话。
- 模型主要用于趋势分析、响应面展示、方法验证和参数寻优参考。

## 4. 运行方式

```bash
python generate_synthetic_data.py
python response_surface_regression.py
python optimize_response_surface.py
```

## 5. 结果摘要

- 原始真实实验数据数量：`8`
- 合成扩展数据数量：`100`
- 二次响应面模型公式：`scooped_mass = -621.736111 + 218.808619 * speed_setting + 49.185807 * penetration_depth + 13.806745 * entry_angle - 728.146570 * speed_setting² + 15.913510 * speed_setting * penetration_depth + 3.023693 * speed_setting * entry_angle - 0.972549 * penetration_depth² + 0.009497 * penetration_depth * entry_angle - 0.224407 * entry_angle²`
- R²：`0.6674`
- Adjusted R²：`0.6369`
- RMSE：`66.3002`
- MAE：`32.8335`
- 预测最优切入角度：`34.694 deg`
- 预测最优下潜深度：`29.796 mm`
- 预测最优速度设置：`0.543`
- 最大预测铲泥重量：`417.640 g`

## 6. 严格声明

- synthetic 数据不能作为真实实验数据使用。
- 响应面模型结果来自“初步真实实验 + 明确标记的 synthetic 扩展数据”的联合拟合。
- 该拟合结果主要用于趋势展示、参数优化参考和方法验证，不等同于完全由真实实验直接证明的结论。
- 在论文中应表述为“基于初步实验与响应面仿真扩展得到”，而不能表述为“通过大量真实实验得到”。
- 预测最优参数组合仍需要后续真实实验验证。

## 7. 依赖

```bash
pip install pandas numpy matplotlib scikit-learn statsmodels openpyxl
```

## 8. 输出文件说明

- `plots/`：原始散点、synthetic 分布、三张响应面图、预测对比图、残差图、敏感性图。
- `model_outputs/response_surface_model_metrics.json`：拟合指标。
- `model_outputs/response_surface_coefficients.csv`：模型系数。
- `model_outputs/anova_or_term_importance.csv`：项显著性与重要性。
- `model_outputs/predicted_optimum.json`：网格寻优结果。
- `model_outputs/fitted_model_summary.txt`：回归摘要与论文风格结果解释。
