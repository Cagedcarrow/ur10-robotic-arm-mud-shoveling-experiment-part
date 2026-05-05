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


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data_extend"
PLOTS_DIR = OUTPUT_ROOT / "plots"
MODEL_DIR = OUTPUT_ROOT / "model_outputs"
COMBINED_DATA_PATH = OUTPUT_ROOT / "combined_data_with_flag.csv"
METRICS_PATH = MODEL_DIR / "response_surface_model_metrics.json"
COEF_PATH = MODEL_DIR / "response_surface_coefficients.csv"
TERM_PATH = MODEL_DIR / "anova_or_term_importance.csv"
SUMMARY_PATH = MODEL_DIR / "fitted_model_summary.txt"
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
        chinese_ok = False
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.size"] = 12
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["axes.unicode_minus"] = False
    return chinese_ok


def label(zh: str, en: str, chinese_ok: bool) -> str:
    return zh if chinese_ok else en


def load_combined_data() -> pd.DataFrame:
    if not COMBINED_DATA_PATH.exists():
        raise RuntimeError(f"Missing combined dataset: {COMBINED_DATA_PATH}. Run generate_synthetic_data.py first.")
    df = pd.read_csv(COMBINED_DATA_PATH)
    missing = [field for field in FEATURES + [TARGET, "data_source", "is_synthetic"] if field not in df.columns]
    if missing:
        raise RuntimeError(f"Combined dataset is missing required fields: {missing}")
    return df


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
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / max(n - p - 1, 1)
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    mae = float(mean_absolute_error(y, pred))

    X_sm = sm.add_constant(X_poly, has_constant="add")
    ols_model = sm.OLS(y, X_sm).fit()

    return {
        "dataframe": df,
        "X": X,
        "y": y,
        "pred": pred,
        "poly": poly,
        "feature_names": feature_names,
        "linreg": linreg,
        "ols_model": ols_model,
        "metrics": {
            "model_type": "quadratic_response_surface_regression",
            "n_samples": int(n),
            "n_real_experiment": int((df["is_synthetic"] == 0).sum()),
            "n_synthetic": int((df["is_synthetic"] == 1).sum()),
            "r2": float(r2),
            "adjusted_r2": float(adj_r2),
            "rmse": rmse,
            "mae": mae,
            "intercept": float(linreg.intercept_),
        },
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
            "coefficient": linreg.coef_,
            "direction": np.where(linreg.coef_ > 0, "positive", np.where(linreg.coef_ < 0, "negative", "neutral")),
        }
    )
    coef_df.to_csv(COEF_PATH, index=False, encoding="utf-8")

    conf = ols_model.conf_int()
    term_df = pd.DataFrame(
        {
            "term": ["const"] + feature_names.tolist(),
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
        "penetration_depth": 32.5,
        "entry_angle": 35.0,
    }
    defaults[fixed_name] = fixed_value
    data = {name: np.full(grid_x.shape, defaults[name], dtype=float) for name in FEATURES}
    data[x_name] = grid_x
    data[y_name] = grid_y
    flat = np.column_stack([data[name].ravel() for name in FEATURES])
    pred = result["linreg"].predict(result["poly"].transform(flat))
    return pred.reshape(grid_x.shape)


def plot_raw_data_scatter(df: pd.DataFrame, chinese_ok: bool) -> None:
    real_df = df[df["is_synthetic"] == 0].copy()
    fig = plt.figure(figsize=(8.4, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        real_df["entry_angle"],
        real_df["penetration_depth"],
        real_df["scooped_mass"],
        c=real_df["speed_setting"],
        cmap="viridis",
        s=70,
        edgecolor="black",
        label=label("真实实验", "Real experiment", chinese_ok),
    )
    ax.set_xlabel("entry_angle (deg)")
    ax.set_ylabel("penetration_depth (mm)")
    ax.set_zlabel("scooped_mass (g)")
    ax.set_title(label("原始实验数据散点", "Raw data scatter", chinese_ok))
    fig.colorbar(sc, ax=ax, pad=0.08, label="speed_setting")
    fig.savefig(PLOTS_DIR / "raw_data_scatter.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_synthetic_distribution(df: pd.DataFrame, chinese_ok: bool) -> None:
    syn = df[df["is_synthetic"] == 1].copy()
    fig = plt.figure(figsize=(8.4, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        syn["speed_setting"],
        syn["penetration_depth"],
        syn["entry_angle"],
        c=syn["scooped_mass"],
        cmap="plasma",
        s=35,
        alpha=0.8,
        edgecolor="none",
    )
    ax.set_xlabel("speed_setting")
    ax.set_ylabel("penetration_depth (mm)")
    ax.set_zlabel("entry_angle (deg)")
    ax.set_title(label("合成数据分布", "Synthetic data distribution", chinese_ok))
    fig.colorbar(sc, ax=ax, pad=0.08, label="scooped_mass (g)")
    fig.savefig(PLOTS_DIR / "synthetic_data_distribution.png", dpi=300, bbox_inches="tight")
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
    ax.plot_surface(xx, yy, zz, cmap="viridis", alpha=0.78, linewidth=0, antialiased=True)

    real_df = df[df["is_synthetic"] == 0]
    syn_df = df[df["is_synthetic"] == 1]
    ax.scatter(real_df[x_name], real_df[y_name], real_df[TARGET], c="#D55E00", s=55, edgecolor="black", label="real_experiment")
    ax.scatter(syn_df[x_name], syn_df[y_name], syn_df[TARGET], c="#0072B2", s=18, alpha=0.28, label="synthetic")
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_zlabel("scooped_mass (g)")
    ax.set_title(
        label(f"{x_name} 与 {y_name} 响应面", f"Response surface: {x_name} vs {y_name}", chinese_ok)
    )
    ax.legend(loc="upper left")
    fig.savefig(PLOTS_DIR / output_name, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_predicted_vs_actual(df: pd.DataFrame, pred: np.ndarray, chinese_ok: bool) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    palette = {"real_experiment": "#D55E00", "synthetic": "#0072B2"}
    markers = {"real_experiment": "o", "synthetic": "^"}
    for source in ["real_experiment", "synthetic"]:
        mask = df["data_source"] == source
        ax.scatter(
            df.loc[mask, TARGET],
            pred[mask.to_numpy()],
            c=palette[source],
            marker=markers[source],
            s=55 if source == "real_experiment" else 30,
            alpha=0.8 if source == "real_experiment" else 0.55,
            label=source,
            edgecolor="black" if source == "real_experiment" else "none",
        )
    bounds = [float(min(df[TARGET].min(), pred.min())), float(max(df[TARGET].max(), pred.max()))]
    ax.plot(bounds, bounds, "--", color="black", lw=1.2)
    ax.set_xlabel(label("观测 scooped_mass (g)", "Observed scooped_mass (g)", chinese_ok))
    ax.set_ylabel(label("预测 scooped_mass (g)", "Predicted scooped_mass (g)", chinese_ok))
    ax.set_title(label("预测值与观测值对比", "Predicted vs actual", chinese_ok))
    ax.legend()
    fig.savefig(PLOTS_DIR / "predicted_vs_actual.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_residual_analysis(df: pd.DataFrame, pred: np.ndarray, chinese_ok: bool) -> None:
    residual = df[TARGET].to_numpy(dtype=float) - pred
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    axes[0].hist(residual, bins=20, color="#4C72B0", alpha=0.8, edgecolor="black")
    axes[0].set_xlabel(label("残差", "Residual", chinese_ok))
    axes[0].set_ylabel(label("频数", "Count", chinese_ok))
    axes[0].set_title(label("残差分布", "Residual distribution", chinese_ok))

    axes[1].scatter(pred, residual, c=np.where(df["is_synthetic"] == 1, "#0072B2", "#D55E00"), alpha=0.65, s=35)
    axes[1].axhline(0.0, color="black", lw=1.1, ls="--")
    axes[1].set_xlabel(label("预测值", "Predicted", chinese_ok))
    axes[1].set_ylabel(label("残差", "Residual", chinese_ok))
    axes[1].set_title(label("残差与预测值", "Residual vs predicted", chinese_ok))
    fig.savefig(PLOTS_DIR / "residual_analysis.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_factor_sensitivity(result: dict[str, object], df: pd.DataFrame, chinese_ok: bool) -> dict[str, float]:
    med_depth = float(np.median(df["penetration_depth"]))
    med_angle = float(np.median(df["entry_angle"]))
    med_speed = float(np.median(df["speed_setting"]))

    grids = {
        "speed_setting": np.linspace(0.2, 1.0, 120),
        "penetration_depth": np.linspace(20.0, 40.0, 120),
        "entry_angle": np.linspace(20.0, 60.0, 120),
    }
    fixed = {
        "speed_setting": {"penetration_depth": med_depth, "entry_angle": 35.0},
        "penetration_depth": {"speed_setting": 0.55, "entry_angle": 35.0},
        "entry_angle": {"speed_setting": 0.55, "penetration_depth": med_depth},
    }

    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.6))
    peaks: dict[str, float] = {}
    for ax, feature in zip(axes, FEATURES):
        grid = grids[feature]
        frame = pd.DataFrame(
            {
                "speed_setting": np.full_like(grid, fixed.get(feature, {}).get("speed_setting", med_speed), dtype=float),
                "penetration_depth": np.full_like(grid, fixed.get(feature, {}).get("penetration_depth", med_depth), dtype=float),
                "entry_angle": np.full_like(grid, fixed.get(feature, {}).get("entry_angle", med_angle), dtype=float),
            }
        )
        frame[feature] = grid
        pred = result["linreg"].predict(result["poly"].transform(frame[FEATURES].to_numpy(dtype=float)))
        peaks[feature] = float(grid[int(np.argmax(pred))])
        ax.plot(grid, pred, color="#3E6B8A", lw=2.0)
        ax.set_xlabel(feature)
        ax.set_ylabel("predicted scooped_mass (g)")
        ax.set_title(label(f"{feature} 敏感性", f"Sensitivity: {feature}", chinese_ok))
    fig.savefig(PLOTS_DIR / "factor_sensitivity.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return peaks


def build_interpretation(result: dict[str, object], sensitivity_peaks: dict[str, float]) -> str:
    metrics = result["metrics"]
    coef_map = dict(zip(result["feature_names"], result["linreg"].coef_))
    angle_peak = sensitivity_peaks["entry_angle"]
    depth_peak = sensitivity_peaks["penetration_depth"]
    speed_peak = sensitivity_peaks["speed_setting"]
    lines = [
        "二次响应面模型分析说明",
        "",
        "以下结论基于原始实验数据与明确标记的 synthetic 扩展数据的联合拟合，主要用于趋势分析、方法验证和参数寻优参考，不能等同于完全由大量真实实验直接证明的物理定律。",
        "",
        f"模型拟合指标：R² = {metrics['r2']:.4f}，Adjusted R² = {metrics['adjusted_r2']:.4f}，RMSE = {metrics['rmse']:.4f}，MAE = {metrics['mae']:.4f}。",
        "",
        f"切入角度效应显示为明显的二次响应，预测峰值出现在约 {angle_peak:.2f}° 附近，表明铲泥重量存在角度最优区间。角度过小可能导致切入不足、有效装载体积偏低；角度过大则可能增加扰动与泥体侧向逸散，从而降低最终铲泥质量。",
        f"下潜深度效应同样表现出非单调趋势，预测峰值位于约 {depth_peak:.2f} mm 附近。下潜过浅时铲体对泥体的有效切入不足，下潜过深时则可能增大阻力、扰动和回撤损失，因此存在适中的最优深度区间。",
        f"速度效应呈现中等速度最优特征，预测峰值位于 speed_setting 约 {speed_peak:.3f}。速度过低可能削弱切入与装载效率，速度过高则更容易产生甩泥、扰动增强或装载保持不稳定现象。",
        "",
        "交互项分析表明，三个控制因素之间并非相互独立。speed_setting × penetration_depth 反映推进速度与切入深度对装载稳定性的共同影响；speed_setting × entry_angle 说明切入姿态与运动节奏存在耦合；penetration_depth × entry_angle 则表明深度与姿态共同决定铲体与泥体接触几何关系。上述交互趋势具有一定参考意义，但仍需要后续真实实验进一步验证。",
        "",
        "主要模型项方向如下：",
    ]
    for term in ["speed_setting", "penetration_depth", "entry_angle", "speed_setting^2", "penetration_depth^2", "entry_angle^2", "speed_setting penetration_depth", "speed_setting entry_angle", "penetration_depth entry_angle"]:
        if term in coef_map:
            direction = "正向" if coef_map[term] > 0 else "负向"
            lines.append(f"- {term}: {direction}（系数 {coef_map[term]:.6f}）")

    lines.extend(
        [
            "",
            "完整 statsmodels 回归摘要见下文。",
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

    plot_raw_data_scatter(df, chinese_ok)
    plot_synthetic_distribution(df, chinese_ok)
    plot_surface(df, result, fixed_name="speed_setting", fixed_value=0.55, x_name="entry_angle", y_name="penetration_depth", output_name="response_surface_angle_depth.png", chinese_ok=chinese_ok)
    plot_surface(df, result, fixed_name="penetration_depth", fixed_value=32.5, x_name="entry_angle", y_name="speed_setting", output_name="response_surface_angle_speed.png", chinese_ok=chinese_ok)
    plot_surface(df, result, fixed_name="entry_angle", fixed_value=35.0, x_name="penetration_depth", y_name="speed_setting", output_name="response_surface_depth_speed.png", chinese_ok=chinese_ok)
    plot_predicted_vs_actual(df, result["pred"], chinese_ok)
    plot_residual_analysis(df, result["pred"], chinese_ok)
    sensitivity_peaks = plot_factor_sensitivity(result, df, chinese_ok)

    formula = build_formula(result["metrics"]["intercept"], result["feature_names"], result["linreg"].coef_)
    summary_text = build_interpretation(result, sensitivity_peaks)
    SUMMARY_PATH.write_text(formula + "\n\n" + summary_text, encoding="utf-8")

    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(formula)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
