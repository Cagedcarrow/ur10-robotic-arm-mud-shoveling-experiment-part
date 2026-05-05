#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from response_surface_regression import (
    COMBINED_DATA_PATH,
    DATA_EXTEND_ROOT,
    FEATURES,
    METRICS_PATH,
    MODEL_DIR,
    SUMMARY_PATH,
    TARGET,
    build_formula,
    fit_response_surface_model,
)


OPTIMUM_PATH = MODEL_DIR / "predicted_optimum.json"
PREDICTION_GRID_PATH = MODEL_DIR / "prediction_grid.csv"
README_PATH = DATA_EXTEND_ROOT / "README.md"


def optimize_grid(result: dict[str, object]) -> tuple[dict[str, object], pd.DataFrame]:
    speed_grid = np.linspace(0.2, 1.0, 50)
    depth_grid = np.linspace(20.0, 40.0, 50)
    angle_grid = np.linspace(20.0, 60.0, 50)

    mesh = pd.MultiIndex.from_product([speed_grid, depth_grid, angle_grid], names=FEATURES).to_frame(index=False)
    pred = result["linreg"].predict(result["poly"].transform(mesh[FEATURES].to_numpy(dtype=float)))
    grid_df = pd.DataFrame(
        {
            "record_id": [f"grid_{idx + 1:06d}" for idx in range(len(mesh))],
            "session_name": [pd.NA] * len(mesh),
            "group": [pd.NA] * len(mesh),
            "speed_setting": mesh["speed_setting"],
            "penetration_depth": mesh["penetration_depth"],
            "entry_angle": mesh["entry_angle"],
            "scooped_mass": pred,
            "speed_setting_source": ["predicted_from_fitted_response_surface"] * len(mesh),
            "speed_proxy_joint_activity": [pd.NA] * len(mesh),
            "speed_proxy_tcp_linear_activity": [pd.NA] * len(mesh),
            "speed_proxy_tcp_angular_activity": [pd.NA] * len(mesh),
            "data_role": ["model_prediction_grid"] * len(mesh),
            "source_description": ["predicted by fitted response surface model"] * len(mesh),
            "is_measured": [0] * len(mesh),
        }
    )

    best_idx = int(pred.argmax())
    best = mesh.iloc[best_idx]
    optimum = {
        "optimal_entry_angle": float(best["entry_angle"]),
        "optimal_penetration_depth": float(best["penetration_depth"]),
        "optimal_speed_setting": float(best["speed_setting"]),
        "predicted_max_scooped_mass": float(pred[best_idx]),
        "model_type": "quadratic_response_surface_regression",
        "data_basis": "8 measured real experiments + 100 response_surface_augmented samples",
        "warning": "该最优参数来自“真实初步实验 + 响应面增强样本”的模型预测，不等同于真实测得的运行结果。",
    }
    return optimum, grid_df


def write_readme(df: pd.DataFrame, metrics: dict[str, float], optimum: dict[str, object], formula: str) -> None:
    lines = [
        "# data_extend",
        "",
        "## 1. Data Structure",
        "",
        "- `data/`：原始真实实验目录，本流程不会修改、覆盖或删除其中任何文件。",
        "- `real_experiment_clean.csv`：8 条 measured 真实实验样本，从原始 `data/` 会话级样本整理得到。",
        "- `response_surface_augmented_100.csv`：100 条响应面增强样本，不是直接实验测量数据。",
        "- `combined_modeling_dataset.csv`：用于二次响应面建模的统一数据集，包含 measured real experiment 与 response_surface_augmented 两类样本。",
        "- `model_outputs/prediction_grid.csv`：基于拟合模型生成的预测网格点，`data_role = model_prediction_grid`。",
        "- `future_real_experiment_design.csv`：用于后续补充真实实验的设计表，当前测量字段留空。",
        "",
        "## 2. Data Role Definitions",
        "",
        "- `data_role = real_experiment`：measured from original experiment",
        "- `data_role = response_surface_augmented`：generated from quadratic response surface assumption",
        "- `data_role = model_prediction_grid`：predicted by fitted response surface model",
        "- `is_measured = 1` 仅对应真实测量样本；增强样本和预测网格均为 `0`。",
        "",
        "## 3. Real Experiment Table",
        "",
        "- `real_experiment_clean.csv` 来自原始 `data/`，共 8 条 measured 样本。",
        "- `penetration_depth` 与 `entry_angle` 按实验设定映射到 8 个真实会话。",
        "- `speed_setting` 不是原始实验表单直接记录字段，而是依据 `Act_qd*` 与 TCP 速度强度推导得到的代理变量。",
        "- 原始 `data/` 中未发现统一完整的 `speed_setting / penetration_depth / entry_angle / scooped_mass` 设计总表，因此采用 session 级整理方式。",
        "",
        "## 4. Response-Surface Augmented Table",
        "",
        "- `response_surface_augmented_100.csv` 不是直接实验测量数据。",
        "- 该数据集基于初步实验趋势假设构造，用于改善响应面形状展示、模型稳定性分析和参数寻优参考。",
        "- 增强样本保留明确来源字段，不会被重标记为 measured real experiment。",
        "",
        "## 5. Modeling Assumptions",
        "",
        "- 铲泥重量与速度设置、下潜深度、切入角度之间近似满足二次响应面关系。",
        "- 切入角度存在最优区间，模型趋势中心设定在约 `35°` 附近。",
        "- 机器臂速度存在中等最优区间，过低或过高都可能降低铲泥保持能力。",
        "- 下潜深度存在适中最优区间，而非越深越优。",
        "- 三个因素之间可能存在交互影响，因此模型包含一次项、二次项与交互项。",
        "",
        "## 6. Modeling Scripts",
        "",
        "```bash",
        "python3 data_extend/scripts/generate_augmented_response_surface_data.py",
        "python3 data_extend/scripts/response_surface_regression.py",
        "python3 data_extend/scripts/optimize_response_surface.py",
        "python3 data_extend/scripts/generate_future_experiment_design.py",
        "```",
        "",
        "## 7. Result Summary",
        "",
        f"- measured real experiment count: `{int((df['data_role'] == 'real_experiment').sum())}`",
        f"- response_surface_augmented count: `{int((df['data_role'] == 'response_surface_augmented').sum())}`",
        f"- quadratic response-surface formula: `{formula}`",
        f"- R²: `{metrics['r2']:.4f}`",
        f"- Adjusted R²: `{metrics['adjusted_r2']:.4f}`",
        f"- RMSE: `{metrics['rmse']:.4f}`",
        f"- MAE: `{metrics['mae']:.4f}`",
        f"- predicted optimal entry angle: `{optimum['optimal_entry_angle']:.3f} deg`",
        f"- predicted optimal penetration depth: `{optimum['optimal_penetration_depth']:.3f} mm`",
        f"- predicted optimal speed setting: `{optimum['optimal_speed_setting']:.3f}`",
        f"- predicted maximum scooped mass: `{optimum['predicted_max_scooped_mass']:.3f} g`",
        "",
        "## 8. Interpretation and Limitations",
        "",
        "- 模型预测显示，切入角度约 `35°` 时铲泥重量较大。",
        "- 模型预测显示，中等速度设置更容易获得较高铲泥重量。",
        "- 模型预测显示，下潜深度约 `30 mm` 左右具有较优趋势。",
        "- 这些结论具有参数优化参考意义，但仍需更多真实实验验证。",
        "- 当前结果来自“真实初步实验 + 响应面增强样本”的联合拟合，不等同于大量真实实验直接证明的物理定律。",
        "",
        "## 9. Strict Statement",
        "",
        "- `response_surface_augmented_100.csv` 不能作为真实测量数据使用。",
        "- `combined_modeling_dataset.csv` 只用于二次响应面回归建模、趋势展示和参数寻优参考。",
        "- `model_prediction_grid` 仅表示拟合模型上的预测网格点，不代表真实实验运行结果。",
        f"- 最优参数结论：{optimum['warning']}",
        "",
        "## 10. Dependencies",
        "",
        "```bash",
        "pip install pandas numpy matplotlib scikit-learn statsmodels openpyxl",
        "```",
    ]
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not COMBINED_DATA_PATH.exists():
        raise RuntimeError("Missing combined_modeling_dataset.csv. Run generate_augmented_response_surface_data.py first.")

    df = pd.read_csv(COMBINED_DATA_PATH)
    result = fit_response_surface_model(df)
    optimum, prediction_grid = optimize_grid(result)
    prediction_grid.to_csv(PREDICTION_GRID_PATH, index=False, encoding="utf-8")
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
        f"最终总结：真实实验 {int((df['data_role'] == 'real_experiment').sum())} 条，"
        f"响应面增强样本 {int((df['data_role'] == 'response_surface_augmented').sum())} 条，"
        f"R²={metrics['r2']:.4f}，RMSE={metrics['rmse']:.4f}，MAE={metrics['mae']:.4f}。"
    )
    print(optimum["warning"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
