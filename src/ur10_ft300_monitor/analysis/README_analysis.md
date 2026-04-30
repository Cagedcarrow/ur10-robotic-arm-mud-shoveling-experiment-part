# UR10+FT300 实验数据离线处理说明

## 1. 用途

本目录用于“实验后处理”：
- 读取 `data/YYYYMMDD_HHMMSS/ur10_ft300_realtime_data.csv`
- 清洗并提取有效实验段
- 计算力学/轨迹/能量/平滑性指标
- 生成单次实验图表与文本总结
- 批量汇总多个实验并计算综合评分 `Q`

该流程只处理数据，不会发送任何机械臂运动控制命令。

## 2. 依赖安装

```bash
pip install numpy pandas scipy matplotlib openpyxl
```

若运行时报缺包，请先安装以上依赖后再执行。

## 3. 单个实验处理

按目录处理：

```bash
python analysis/process_experiment_data.py --dir data/20260430_203015
```

按 CSV 直接处理：

```bash
python analysis/process_experiment_data.py --csv data/20260430_203015/ur10_ft300_realtime_data.csv
```

带人工质量与阈值：

```bash
python analysis/process_experiment_data.py --dir data/20260430_203015 --mass-g 132.5 --force-threshold 10
```

输出到该实验目录：
- `processed_metrics.csv`（1 行指标）
- `processed_summary.txt`（中文总结）
- `figures/*.png`（图像）

## 4. 批量处理

```bash
python analysis/batch_process_all.py
```

功能：
- 遍历 `data/*/ur10_ft300_realtime_data.csv`
- 逐实验处理并保留单次结果
- 汇总生成：
  - `results/summary_metrics.csv`
  - `results/summary_metrics.xlsx`
  - `results/figures/mass_vs_force.png`
  - `results/figures/fmax_bar.png`
  - `results/figures/energy_bar.png`
  - `results/figures/score_bar.png`
- 错误写入 `results/processing_errors.txt`

## 5. manual_record.txt 格式与优先级

可在实验目录新增：

```text
mass_g=132.5
experiment_id=L9-01
d_mm=20
theta_deg=30
vc_mps=0.05
vl_mps=0.05
note=正常铲取，无明显卡滞
```

优先级：
- `--mass-g` 命令行参数优先于 `manual_record.txt` 中的 `mass_g`
- 其他字段从 `manual_record.txt` 读取并进入结果

## 6. 指标算法与含义

- `F_resultant = sqrt(Fx_smooth^2 + Fy_smooth^2 + Fz_smooth^2)`  
  输出 `F_max/F_mean/F_std/F_rms`，反映阻力强度与波动。

- `M_resultant = sqrt(Mx_smooth^2 + My_smooth^2 + Mz_smooth^2)`  
  输出 `M_max/M_mean/M_std/M_rms`，反映扭转载荷。

- `path_length = sum(sqrt(dX^2+dY^2+dZ^2))`  
  反映 TCP 实际轨迹长度。

- `E_force = sum(F_resultant * ds)`  
  末端机械作业能量估计（非电能）。

- `E_per_mass = E_force / mass_g`  
  单位质量作业能量，质量缺失时为 `NaN`。

- `I_sum = |I0|+...+|I5|`  
  输出 `I_max/I_mean/I_std/I_rms`，反映关节负载。

- `smoothness_force = mean(|ΔF|/Δt)`  
  越小越平稳。

- `shock_count`  
  统计 `|ΔF| > force_threshold` 次数，识别冲击/卡滞风险。

- `tcp_speed = sqrt(Act_dX^2 + Act_dY^2 + Act_dZ^2)`  
  输出 `tcp_speed_max/tcp_speed_mean`。

- 采样质量指标：
  `sample_count_total/sample_count_exp/duration/ft_fresh_ratio/ur_fresh_ratio`

## 7. 综合评分 Q（批量）

目标方向：
- `mass_g` 越大越好（正向）
- `F_max/E_force/smoothness_force/I_mean` 越小越好（负向）

归一化：
- 正向：`(x-min)/(max-min)`
- 负向：`(max-x)/(max-min)`
- 若 `max==min`，该列统一 `0.5`

评分：

```text
Q = 0.35*mass_score + 0.20*F_score + 0.20*E_score + 0.15*S_score + 0.10*I_score
```

并输出 `rank`（Q 越大排名越靠前，第一名 rank=1）。

## 8. 数据清洗与基线策略

- 时间列：优先 `epoch_time`，其次 `Time`，再退化为行号。
- 实验段：优先 `Label=1`，不足 10 行回退全段并给 warning。
- fresh 过滤：FT 指标优先 `ft_fresh=1`，UR 指标优先 `ur_fresh=1`，不足 10 行回退。
- 缺失值：`to_numeric -> ffill -> bfill`，指标端 NaN 安全计算。
- FT 零点修正：
  1. 首个 `Label=1` 前的 `Label=0` 且 >=10 行；
  2. 否则实验段前 5% 且 >=10 行；
  3. 再不足则不修正并写 warning。
- 平滑：默认 rolling window=5。

## 9. 常见问题

- 没有 `Label=1` 怎么办：自动回退全段，并在 `processed_summary.txt` 标注警告。
- FT300 零点漂移怎么办：检查 baseline_method；若为 `none`，建议延长实验前静止段并重新采集。
- fresh_ratio 太低说明什么：对应链路刷新不足或通信不稳定，指标可信度下降。
- `mass_g` 未填写怎么办：`E_per_mass` 为 `NaN`；批量评分中 `mass_score` 用中位数填补后归一化。

