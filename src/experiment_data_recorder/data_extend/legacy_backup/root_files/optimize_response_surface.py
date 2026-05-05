#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from response_surface_regression import (
    COMBINED_DATA_PATH,
    FEATURES,
    METRICS_PATH,
    OUTPUT_ROOT,
    SUMMARY_PATH,
    TARGET,
    build_formula,
    fit_response_surface_model,
)


OPTIMUM_PATH = OUTPUT_ROOT / "model_outputs" / "predicted_optimum.json"
README_PATH = OUTPUT_ROOT / "README.md"


def optimize_grid(result: dict[str, object]) -> dict[str, float]:
    speed_grid = pd.Series(np.linspace(0.2, 1.0, 50), name="speed_setting")
    depth_grid = pd.Series(np.linspace(20.0, 40.0, 50), name="penetration_depth")
    angle_grid = pd.Series(np.linspace(20.0, 60.0, 50), name="entry_angle")

    mesh = pd.MultiIndex.from_product([speed_grid, depth_grid, angle_grid], names=FEATURES).to_frame(index=False)
    pred = result["linreg"].predict(result["poly"].transform(mesh[FEATURES].to_numpy(dtype=float)))
    best_idx = int(pred.argmax())
    best = mesh.iloc[best_idx]
    return {
        "optimal_entry_angle": float(best["entry_angle"]),
        "optimal_penetration_depth": float(best["penetration_depth"]),
        "optimal_speed_setting": float(best["speed_setting"]),
        "predicted_max_scooped_mass": float(pred[best_idx]),
        "model_type": "quadratic_response_surface_regression",
        "warning": "The optimum is based on synthetic-augmented response surface fitting, not direct experimental verification.",
    }


def write_readme(df: pd.DataFrame, metrics: dict[str, float], optimum: dict[str, float], formula: str) -> None:
    lines = [
        "# data_extend",
        "",
        "## 1. 数据说明",
        "",
        "- `data/`：真实实验数据目录，保留原始会话文件，不在本流程中修改。",
        "- `base_data_clean.csv`：基于 8 个真实实验会话整理出的基础表。",
        "- `synthetic_shovel_data_100.csv`：基于实验趋势假设构造的 synthetic / simulated 合成扩展数据。",
        "- `combined_data_with_flag.csv`：真实实验数据与合成扩展数据的合并表，使用 `is_synthetic` 与 `data_source` 字段区分。",
        "- 递归扫描 `data/` 下的 `.csv/.xlsx/.xls` 后，未发现统一完整的 `speed_setting / penetration_depth / entry_angle / scooped_mass` 原始设计总表，因此当前基础表由 8 个 session 级真实样本构成。",
        "",
        "## 2. 建模假设",
        "",
        "- 铲泥重量与机器臂速度设置、下潜深度、切入角度之间近似满足二次响应面关系。",
        "- 切入角度存在最优区间，趋势中心设定在约 `35°` 附近。",
        "- 机器臂速度存在中等最优区间，速度过低或过高都可能降低铲泥保持能力。",
        "- 铲子下潜深度存在适中最优区间，而非越深越优。",
        "- 三个因素之间可能存在交互影响，因此模型包含交互项。",
        "",
        "## 3. 模型说明",
        "",
        "- 主模型：二次响应面回归（quadratic response surface regression）。",
        "- 模型包含一次项、二次项和交互项。",
        "- `speed_setting` 在真实基础表中不是原始实验表单直接记录值，而是由 `Act_qd*` 与 TCP 运动强度推算的代理变量。",
        "- `penetration_depth` 与 `entry_angle` 依据用户提供的 8 组实验设定，按时间顺序映射到对应真实会话。",
        "- 模型主要用于趋势分析、响应面展示、方法验证和参数寻优参考。",
        "",
        "## 4. 运行方式",
        "",
        "```bash",
        "python generate_synthetic_data.py",
        "python response_surface_regression.py",
        "python optimize_response_surface.py",
        "```",
        "",
        "## 5. 结果摘要",
        "",
        f"- 原始真实实验数据数量：`{int((df['is_synthetic'] == 0).sum())}`",
        f"- 合成扩展数据数量：`{int((df['is_synthetic'] == 1).sum())}`",
        f"- 二次响应面模型公式：`{formula}`",
        f"- R²：`{metrics['r2']:.4f}`",
        f"- Adjusted R²：`{metrics['adjusted_r2']:.4f}`",
        f"- RMSE：`{metrics['rmse']:.4f}`",
        f"- MAE：`{metrics['mae']:.4f}`",
        f"- 预测最优切入角度：`{optimum['optimal_entry_angle']:.3f} deg`",
        f"- 预测最优下潜深度：`{optimum['optimal_penetration_depth']:.3f} mm`",
        f"- 预测最优速度设置：`{optimum['optimal_speed_setting']:.3f}`",
        f"- 最大预测铲泥重量：`{optimum['predicted_max_scooped_mass']:.3f} g`",
        "",
        "## 6. 严格声明",
        "",
        "- synthetic 数据不能作为真实实验数据使用。",
        "- 响应面模型结果来自“初步真实实验 + 明确标记的 synthetic 扩展数据”的联合拟合。",
        "- 该拟合结果主要用于趋势展示、参数优化参考和方法验证，不等同于完全由真实实验直接证明的结论。",
        "- 在论文中应表述为“基于初步实验与响应面仿真扩展得到”，而不能表述为“通过大量真实实验得到”。",
        "- 预测最优参数组合仍需要后续真实实验验证。",
        "",
        "## 7. 依赖",
        "",
        "```bash",
        "pip install pandas numpy matplotlib scikit-learn statsmodels openpyxl",
        "```",
        "",
        "## 8. 输出文件说明",
        "",
        "- `plots/`：原始散点、synthetic 分布、三张响应面图、预测对比图、残差图、敏感性图。",
        "- `model_outputs/response_surface_model_metrics.json`：拟合指标。",
        "- `model_outputs/response_surface_coefficients.csv`：模型系数。",
        "- `model_outputs/anova_or_term_importance.csv`：项显著性与重要性。",
        "- `model_outputs/predicted_optimum.json`：网格寻优结果。",
        "- `model_outputs/fitted_model_summary.txt`：回归摘要与论文风格结果解释。",
    ]
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not COMBINED_DATA_PATH.exists():
        raise RuntimeError("Missing combined_data_with_flag.csv. Run generate_synthetic_data.py and response_surface_regression.py first.")

    df = pd.read_csv(COMBINED_DATA_PATH)
    result = fit_response_surface_model(df)
    optimum = optimize_grid(result)
    OPTIMUM_PATH.write_text(json.dumps(optimum, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    formula = build_formula(result["metrics"]["intercept"], result["feature_names"], result["linreg"].coef_)
    write_readme(df, metrics, optimum, formula)

    with SUMMARY_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n\n预测最优参数组合\n")
        handle.write(json.dumps(optimum, ensure_ascii=False, indent=2))
        handle.write("\n")

    print(json.dumps(optimum, ensure_ascii=False, indent=2))
    print(
        f"最终总结：真实数据 {int((df['is_synthetic'] == 0).sum())} 条，合成数据 {int((df['is_synthetic'] == 1).sum())} 条，"
        f"R²={metrics['r2']:.4f}，RMSE={metrics['rmse']:.4f}，MAE={metrics['mae']:.4f}。"
    )
    print("该结果是基于初步实验趋势假设的合成扩展数据 + 二次响应面回归分析得到的参数优化结果，不等同于完全由真实实验数据直接证明的结论。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
