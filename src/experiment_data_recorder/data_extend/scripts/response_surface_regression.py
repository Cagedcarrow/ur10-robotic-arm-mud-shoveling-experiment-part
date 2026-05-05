#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib import font_manager
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_EXTEND_ROOT = Path(__file__).resolve().parents[1]
PLOTS_DIR = DATA_EXTEND_ROOT / "plots"
MODEL_DIR = DATA_EXTEND_ROOT / "model_outputs"
COMBINED_DATA_PATH = DATA_EXTEND_ROOT / "combined_modeling_dataset.csv"

METRICS_PATH = MODEL_DIR / "response_surface_model_metrics.json"
COEF_PATH = MODEL_DIR / "response_surface_coefficients.csv"
TERM_PATH = MODEL_DIR / "term_importance.csv"
SUMMARY_PATH = MODEL_DIR / "fitted_model_summary.txt"
REAL_SCATTER_PATH = PLOTS_DIR / "real_experiment_scatter.png"
AUGMENTED_DIST_PATH = PLOTS_DIR / "augmented_data_distribution.png"
PREDICTED_OBSERVED_PATH = PLOTS_DIR / "predicted_vs_observed.png"
RESIDUAL_PATH = PLOTS_DIR / "residual_analysis.png"
SENSITIVITY_PATH = PLOTS_DIR / "factor_sensitivity.png"

CHINESE_FONT_PATH = Path("/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf")
CHINESE_FONT_NAME = "AR PL SungtiL GB"

FEATURES = ["speed_setting", "penetration_depth", "entry_angle"]
TARGET = "scooped_mass"


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def setup_matplotlib() -> bool:
    if CHINESE_FONT_PATH.exists():
        font_manager.fontManager.addfont(str(CHINESE_FONT_PATH))
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [CHINESE_FONT_NAME, "DejaVu Sans", "Arial"]
        chinese_ok = True
    else:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        chinese_ok = False
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.size"] = 12
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.linewidth"] = 1.4
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["axes.unicode_minus"] = False
    return chinese_ok


def label(zh: str, en: str, chinese_ok: bool) -> str:
    return zh if chinese_ok else en


def load_combined_data() -> pd.DataFrame:
    if not COMBINED_DATA_PATH.exists():
        raise RuntimeError(f"Missing dataset: {COMBINED_DATA_PATH}. Run generate_augmented_response_surface_data.py first.")
    df = pd.read_csv(COMBINED_DATA_PATH)
    required = FEATURES + [TARGET, "data_role", "source_description", "is_measured"]
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required fields in combined dataset: {missing}")
    return df


def classify_term(term: str) -> str:
    if "^2" in term:
        return "quadratic"
    if " " in term:
        return "interaction"
    return "linear"


def fit_response_surface_model(df: pd.DataFrame) -> dict[str, object]:
    X = df[FEATURES].to_numpy(dtype=float)
    y = df[TARGET].to_numpy(dtype=float)

    poly = PolynomialFeatures(degree=2, include_bias=False)
    X_poly = poly.fit_transform(X)
    feature_names = poly.get_feature_names_out(FEATURES)

    linreg = LinearRegression()
    linreg.fit(X_poly, y)
    pred = linreg.predict(X_poly)

    n = len(df)
    p = X_poly.shape[1]
    r2 = r2_score(y, pred)
    adjusted_r2 = 1.0 - (1.0 - r2) * (n - 1) / max(n - p - 1, 1)
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    mae = float(mean_absolute_error(y, pred))

    X_sm = sm.add_constant(X_poly, has_constant="add")
    ols_model = sm.OLS(y, X_sm).fit()

    metrics = {
        "model_type": "quadratic_response_surface_regression",
        "data_basis": "8 measured real experiments + 100 response_surface_augmented samples",
        "n_samples": int(n),
        "n_real_experiment": int((df["data_role"] == "real_experiment").sum()),
        "n_response_surface_augmented": int((df["data_role"] == "response_surface_augmented").sum()),
        "r2": float(r2),
        "adjusted_r2": float(adjusted_r2),
        "rmse": rmse,
        "mae": mae,
        "intercept": float(linreg.intercept_),
    }

    return {
        "dataframe": df,
        "X": X,
        "y": y,
        "pred": pred,
        "poly": poly,
        "feature_names": feature_names,
        "linreg": linreg,
        "ols_model": ols_model,
        "metrics": metrics,
    }


def build_formula(intercept: float, feature_names: np.ndarray, coef: np.ndarray) -> str:
    terms = [f"{intercept:.6f}"]
    for name, value in zip(feature_names, coef):
        sign = "+" if value >= 0 else "-"
        pretty_name = name.replace(" ", " * ").replace("^2", "²")
        terms.append(f" {sign} {abs(value):.6f} * {pretty_name}")
    return "scooped_mass = " + "".join(terms)


def write_model_outputs(result: dict[str, object]) -> None:
    metrics = result["metrics"]
    feature_names = result["feature_names"]
    linreg = result["linreg"]
    ols_model = result["ols_model"]
    X_poly = result["poly"].fit_transform(result["X"])

    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    coef_df = pd.DataFrame(
        {
            "term": feature_names,
            "term_type": [classify_term(term) for term in feature_names],
            "coefficient": linreg.coef_,
            "direction": np.where(linreg.coef_ > 0, "positive", np.where(linreg.coef_ < 0, "negative", "neutral")),
        }
    )
    coef_df.to_csv(COEF_PATH, index=False, encoding="utf-8")

    conf = ols_model.conf_int()
    term_df = pd.DataFrame(
        {
            "term": ["const"] + feature_names.tolist(),
            "term_type": ["intercept"] + [classify_term(term) for term in feature_names],
            "coefficient": ols_model.params,
            "p_value": ols_model.pvalues,
            "ci_low": conf[:, 0],
            "ci_high": conf[:, 1],
            "abs_standardized_effect": [math.nan] + list(np.abs(ols_model.params[1:] * np.nanstd(X_poly, axis=0))),
        }
    )
    term_df.to_csv(TERM_PATH, index=False, encoding="utf-8")


def make_surface_prediction(
    result: dict[str, object],
    fixed_name: str,
    fixed_value: float,
    x_name: str,
    y_name: str,
    x_grid: np.ndarray,
    y_grid: np.ndarray,
) -> np.ndarray:
    grid_x, grid_y = np.meshgrid(x_grid, y_grid)
    defaults = {
        "speed_setting": 0.55,
        "penetration_depth": 30.0,
        "entry_angle": 35.0,
    }
    defaults[fixed_name] = fixed_value
    data = {name: np.full(grid_x.shape, defaults[name], dtype=float) for name in FEATURES}
    data[x_name] = grid_x
    data[y_name] = grid_y
    flat = np.column_stack([data[name].ravel() for name in FEATURES])
    pred = result["linreg"].predict(result["poly"].transform(flat))
    return pred.reshape(grid_x.shape)


def plot_real_experiment_scatter(df: pd.DataFrame, chinese_ok: bool) -> None:
    real_df = df[df["data_role"] == "real_experiment"].copy()
    fig = plt.figure(figsize=(8.4, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        real_df["entry_angle"],
        real_df["penetration_depth"],
        real_df["scooped_mass"],
        c=real_df["speed_setting"],
        cmap="viridis",
        marker="o",
        s=85,
        edgecolor="black",
        label=label("真实实验样本", "Measured real experiment", chinese_ok),
    )
    ax.set_xlabel("entry_angle (deg)")
    ax.set_ylabel("penetration_depth (mm)")
    ax.set_zlabel("scooped_mass (g)")
    ax.set_title(label("真实实验样本分布", "Measured real experiment samples", chinese_ok))
    fig.colorbar(sc, ax=ax, pad=0.08, label="speed_setting")
    ax.legend(loc="upper left")
    fig.savefig(REAL_SCATTER_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_augmented_distribution(df: pd.DataFrame, chinese_ok: bool) -> None:
    aug_df = df[df["data_role"] == "response_surface_augmented"].copy()
    fig = plt.figure(figsize=(8.4, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        aug_df["speed_setting"],
        aug_df["penetration_depth"],
        aug_df["entry_angle"],
        c=aug_df["scooped_mass"],
        cmap="plasma",
        marker="^",
        s=28,
        alpha=0.75,
        edgecolor="none",
        label=label("响应面增强样本", "Response-surface augmented", chinese_ok),
    )
    ax.set_xlabel("speed_setting")
    ax.set_ylabel("penetration_depth (mm)")
    ax.set_zlabel("entry_angle (deg)")
    ax.set_title(label("响应面增强样本覆盖", "Augmented design-space coverage", chinese_ok))
    fig.colorbar(sc, ax=ax, pad=0.08, label="scooped_mass (g)")
    ax.legend(loc="upper left")
    fig.savefig(AUGMENTED_DIST_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_surface(
    df: pd.DataFrame,
    result: dict[str, object],
    fixed_name: str,
    fixed_value: float,
    x_name: str,
    y_name: str,
    output_name: str,
    chinese_ok: bool,
) -> None:
    fig = plt.figure(figsize=(8.8, 6.8))
    ax = fig.add_subplot(111, projection="3d")
    x_grid = np.linspace(df[x_name].min(), df[x_name].max(), 50)
    y_grid = np.linspace(df[y_name].min(), df[y_name].max(), 50)
    zz = make_surface_prediction(result, fixed_name, fixed_value, x_name, y_name, x_grid, y_grid)
    xx, yy = np.meshgrid(x_grid, y_grid)
    ax.plot_surface(xx, yy, zz, cmap="viridis", alpha=0.76, linewidth=0, antialiased=True)

    real_df = df[df["data_role"] == "real_experiment"]
    aug_df = df[df["data_role"] == "response_surface_augmented"]
    ax.scatter(real_df[x_name], real_df[y_name], real_df[TARGET], c="#D55E00", marker="o", s=62, edgecolor="black", label="measured real experiment")
    ax.scatter(aug_df[x_name], aug_df[y_name], aug_df[TARGET], c="#0072B2", marker="^", s=22, alpha=0.35, label="response_surface_augmented")
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_zlabel("scooped_mass (g)")
    ax.set_title(label("模型预测响应面", "Fitted response surface", chinese_ok))
    ax.legend(loc="upper left")
    fig.savefig(PLOTS_DIR / output_name, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_predicted_vs_observed(df: pd.DataFrame, pred: np.ndarray, chinese_ok: bool) -> None:
    fig, ax = plt.subplots(figsize=(7.3, 6.0))
    styles = {
        "real_experiment": {"color": "#D55E00", "marker": "o", "label": "measured real experiment", "size": 60, "edgecolor": "black", "alpha": 0.9},
        "response_surface_augmented": {"color": "#0072B2", "marker": "^", "label": "response_surface_augmented", "size": 32, "edgecolor": "none", "alpha": 0.55},
    }
    for role, style in styles.items():
        mask = df["data_role"] == role
        ax.scatter(
            df.loc[mask, TARGET],
            pred[mask.to_numpy()],
            c=style["color"],
            marker=style["marker"],
            s=style["size"],
            edgecolor=style["edgecolor"],
            alpha=style["alpha"],
            label=style["label"],
        )
    bounds = [float(min(df[TARGET].min(), pred.min())), float(max(df[TARGET].max(), pred.max()))]
    ax.plot(bounds, bounds, "--", color="black", lw=1.2)
    ax.set_xlabel(label("观测 scooped_mass (g)", "Observed scooped_mass (g)", chinese_ok))
    ax.set_ylabel(label("预测 scooped_mass (g)", "Predicted scooped_mass (g)", chinese_ok))
    ax.set_title(label("预测值与观测值", "Predicted vs observed", chinese_ok))
    ax.legend()
    fig.savefig(PREDICTED_OBSERVED_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_residual_analysis(df: pd.DataFrame, pred: np.ndarray, chinese_ok: bool) -> None:
    residual = df[TARGET].to_numpy(dtype=float) - pred
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.8))
    axes[0].hist(residual, bins=20, color="#4C72B0", alpha=0.8, edgecolor="black")
    axes[0].set_xlabel(label("残差", "Residual", chinese_ok))
    axes[0].set_ylabel(label("频数", "Count", chinese_ok))
    axes[0].set_title(label("残差分布", "Residual distribution", chinese_ok))

    role_colors = np.where(df["data_role"] == "real_experiment", "#D55E00", "#0072B2")
    axes[1].scatter(pred, residual, c=role_colors, s=np.where(df["data_role"] == "real_experiment", 55, 24), alpha=0.65)
    axes[1].axhline(0.0, color="black", lw=1.0, ls="--")
    axes[1].set_xlabel(label("预测值", "Predicted", chinese_ok))
    axes[1].set_ylabel(label("残差", "Residual", chinese_ok))
    axes[1].set_title(label("残差与预测值", "Residual vs predicted", chinese_ok))
    fig.savefig(RESIDUAL_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_factor_sensitivity(result: dict[str, object], df: pd.DataFrame, chinese_ok: bool) -> dict[str, float]:
    grids = {
        "speed_setting": np.linspace(0.2, 1.0, 140),
        "penetration_depth": np.linspace(20.0, 40.0, 140),
        "entry_angle": np.linspace(20.0, 60.0, 140),
    }
    fixed = {
        "speed_setting": {"penetration_depth": 30.0, "entry_angle": 35.0},
        "penetration_depth": {"speed_setting": 0.55, "entry_angle": 35.0},
        "entry_angle": {"speed_setting": 0.55, "penetration_depth": 30.0},
    }

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.8))
    peaks: dict[str, float] = {}
    for ax, feature in zip(axes, FEATURES):
        grid = grids[feature]
        frame = pd.DataFrame(
            {
                "speed_setting": np.full_like(grid, fixed.get(feature, {}).get("speed_setting", 0.55), dtype=float),
                "penetration_depth": np.full_like(grid, fixed.get(feature, {}).get("penetration_depth", 30.0), dtype=float),
                "entry_angle": np.full_like(grid, fixed.get(feature, {}).get("entry_angle", 35.0), dtype=float),
            }
        )
        frame[feature] = grid
        pred = result["linreg"].predict(result["poly"].transform(frame[FEATURES].to_numpy(dtype=float)))
        peaks[feature] = float(grid[int(np.argmax(pred))])
        ax.plot(grid, pred, color="#3E6B8A", lw=2.0)
        ax.set_xlabel(feature)
        ax.set_ylabel("predicted scooped_mass (g)")
        ax.set_title(label("单因素敏感性", "One-factor sensitivity", chinese_ok))
    fig.savefig(SENSITIVITY_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return peaks


def build_interpretation(result: dict[str, object], sensitivity_peaks: dict[str, float]) -> str:
    metrics = result["metrics"]
    coef_map = dict(zip(result["feature_names"], result["linreg"].coef_))
    angle_peak = sensitivity_peaks["entry_angle"]
    depth_peak = sensitivity_peaks["penetration_depth"]
    speed_peak = sensitivity_peaks["speed_setting"]
    lines = [
        "二次响应面回归模型说明",
        "",
        "本模型基于 8 条 measured 真实实验样本与 100 条 response_surface_augmented 增强样本联合建立，主要用于趋势拟合、响应面展示、模型稳定性分析与参数寻优参考，不等同于纯真实实验验证结论。",
        "",
        "之所以采用二次响应面回归，是因为本研究关注的三个控制变量——机器臂速度设置、铲子下潜深度与切入角度——都可能表现出非线性和中间最优效应。二次响应面模型能够同时表达一次项、二次项与交互项，在当前小样本真实实验基础上，比单纯线性模型更适合描述“过低不足、过高损失、中间最优”的趋势结构。",
        "",
        f"模型拟合指标为：R² = {metrics['r2']:.4f}，Adjusted R² = {metrics['adjusted_r2']:.4f}，RMSE = {metrics['rmse']:.4f}，MAE = {metrics['mae']:.4f}。",
        "",
        f"模型预测显示，切入角度在约 {angle_peak:.2f}° 附近时，预测铲泥重量相对较高。这一趋势说明切入角度过小时可能导致切入不足和有效装载体积偏低，而切入角度过大则可能增强扰动、增加泥体侧向逸散，从而降低最终保持质量。",
        f"模型预测显示，下潜深度在约 {depth_peak:.2f} mm 附近时更有利于获得较高铲泥重量。下潜过浅时，铲体对泥体的切入和携带能力可能不足；下潜过深时，则可能增大阻力、扰动和回撤损失，因此存在适中的最优区间。",
        f"模型预测显示，速度设置在约 {speed_peak:.3f} 附近时更容易获得较高铲泥重量。速度过低可能削弱切入与装载效率，速度过高则可能产生甩泥、扰动增强或装载保持不稳定现象，因此中等速度具有参数优化参考意义。",
        "",
        "交互项进一步表明三个因素之间并非相互独立。速度与下潜深度共同影响切入稳定性与泥体保持能力，速度与切入角度之间存在运动节奏和姿态耦合，而下潜深度与切入角度共同决定铲体-泥体接触几何。当前交互趋势具有一定参考意义，但仍需更多真实实验验证。",
        "",
        "主要模型项方向如下：",
    ]
    ordered_terms = [
        "speed_setting",
        "penetration_depth",
        "entry_angle",
        "speed_setting^2",
        "penetration_depth^2",
        "entry_angle^2",
        "speed_setting penetration_depth",
        "speed_setting entry_angle",
        "penetration_depth entry_angle",
    ]
    for term in ordered_terms:
        if term in coef_map:
            direction = "正向" if coef_map[term] > 0 else "负向"
            lines.append(f"- {term}: {direction}（系数 {coef_map[term]:.6f}）")

    lines.extend(
        [
            "",
            "模型局限性：",
            "- 真实 measured 样本仅 8 条，增强样本用于稳住响应面形状，但不能替代新的真实测量。",
            "- speed_setting 为由 Act_qd* 与 TCP 速度强度推导的代理变量，不是实验表单直接记录值。",
            "- 因此当前最优参数组合应理解为模型预测结果，而非已被真实实验充分证明的最终工艺参数。",
            "",
            "完整 statsmodels 回归摘要如下：",
            "",
            str(result["ols_model"].summary()),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ensure_dirs()
    chinese_ok = setup_matplotlib()
    df = load_combined_data()
    result = fit_response_surface_model(df)
    write_model_outputs(result)

    plot_real_experiment_scatter(df, chinese_ok)
    plot_augmented_distribution(df, chinese_ok)
    plot_surface(df, result, fixed_name="speed_setting", fixed_value=0.55, x_name="entry_angle", y_name="penetration_depth", output_name="response_surface_angle_depth.png", chinese_ok=chinese_ok)
    plot_surface(df, result, fixed_name="penetration_depth", fixed_value=30.0, x_name="entry_angle", y_name="speed_setting", output_name="response_surface_angle_speed.png", chinese_ok=chinese_ok)
    plot_surface(df, result, fixed_name="entry_angle", fixed_value=35.0, x_name="penetration_depth", y_name="speed_setting", output_name="response_surface_depth_speed.png", chinese_ok=chinese_ok)
    plot_predicted_vs_observed(df, result["pred"], chinese_ok)
    plot_residual_analysis(df, result["pred"], chinese_ok)
    sensitivity_peaks = plot_factor_sensitivity(result, df, chinese_ok)

    formula = build_formula(result["metrics"]["intercept"], result["feature_names"], result["linreg"].coef_)
    SUMMARY_PATH.write_text(formula + "\n\n" + build_interpretation(result, sensitivity_peaks), encoding="utf-8")

    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(formula)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
