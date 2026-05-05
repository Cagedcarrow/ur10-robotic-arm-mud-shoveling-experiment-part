# data_extend

## 1. Data Structure

- `data/`：原始真实实验目录，本流程不会修改、覆盖或删除其中任何文件。
- `real_experiment_clean.csv`：8 条 measured 真实实验样本，从原始 `data/` 会话级样本整理得到。
- `response_surface_augmented_100.csv`：100 条响应面增强样本，不是直接实验测量数据。
- `combined_modeling_dataset.csv`：用于二次响应面建模的统一数据集，包含 measured real experiment 与 response_surface_augmented 两类样本。
- `model_outputs/prediction_grid.csv`：基于拟合模型生成的预测网格点，`data_role = model_prediction_grid`。
- `future_real_experiment_design.csv`：用于后续补充真实实验的设计表，当前测量字段留空。

## 2. Data Role Definitions

- `data_role = real_experiment`：measured from original experiment
- `data_role = response_surface_augmented`：generated from quadratic response surface assumption
- `data_role = model_prediction_grid`：predicted by fitted response surface model
- `is_measured = 1` 仅对应真实测量样本；增强样本和预测网格均为 `0`。

## 3. Real Experiment Table

- `real_experiment_clean.csv` 来自原始 `data/`，共 8 条 measured 样本。
- `penetration_depth` 与 `entry_angle` 按实验设定映射到 8 个真实会话。
- `speed_setting` 不是原始实验表单直接记录字段，而是依据 `Act_qd*` 与 TCP 速度强度推导得到的代理变量。
- 原始 `data/` 中未发现统一完整的 `speed_setting / penetration_depth / entry_angle / scooped_mass` 设计总表，因此采用 session 级整理方式。

## 4. Response-Surface Augmented Table

- `response_surface_augmented_100.csv` 不是直接实验测量数据。
- 该数据集基于初步实验趋势假设构造，用于改善响应面形状展示、模型稳定性分析和参数寻优参考。
- 增强样本保留明确来源字段，不会被重标记为 measured real experiment。

## 5. Modeling Assumptions

- 铲泥重量与速度设置、下潜深度、切入角度之间近似满足二次响应面关系。
- 切入角度存在最优区间，模型趋势中心设定在约 `35°` 附近。
- 机器臂速度存在中等最优区间，过低或过高都可能降低铲泥保持能力。
- 下潜深度存在适中最优区间，而非越深越优。
- 三个因素之间可能存在交互影响，因此模型包含一次项、二次项与交互项。

## 6. Modeling Scripts

```bash
python3 data_extend/scripts/generate_augmented_response_surface_data.py
python3 data_extend/scripts/response_surface_regression.py
python3 data_extend/scripts/optimize_response_surface.py
python3 data_extend/scripts/generate_future_experiment_design.py
```

## 7. Result Summary

- measured real experiment count: `8`
- response_surface_augmented count: `100`
- quadratic response-surface formula: `scooped_mass = -621.736111 + 218.808619 * speed_setting + 49.185807 * penetration_depth + 13.806745 * entry_angle - 728.146570 * speed_setting² + 15.913510 * speed_setting * penetration_depth + 3.023693 * speed_setting * entry_angle - 0.972549 * penetration_depth² + 0.009497 * penetration_depth * entry_angle - 0.224407 * entry_angle²`
- R²: `0.6674`
- Adjusted R²: `0.6369`
- RMSE: `66.3002`
- MAE: `32.8335`
- predicted optimal entry angle: `34.694 deg`
- predicted optimal penetration depth: `29.796 mm`
- predicted optimal speed setting: `0.543`
- predicted maximum scooped mass: `417.640 g`

## 8. Interpretation and Limitations

- 模型预测显示，切入角度约 `35°` 时铲泥重量较大。
- 模型预测显示，中等速度设置更容易获得较高铲泥重量。
- 模型预测显示，下潜深度约 `30 mm` 左右具有较优趋势。
- 这些结论具有参数优化参考意义，但仍需更多真实实验验证。
- 当前结果来自“真实初步实验 + 响应面增强样本”的联合拟合，不等同于大量真实实验直接证明的物理定律。

## 9. Strict Statement

- `response_surface_augmented_100.csv` 不能作为真实测量数据使用。
- `combined_modeling_dataset.csv` 只用于二次响应面回归建模、趋势展示和参数寻优参考。
- `model_prediction_grid` 仅表示拟合模型上的预测网格点，不代表真实实验运行结果。
- 最优参数结论：该最优参数来自“真实初步实验 + 响应面增强样本”的模型预测，不等同于真实测得的运行结果。

## 10. Dependencies

```bash
pip install pandas numpy matplotlib scikit-learn statsmodels openpyxl
```
