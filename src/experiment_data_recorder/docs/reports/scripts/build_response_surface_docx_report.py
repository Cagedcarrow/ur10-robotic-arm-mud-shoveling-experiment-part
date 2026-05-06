#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[3]
REPORT_ROOT = ROOT / "docs" / "reports"
ASSET_DIR = REPORT_ROOT / "assets" / "response_surface_report_cn"
SCRIPT_DIR = REPORT_ROOT / "scripts"

DATA_EXTEND = ROOT / "data_extend"
PROV_PATH = DATA_EXTEND / "combined_modeling_dataset_provenance.csv"
OPT_PATH = DATA_EXTEND / "model_outputs" / "predicted_optimum.json"
METRIC_PATH = DATA_EXTEND / "model_outputs" / "response_surface_model_metrics.json"
COEF_PATH = DATA_EXTEND / "model_outputs" / "response_surface_coefficients.csv"

OUT_MD = REPORT_ROOT / "2026-05-06_铲泥实验设计与响应面分析.md"
OUT_DOCX = REPORT_ROOT / "2026-05-06_铲泥实验设计与响应面分析.docx"
OUT_CMD = REPORT_ROOT / "2026-05-06_铲泥实验设计与响应面分析_commands.sh"

FEATURES = ["speed_setting", "penetration_depth", "entry_angle"]
TARGET = "scooped_mass"


def ensure_dirs() -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)


def setup_matplotlib() -> None:
    zh_font = Path("/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf")
    if zh_font.exists():
        from matplotlib import font_manager

        font_manager.fontManager.addfont(str(zh_font))
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["AR PL SungtiL GB", "SimHei", "DejaVu Sans", "Arial"]
    else:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.size"] = 12
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.linewidth"] = 1.4
    plt.rcParams["legend.frameon"] = False


def load_inputs():
    df = pd.read_csv(PROV_PATH)
    opt = json.loads(OPT_PATH.read_text(encoding="utf-8"))
    metrics = json.loads(METRIC_PATH.read_text(encoding="utf-8"))
    coef_df = pd.read_csv(COEF_PATH)
    coef_map = dict(zip(coef_df["term"], coef_df["coefficient"]))
    return df, opt, metrics, coef_map


def predict_mass(speed: np.ndarray, depth: np.ndarray, angle: np.ndarray, intercept: float, coef: dict[str, float]) -> np.ndarray:
    return (
        intercept
        + coef["speed_setting"] * speed
        + coef["penetration_depth"] * depth
        + coef["entry_angle"] * angle
        + coef["speed_setting^2"] * speed**2
        + coef["penetration_depth^2"] * depth**2
        + coef["entry_angle^2"] * angle**2
        + coef["speed_setting penetration_depth"] * speed * depth
        + coef["speed_setting entry_angle"] * speed * angle
        + coef["penetration_depth entry_angle"] * depth * angle
    )


def fig_path(name: str) -> Path:
    return ASSET_DIR / name


def save_fig(fig: plt.Figure, name: str) -> None:
    fig.savefig(fig_path(name + ".png"), dpi=320, bbox_inches="tight")
    fig.savefig(fig_path(name + ".svg"), bbox_inches="tight")
    plt.close(fig)


def draw_figures(df: pd.DataFrame, opt: dict, metrics: dict, coef_map: dict[str, float]) -> list[tuple[str, str]]:
    real = df[df["data_role"] == "real_experiment"].copy()
    aug = df[df["data_role"] == "response_surface_augmented"].copy()
    intercept = float(metrics["intercept"])

    figure_items: list[tuple[str, str]] = []

    # 图1：样本构成散点
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    pairs = [
        ("entry_angle", "penetration_depth", "切入角度 (deg)", "下潜深度 (mm)"),
        ("entry_angle", "speed_setting", "切入角度 (deg)", "速度代理变量"),
        ("penetration_depth", "speed_setting", "下潜深度 (mm)", "速度代理变量"),
    ]
    for ax, (x, y, xl, yl) in zip(axes, pairs):
        ax.scatter(aug[x], aug[y], c="#8FB9E2", s=28, alpha=0.55, marker="^", label="增强样本 (n=92)")
        ax.scatter(real[x], real[y], c="#D95F02", s=72, alpha=0.95, marker="o", edgecolor="black", label="真实样本 (n=8)")
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.grid(alpha=0.25)
    axes[0].legend(loc="best")
    fig.suptitle("图1 真实样本与增强样本在设计空间中的分布", fontsize=14)
    save_fig(fig, "fig01_design_space_distribution")
    figure_items.append(("fig01_design_space_distribution.png", "图1 真实样本与增强样本在设计空间中的分布"))

    # 图2：真实样本泥重柱状图
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    plot_real = real.sort_values("session_name")
    ax.bar(plot_real["session_name"], plot_real[TARGET], color="#F4A582", edgecolor="black", linewidth=1.0)
    ax.set_ylabel("估计铲泥质量 (g)")
    ax.set_xlabel("真实实验会话")
    ax.set_title("图2 8条真实实验样本的铲泥质量分布")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)
    save_fig(fig, "fig02_real_mass_bar")
    figure_items.append(("fig02_real_mass_bar.png", "图2 8条真实实验样本的铲泥质量分布"))

    def contour_plot(x_name, y_name, fixed_name, fixed_val, title, out_name, x_label, y_label):
        x_min, x_max = float(df[x_name].min()), float(df[x_name].max())
        y_min, y_max = float(df[y_name].min()), float(df[y_name].max())
        xs = np.linspace(x_min, x_max, 160)
        ys = np.linspace(y_min, y_max, 160)
        xx, yy = np.meshgrid(xs, ys)
        speed = np.full_like(xx, float(opt["optimal_speed_setting"]))
        depth = np.full_like(xx, float(opt["optimal_penetration_depth"]))
        angle = np.full_like(xx, float(opt["optimal_entry_angle"]))
        mapping = {"speed_setting": speed, "penetration_depth": depth, "entry_angle": angle}
        mapping[x_name] = xx
        mapping[y_name] = yy
        mapping[fixed_name] = np.full_like(xx, fixed_val)
        zz = predict_mass(mapping["speed_setting"], mapping["penetration_depth"], mapping["entry_angle"], intercept, coef_map)

        fig, ax = plt.subplots(figsize=(6.8, 5.6))
        cf = ax.contourf(xx, yy, zz, levels=18, cmap="viridis")
        cbar = fig.colorbar(cf, ax=ax)
        cbar.set_label("预测铲泥质量 (g)")
        ax.scatter(real[x_name], real[y_name], c="#D95F02", s=48, marker="o", edgecolor="black", label="真实样本")
        ax.scatter(aug[x_name], aug[y_name], c="#8FB9E2", s=18, marker="^", alpha=0.45, label="增强样本")
        ax.scatter([float(opt[f"optimal_{x_name}"])], [float(opt[f"optimal_{y_name}"])], c="red", s=120, marker="*", label="最优点")
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(title)
        ax.legend(loc="best")
        ax.grid(alpha=0.2)
        save_fig(fig, out_name)

    contour_plot(
        "entry_angle",
        "penetration_depth",
        "speed_setting",
        float(opt["optimal_speed_setting"]),
        "图3 固定最优速度时的角度-深度响应面等值图",
        "fig03_contour_angle_depth",
        "切入角度 (deg)",
        "下潜深度 (mm)",
    )
    figure_items.append(("fig03_contour_angle_depth.png", "图3 固定最优速度时的角度-深度响应面等值图"))

    contour_plot(
        "entry_angle",
        "speed_setting",
        "penetration_depth",
        float(opt["optimal_penetration_depth"]),
        "图4 固定最优深度时的角度-速度响应面等值图",
        "fig04_contour_angle_speed",
        "切入角度 (deg)",
        "速度代理变量",
    )
    figure_items.append(("fig04_contour_angle_speed.png", "图4 固定最优深度时的角度-速度响应面等值图"))

    contour_plot(
        "penetration_depth",
        "speed_setting",
        "entry_angle",
        float(opt["optimal_entry_angle"]),
        "图5 固定最优角度时的深度-速度响应面等值图",
        "fig05_contour_depth_speed",
        "下潜深度 (mm)",
        "速度代理变量",
    )
    figure_items.append(("fig05_contour_depth_speed.png", "图5 固定最优角度时的深度-速度响应面等值图"))

    # 图6：预测值 vs 观测值
    y = df[TARGET].to_numpy(dtype=float)
    pred = predict_mass(
        df["speed_setting"].to_numpy(dtype=float),
        df["penetration_depth"].to_numpy(dtype=float),
        df["entry_angle"].to_numpy(dtype=float),
        intercept,
        coef_map,
    )
    fig, ax = plt.subplots(figsize=(6.8, 6.0))
    m_real = df["data_role"] == "real_experiment"
    m_aug = df["data_role"] == "response_surface_augmented"
    ax.scatter(y[m_aug], pred[m_aug], c="#8FB9E2", marker="^", s=26, alpha=0.5, label="增强样本")
    ax.scatter(y[m_real], pred[m_real], c="#D95F02", marker="o", s=80, edgecolor="black", label="真实样本")
    low = float(min(y.min(), pred.min()))
    high = float(max(y.max(), pred.max()))
    ax.plot([low, high], [low, high], "k--", lw=1.2, label="理想线 y=x")
    ax.set_xlabel("观测铲泥质量 (g)")
    ax.set_ylabel("模型预测铲泥质量 (g)")
    ax.set_title("图6 模型预测值与观测值对比")
    ax.text(
        0.03,
        0.97,
        f"R²={metrics['r2']:.4f}\nAdjusted R²={metrics['adjusted_r2']:.4f}\nRMSE={metrics['rmse']:.2f}\nMAE={metrics['mae']:.2f}",
        transform=ax.transAxes,
        va="top",
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#666"},
    )
    ax.legend(loc="lower right")
    ax.grid(alpha=0.25)
    save_fig(fig, "fig06_pred_vs_obs")
    figure_items.append(("fig06_pred_vs_obs.png", "图6 模型预测值与观测值对比"))

    # 图7：残差分析
    residual = y - pred
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].hist(residual, bins=18, color="#7FBF7B", alpha=0.85, edgecolor="black")
    axes[0].set_title("图7(a) 残差分布")
    axes[0].set_xlabel("残差 (g)")
    axes[0].set_ylabel("频数")
    axes[0].grid(alpha=0.2)

    axes[1].scatter(pred[m_aug], residual[m_aug], c="#8FB9E2", s=22, alpha=0.55, marker="^")
    axes[1].scatter(pred[m_real], residual[m_real], c="#D95F02", s=70, edgecolor="black", marker="o")
    axes[1].axhline(0, color="black", linestyle="--", lw=1.1)
    axes[1].set_title("图7(b) 残差-预测值关系")
    axes[1].set_xlabel("预测铲泥质量 (g)")
    axes[1].set_ylabel("残差 (g)")
    axes[1].grid(alpha=0.2)
    save_fig(fig, "fig07_residual")
    figure_items.append(("fig07_residual.png", "图7 残差分布与残差-预测值关系"))

    # 图8：单因素敏感性
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    default = {
        "speed_setting": float(opt["optimal_speed_setting"]),
        "penetration_depth": float(opt["optimal_penetration_depth"]),
        "entry_angle": float(opt["optimal_entry_angle"]),
    }
    grids = {
        "speed_setting": np.linspace(0.2, 1.0, 180),
        "penetration_depth": np.linspace(20.0, 40.0, 180),
        "entry_angle": np.linspace(20.0, 60.0, 180),
    }
    labels = {
        "speed_setting": "速度代理变量",
        "penetration_depth": "下潜深度 (mm)",
        "entry_angle": "切入角度 (deg)",
    }
    for ax, feature in zip(axes, FEATURES):
        base_speed = np.full_like(grids[feature], default["speed_setting"], dtype=float)
        base_depth = np.full_like(grids[feature], default["penetration_depth"], dtype=float)
        base_angle = np.full_like(grids[feature], default["entry_angle"], dtype=float)
        if feature == "speed_setting":
            base_speed = grids[feature]
        elif feature == "penetration_depth":
            base_depth = grids[feature]
        else:
            base_angle = grids[feature]
        pv = predict_mass(base_speed, base_depth, base_angle, intercept, coef_map)
        ax.plot(grids[feature], pv, color="#2C7FB8", lw=2.2)
        ax.set_xlabel(labels[feature])
        ax.set_ylabel("预测铲泥质量 (g)")
        ax.set_title(f"{labels[feature]}敏感性")
        ax.grid(alpha=0.25)
    fig.suptitle("图8 单因素敏感性分析（其余变量固定在最优点）", fontsize=14)
    save_fig(fig, "fig08_sensitivity")
    figure_items.append(("fig08_sensitivity.png", "图8 单因素敏感性分析"))

    # 图9：最优点邻域热力图（角度-深度）
    a = np.linspace(28.0, 40.0, 160)
    d = np.linspace(25.0, 36.0, 160)
    aa, dd = np.meshgrid(a, d)
    ss = np.full_like(aa, float(opt["optimal_speed_setting"]))
    zz = predict_mass(ss, dd, aa, intercept, coef_map)
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    im = ax.imshow(
        zz,
        origin="lower",
        extent=[a.min(), a.max(), d.min(), d.max()],
        aspect="auto",
        cmap="YlOrRd",
    )
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("预测铲泥质量 (g)")
    ax.scatter([float(opt["optimal_entry_angle"])], [float(opt["optimal_penetration_depth"])], c="blue", s=120, marker="*", label="最优点")
    ax.set_xlabel("切入角度 (deg)")
    ax.set_ylabel("下潜深度 (mm)")
    ax.set_title("图9 最优点邻域热力图（速度固定）")
    ax.legend(loc="best")
    save_fig(fig, "fig09_optimum_neighborhood")
    figure_items.append(("fig09_optimum_neighborhood.png", "图9 最优点邻域热力图（速度固定）"))

    return figure_items


def build_markdown(metrics: dict, opt: dict, figure_items: list[tuple[str, str]]) -> str:
    figure_md = []
    for rel_name, cap in figure_items:
        rel = f"assets/response_surface_report_cn/{rel_name}"
        figure_md.append(f"![{cap}]({rel})\n\n{cap}。\n")
    figures_block = "\n".join(figure_md)

    return f"""# 基于实验记录系统与二次响应面模型的铲泥参数优化研究

## 摘要

针对机械臂铲泥（scooping）作业中速度、下潜深度与切入角三参数耦合整定效率低且严重依赖操作经验的问题，本文提出了一种融合实验记录系统与二次响应面模型（Quadratic Response Surface Model）的参数优化方法。研究基于 100 组样本构建响应面模型，其中真实物理实验样本 8 组，响应面增强样本 92 组。通过引入二阶项与交互作用项，该模型能够有效表征耦合参数空间中的非线性响应特征与内部驻点（最优值）结构。当前拟合指标为 R²={metrics['r2']:.4f}、Adjusted R²={metrics['adjusted_r2']:.4f}、RMSE={metrics['rmse']:.4f} g、MAE={metrics['mae']:.4f} g。优化结果表明，切入角 {opt['optimal_entry_angle']:.3f}°、下潜深度 {opt['optimal_penetration_depth']:.3f} mm、速度代理变量 {opt['optimal_speed_setting']:.3f} 附近可获得较优响应，预测最大铲泥质量为 {opt['predicted_max_scooped_mass']:.3f} g。研究结论可为后续真实实验的加密采样与在线参数优化提供定量依据。

## 1 引言

机械臂铲泥作业的响应特性受运动学参数与接触力学工况的共同影响，呈现出强耦合、强非线性及显著的阶段性演化特征。若采用单因素遍历策略，不仅易陷入局部最优解，且实验成本随参数维度增加而急剧上升。响应面方法（Response Surface Methodology, RSM）能够在有限样本条件下构建连续映射关系，为多参数寻优提供可解释的数学框架。然而，RSM 对样本数据质量与变量定义的一致性要求较高，若实验记录链路不可追溯或数据语义不一致，模型结果将难以复现。

本文围绕以下三个关键问题展开研究：（1）如何构建稳定且可追溯的实验记录流程；（2）如何在真实样本极其有限（n=8）的条件下保证模型结构的稳健性；（3）如何将模型最优解转化为具有工程可操作性的参数调整窗口。本研究的最终目标并非追求不可变更的单一最优值，而是建立一套”可复核的建模流程 + 可解释的参数区间 + 可迭代更新的实验策略”。

## 2 理论与模型

### 2.1 二次响应面模型的一般形式

设速度代理变量为 $v$，下潜深度为 $d$，切入角度为 $\\theta$，响应变量（铲泥质量）为 $m$。二次响应面模型的一般形式可表示为：

$$
\\hat{{m}}=
\\beta_0+
\\beta_1 v+\\beta_2 d+\\beta_3\\theta+
\\beta_{{11}}v^2+\\beta_{{22}}d^2+\\beta_{{33}}\\theta^2+
\\beta_{{12}}vd+\\beta_{{13}}v\\theta+\\beta_{{23}}d\\theta.
$$

为便于揭示模型的结构特征，其矩阵形式可写为：

$$
\\hat{{m}} = \\mathbf{{x}}^T\\mathbf{{B}}\\mathbf{{x}} + \\mathbf{{b}}^T\\mathbf{{x}} + \\beta_0, \\quad
\\mathbf{{x}}=[v,d,\\theta]^T.
$$

### 2.2 优化目标与约束

本文的参数优化目标定义为：

$$
\\max_{{v,d,\\theta}} \\hat{{m}}(v,d,\\theta)
$$

约束区间为：

$$
v\\in[0.2,1.0],\\quad d\\in[20,40],\\quad \\theta\\in[20,60].
$$

### 2.3 评估指标公式

设观测值为 $m_i$，预测值为 $\\hat{{m}}_i$，样本数为 $n$，模型参数个数为 $p$，则：

$$
R^2 = 1 - \\frac{{\\sum_{{i=1}}^n (m_i-\\hat{{m}}_i)^2}}{{\\sum_{{i=1}}^n (m_i-\\bar{{m}})^2}},
$$
$$
R^2_{{adj}} = 1 - (1-R^2)\\frac{{n-1}}{{n-p-1}},
$$
$$
RMSE = \\sqrt{{\\frac{{1}}{{n}}\\sum_{{i=1}}^n (m_i-\\hat{{m}}_i)^2}},
\\qquad
MAE = \\frac{{1}}{{n}}\\sum_{{i=1}}^n |m_i-\\hat{{m}}_i|.
$$

### 2.4 符号释义与工程含义

| 符号 | 含义 | 单位 |
|---|---|---|
| $v$ | 速度代理变量 | 无量纲 |
| $d$ | 下潜深度 | mm |
| $\\theta$ | 切入角度 | deg |
| $m$ | 铲泥质量 | g |
| $\\beta$ | 回归系数 | - |

线性主效应项表征各因素的独立贡献；二次项捕捉响应曲面上的驻点（极大值、极小值或鞍点）特性；交互项刻画因素间的耦合作用。该模型结构适用于描述铲泥过程中”推进—切入—保持”三阶段协同作用所表现出的非线性响应行为。

## 3 实验设计与数据来源

### 3.1 记录系统与实验流程

实验采用一体化数据采集与记录系统，同步采集机器人的运动学状态、力/力矩信号以及视觉图像流。每次实验作为独立会话（session）执行，包含参数设置、作业执行、稳定称重与会话结束四个阶段。系统在会话级别保存完整的元信息，用于后续追溯与复核。该流程的核心设计原则在于确保运动执行过程、载荷响应信号与视觉记录在统一时间轴上的严格对齐，从而避免跨模态分析中由时序偏移引入的系统误差。

### 3.2 基于物理锚点的实验设计与数据增强策略

研究采用”手动示范锚定 + 自动化增强建模”的组合策略。手动示范提供真实物理锚点，自动化增强用于补足设计空间覆盖。当前模型构建所采用的数据配置如下：真实物理实验样本 8 组，响应面增强样本 92 组，总样本量 100 组。该策略的核心目的在于提升模型的稳定性与可解释性，而非以增强样本替代真实测量结论。

### 3.3 响应变量估计

响应变量（铲泥质量）通过对稳定阶段的力学信号进行差分计算间接估计获得。其基本原理为：在同一实验会话内，计算参考稳定段与最终称重稳定段之间沿重力方向的力差值，以此表征净载荷变化，进而依据力—质量映射关系转换为质量估计值。该差分处理策略能够有效抑制瞬态冲击与局部噪声对质量估算的干扰，使响应变量更准确地反映工艺实际效果。

### 3.4 变量区间

- 速度代理变量：0.2–1.0
- 下潜深度：20–40 mm
- 切入角度：20–60 deg

上述区间同时覆盖真实样本分布与增强样本生成域，用于保证拟合与优化的一致性。

## 4 结果与讨论

{figures_block}

### 4.1 模型拟合结果

当前模型的拟合优度指标如下：R²={metrics['r2']:.4f}，校正 R²={metrics['adjusted_r2']:.4f}，RMSE={metrics['rmse']:.4f} g，MAE={metrics['mae']:.4f} g。
上述结果表明，模型能够较好地解释响应变量的总体变化趋势，可为参数优选提供定量依据。
需要指出的是，误差指标仍体现出一定的离散性，表明该模型应定位为”趋势识别与区间优化工具”，不宜在未验证的条件下外推为任意工况的高精度点预测器。

### 4.2 结果解释（图1–图5）

图 1 和图 2 表明：真实样本为曲面拟合提供了关键的物理锚点，增强样本则显著改善了设计空间的覆盖程度，避免拟合结果过度依赖于有限的离散观测点。
图 3 至图 5 显示：在三个固定切片中，响应曲面均呈现出内部高值区域，而非沿定义域边界单调递增。
值得注意的是，上述结论在当前的变量区间定义下成立；若后续实验扩大参数搜索范围，最优点位置可能发生漂移，因此仍需通过迭代实验加以验证。

### 4.3 误差结构与稳定性（图6–图9）

图 6 表明，预测值与观测值在总体上呈现一致的变化方向，模型能够稳定捕获响应变量的主变化趋势。
图 7 的残差分析显示，残差分布近似集中于零值附近，但仍存在一定程度的拖尾（长尾）现象，提示局部工况下的响应机制尚未被完全解释。
图 8 中的单因素敏感性曲线均呈”先升后降”的形态，图 9 进一步确认最优参数邻域内存在稳定的高响应值区域。
受限于当前样本规模（真实样本 n=8），上述结论仍需通过后续实验加以检验。建议在最优参数邻域内开展重复实验，以评估预测响应的漂移程度与方差特性。

### 4.4 最优参数组合与工程含义

经响应面优化求解得到的最优参数组合如下：

- 切入角度：{opt['optimal_entry_angle']:.3f} deg
- 下潜深度：{opt['optimal_penetration_depth']:.3f} mm
- 速度代理变量：{opt['optimal_speed_setting']:.3f}
- 预测最大铲泥质量：{opt['predicted_max_scooped_mass']:.3f} g

该最优组合体现了三个因素的协同平衡：切入角过小或下潜深度过浅会降低有效装载量；切入角过大或下潜深度过深则会加剧扰动与物料流失；速度代理变量过高会削弱持料稳定性。
必须强调的是，上述最优解应被理解为在当前样本定义域与模型假设下的预测最优值，其工程意义在于为下一轮实验的参数窗口收缩提供可靠方向，而非直接等同于最终工艺标定值。

## 5 局限性与后续研究

尽管本模型已为参数优化提供了明确的定量参考，但仍需在以下方面认识其固有局限：

- 真实物理实验样本仅有 8 组，统计推断的支撑能力仍然有限；
- 增强样本虽有助于稳定模型拟合过程，但不能替代真实物理测量；
- 速度变量为基于关节与 TCP 运动学导出的代理指标，并非控制器原生设定值；
- 在模型定位上，更适合服务于”趋势识别与参数区间优选”，不适宜直接作为高精度单响应预测器使用。

后续研究建议围绕当前最优参数邻域开展加密采样，并设置中心点重复实验以评估重复性误差。每获取一批新的真实实验样本后，应重新拟合模型并比较最优参数点的漂移量，从而逐步提升模型的稳健性与工艺可迁移性。

## 6 结论

本文构建了面向机械臂铲泥任务的二次响应面优化框架，在”实验记录系统—变量定义—模型拟合—参数优选”的完整链路上实现了方法闭环。研究结果表明，切入角、下潜深度与速度代理变量均呈现出显著的驻点（内部最优）特征，且最优区域位于当前设计空间内部而非边界。该发现为后续实验提供了明确的参数窗口化调整方向。考虑到当前真实实验样本量仍然有限，后续工作应通过迭代增量实验持续提升统计稳健性，并进一步检验最优参数点在不同作业条件下的稳定性。

## 附录A 模型关键数值结果汇总

- 样本规模：100（真实 8，增强 92）  
- R²：{metrics['r2']:.4f}  
- Adjusted R²：{metrics['adjusted_r2']:.4f}  
- RMSE：{metrics['rmse']:.4f} g  
- MAE：{metrics['mae']:.4f} g  
- 最优切入角：{opt['optimal_entry_angle']:.3f} deg  
- 最优下潜深度：{opt['optimal_penetration_depth']:.3f} mm  
- 最优速度代理变量：{opt['optimal_speed_setting']:.3f}  
- 预测最大铲泥质量：{opt['predicted_max_scooped_mass']:.3f} g

## 附录B 研究局限性声明

增强样本仅用于提升响应面模型的拟合稳定性与参数寻优分辨率，不能替代真实物理测量的结论。本文报告的所有最优参数均应视作在当前样本定义域与模型假设下的统计预测结果，其有效性有待后续真实实验进一步验证。

"""


def set_style_font(style, latin: str = "Times New Roman", east_asia: str = "宋体", size_pt: float | None = None):
    style.font.name = latin
    style._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    if size_pt is not None:
        style.font.size = Pt(size_pt)


def post_format_docx(path: Path) -> None:
    doc = Document(path)
    section = doc.sections[0]
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)

    style_size_map = {
        "Normal": 12,
        "Heading 1": 16,
        "Heading 2": 14,
        "Heading 3": 13,
        "标题 1": 16,
        "标题 2": 14,
        "标题 3": 13,
    }
    for st in doc.styles:
        if st.name in style_size_map:
            set_style_font(st, latin="Times New Roman", east_asia="宋体", size_pt=style_size_map[st.name])

    for para in doc.paragraphs:
        pf = para.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(6)
        pf.space_before = Pt(0)
        for run in para.runs:
            run.font.name = "Times New Roman"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    doc.save(path)


def count_omath(path: Path) -> tuple[int, int]:
    with zipfile.ZipFile(path, "r") as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    return xml.count("<m:oMath>"), xml.count("<m:oMathPara>")


def approx_chinese_char_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def build_docx(md_path: Path, docx_path: Path) -> None:
    cmd = [
        "pandoc",
        md_path.name,
        "-f",
        "markdown+tex_math_dollars",
        "-t",
        "docx",
        "-s",
        "--resource-path",
        str(REPORT_ROOT),
        "-o",
        docx_path.name,
    ]
    subprocess.run(cmd, check=True, cwd=REPORT_ROOT)


def main() -> int:
    ensure_dirs()
    setup_matplotlib()
    df, opt, metrics, coef_map = load_inputs()
    figures = draw_figures(df, opt, metrics, coef_map)

    md_text = build_markdown(metrics, opt, figures)
    OUT_MD.write_text(md_text, encoding="utf-8")

    build_docx(OUT_MD, OUT_DOCX)
    post_format_docx(OUT_DOCX)
    omath, omath_para = count_omath(OUT_DOCX)

    cmd_text = """#!/usr/bin/env bash
set -euo pipefail
cd /root/ur10_ws/src/experiment_data_recorder
python3 docs/reports/scripts/build_response_surface_docx_report.py
"""
    OUT_CMD.write_text(cmd_text, encoding="utf-8")
    OUT_CMD.chmod(0o755)

    summary = {
        "output_docx": str(OUT_DOCX),
        "output_markdown": str(OUT_MD),
        "asset_dir": str(ASSET_DIR),
        "figure_count": len(figures),
        "chinese_char_count_markdown": approx_chinese_char_count(md_text),
        "oMath_count": omath,
        "oMathPara_count": omath_para,
        "n_samples": int(metrics["n_samples"]),
        "n_real": int(metrics["n_real_experiment"]),
        "n_aug": int(metrics["n_response_surface_augmented"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
