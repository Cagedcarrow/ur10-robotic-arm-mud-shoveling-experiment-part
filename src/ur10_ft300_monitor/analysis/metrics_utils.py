#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from scipy import signal as scipy_signal  # noqa: F401  # reserved for future smoothing upgrade
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "缺少依赖，请先安装: pip install numpy pandas scipy matplotlib openpyxl"
    ) from exc


REQUIRED_COLUMNS = [
    "epoch_time",
    "Label",
    "Fx",
    "Fy",
    "Fz",
    "Mx",
    "My",
    "Mz",
    "Act_X",
    "Act_Y",
    "Act_Z",
    "Act_I0",
    "Act_I1",
    "Act_I2",
    "Act_I3",
    "Act_I4",
    "Act_I5",
]

UR_CURRENT_COLS = [f"Act_I{i}" for i in range(6)]
UR_POSITION_COLS = ["Act_X", "Act_Y", "Act_Z"]
UR_TCP_SPEED_COLS = ["Act_dX", "Act_dY", "Act_dZ"]
FT_COLS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
FT_FORCE_COLS = ["Fx", "Fy", "Fz"]
FT_TORQUE_COLS = ["Mx", "My", "Mz"]

PROCESSED_METRIC_COLUMNS = [
    "experiment_dir",
    "experiment_id",
    "mass_g",
    "d_mm",
    "theta_deg",
    "vc_mps",
    "vl_mps",
    "sample_count_total",
    "sample_count_exp",
    "duration",
    "ft_fresh_ratio",
    "ur_fresh_ratio",
    "F_max",
    "F_mean",
    "F_std",
    "F_rms",
    "M_max",
    "M_mean",
    "M_std",
    "M_rms",
    "path_length",
    "E_force",
    "E_per_mass",
    "I_max",
    "I_mean",
    "I_std",
    "I_rms",
    "smoothness_force",
    "shock_count",
    "tcp_speed_max",
    "tcp_speed_mean",
    "baseline_method",
    "warning",
]


@dataclass
class ProcessArtifacts:
    metrics: Dict[str, object]
    df_exp: pd.DataFrame
    df_ur: pd.DataFrame
    df_ft: pd.DataFrame
    force_rate: np.ndarray
    t_force_rate: np.ndarray
    cumulative_energy: np.ndarray


def _to_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    out = df.copy()
    existing_cols = []
    seen = set()
    for col in cols:
        if col in out.columns and col not in seen:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            existing_cols.append(col)
            seen.add(col)
    if existing_cols:
        out[existing_cols] = out[existing_cols].ffill().bfill()
    return out


def load_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"CSV 数据为空: {csv_path}")
    return df


def check_required_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要列: {', '.join(missing)}")


def resolve_time(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    out = df.copy()
    source = "epoch_time"
    if "epoch_time" in out.columns:
        et = pd.to_numeric(out["epoch_time"], errors="coerce")
        if et.notna().sum() >= 2:
            out["epoch_time"] = et.ffill().bfill()
            out["t"] = out["epoch_time"] - out["epoch_time"].iloc[0]
            return out, source

    if "Time" in out.columns:
        source = "Time"
        tm = pd.to_numeric(out["Time"], errors="coerce")
        if tm.notna().sum() >= 2:
            out["Time"] = tm.ffill().bfill()
            out["t"] = out["Time"] - out["Time"].iloc[0]
            return out, source

    source = "index"
    out["t"] = np.arange(len(out), dtype=float)
    return out, source


def extract_experiment_segment(df: pd.DataFrame, min_rows: int = 10) -> Tuple[pd.DataFrame, bool, str]:
    label_numeric = pd.to_numeric(df["Label"], errors="coerce").fillna(0.0)
    df_labeled = df[label_numeric == 1].copy()
    if len(df_labeled) >= min_rows:
        return df_labeled, True, ""
    warning = "警告：未检测到足够的 Label=1 实验段，本次处理使用全段数据。"
    return df.copy(), False, warning


def fresh_filter(df_exp: pd.DataFrame, min_rows: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    ft_warning = ""
    ur_warning = ""

    if "ft_fresh" in df_exp.columns:
        ft_mask = pd.to_numeric(df_exp["ft_fresh"], errors="coerce").fillna(0.0) == 1
        df_ft = df_exp[ft_mask].copy()
    else:
        df_ft = df_exp.copy()

    if "ur_fresh" in df_exp.columns:
        ur_mask = pd.to_numeric(df_exp["ur_fresh"], errors="coerce").fillna(0.0) == 1
        df_ur = df_exp[ur_mask].copy()
    else:
        df_ur = df_exp.copy()

    if len(df_ft) < min_rows:
        df_ft = df_exp.copy()
        ft_warning = "FT fresh 样本不足，已回退为实验段全量数据。"

    if len(df_ur) < min_rows:
        df_ur = df_exp.copy()
        ur_warning = "UR fresh 样本不足，已回退为实验段全量数据。"

    return df_ft, df_ur, ft_warning, ur_warning


def compute_baseline(df_all: pd.DataFrame, df_exp: pd.DataFrame, min_rows: int = 10) -> Tuple[Dict[str, float], str, str]:
    baseline_values = {c: 0.0 for c in FT_COLS}
    method = "none"
    warning = ""

    labels = pd.to_numeric(df_all["Label"], errors="coerce").fillna(0.0)
    label1_idx = labels[labels == 1].index
    baseline_df = pd.DataFrame()

    if len(label1_idx) > 0:
        first_idx = label1_idx[0]
        before = df_all.loc[: first_idx - 1].copy()
        before_label = pd.to_numeric(before["Label"], errors="coerce").fillna(0.0)
        baseline_df = before[before_label == 0]
        if len(baseline_df) >= min_rows:
            method = "label0_before_first_label1"

    if method == "none":
        head_n = max(1, int(len(df_exp) * 0.05))
        baseline_head = df_exp.head(head_n).copy()
        if len(baseline_head) >= min_rows:
            baseline_df = baseline_head
            method = "first_5_percent_of_experiment"

    if method == "none":
        warning = "警告：FT300 零点段不足，未执行零点修正。"
        return baseline_values, method, warning

    baseline_df = _to_numeric(baseline_df, FT_COLS)
    for c in FT_COLS:
        baseline_values[c] = float(np.nanmean(baseline_df[c].to_numpy(dtype=float)))
        if np.isnan(baseline_values[c]):
            baseline_values[c] = 0.0
    return baseline_values, method, warning


def apply_ft_correction(df: pd.DataFrame, baseline_values: Dict[str, float], smooth_window: int) -> pd.DataFrame:
    out = df.copy()
    window = max(1, int(smooth_window))
    for col in FT_COLS:
        out[f"{col}_corr"] = out[col] - baseline_values.get(col, 0.0)
        out[f"{col}_smooth"] = out[f"{col}_corr"].rolling(window=window, min_periods=1).mean()

    out["F_resultant"] = np.sqrt(
        out["Fx_smooth"] ** 2 + out["Fy_smooth"] ** 2 + out["Fz_smooth"] ** 2
    )
    out["M_resultant"] = np.sqrt(
        out["Mx_smooth"] ** 2 + out["My_smooth"] ** 2 + out["Mz_smooth"] ** 2
    )
    return out


def _stats(series: pd.Series) -> Tuple[float, float, float, float]:
    arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    if arr.size == 0 or np.all(np.isnan(arr)):
        return np.nan, np.nan, np.nan, np.nan
    vmax = float(np.nanmax(arr))
    vmean = float(np.nanmean(arr))
    vstd = float(np.nanstd(arr))
    vrms = float(np.sqrt(np.nanmean(arr**2)))
    return vmax, vmean, vstd, vrms


def _path_ds(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    if len(x) == 0:
        return np.array([], dtype=float)
    dx = np.diff(x, prepend=x[0])
    dy = np.diff(y, prepend=y[0])
    dz = np.diff(z, prepend=z[0])
    return np.sqrt(dx**2 + dy**2 + dz**2)


def _safe_numeric_col(df: pd.DataFrame, col: str) -> np.ndarray:
    if col not in df.columns:
        return np.full(len(df), np.nan, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)


def _compute_force_rate(t: np.ndarray, f: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if len(t) < 2:
        return np.array([], dtype=float), np.array([], dtype=float)
    dt = np.diff(t)
    df = np.abs(np.diff(f))
    valid = dt > 1e-9
    rate = np.full_like(df, np.nan, dtype=float)
    rate[valid] = df[valid] / dt[valid]
    t_mid = t[1:]
    return t_mid, rate


def parse_manual_record(experiment_dir: Path) -> Dict[str, object]:
    record = {
        "mass_g": np.nan,
        "experiment_id": experiment_dir.name,
        "d_mm": np.nan,
        "theta_deg": np.nan,
        "vc_mps": np.nan,
        "vl_mps": np.nan,
        "note": "",
    }
    record_path = experiment_dir / "manual_record.txt"
    if not record_path.exists():
        return record

    text = record_path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        value = v.strip()
        if key in {"mass_g", "d_mm", "theta_deg", "vc_mps", "vl_mps"}:
            try:
                record[key] = float(value)
            except ValueError:
                record[key] = np.nan
        elif key in {"experiment_id", "note"}:
            record[key] = value
    return record


def _plot_single(
    fig_path: Path,
    t: np.ndarray,
    series_map: Dict[str, np.ndarray],
    title: str,
    xlabel: str,
    ylabel: str,
    annotate: Optional[Tuple[float, float, str]] = None,
) -> None:
    plt.figure(figsize=(10, 4))
    for name, values in series_map.items():
        if len(values) == 0:
            continue
        plt.plot(t[: len(values)], values, label=name)
    if annotate is not None:
        x, y, text = annotate
        if np.isfinite(x) and np.isfinite(y):
            plt.scatter([x], [y], color="red", zorder=5)
            plt.text(x, y, text)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    if series_map:
        plt.legend()
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(fig_path, dpi=200, bbox_inches="tight")
    plt.close()


def create_figures(
    fig_dir: Path,
    df_exp: pd.DataFrame,
    df_ur: pd.DataFrame,
    t_force_rate: np.ndarray,
    force_rate: np.ndarray,
    cumulative_energy: np.ndarray,
) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)

    t_exp = _safe_numeric_col(df_exp, "t")
    t_ur = _safe_numeric_col(df_ur, "t")

    _plot_single(
        fig_dir / "force_curve.png",
        t_exp,
        {
            "Fx_corr": _safe_numeric_col(df_exp, "Fx_corr"),
            "Fy_corr": _safe_numeric_col(df_exp, "Fy_corr"),
            "Fz_corr": _safe_numeric_col(df_exp, "Fz_corr"),
        },
        "力曲线（零点修正后）",
        "t (s)",
        "Force (N)",
    )
    _plot_single(
        fig_dir / "torque_curve.png",
        t_exp,
        {
            "Mx_corr": _safe_numeric_col(df_exp, "Mx_corr"),
            "My_corr": _safe_numeric_col(df_exp, "My_corr"),
            "Mz_corr": _safe_numeric_col(df_exp, "Mz_corr"),
        },
        "力矩曲线（零点修正后）",
        "t (s)",
        "Torque (Nm)",
    )

    f_res = _safe_numeric_col(df_exp, "F_resultant")
    if len(f_res) > 0 and np.any(np.isfinite(f_res)):
        idx_f = int(np.nanargmax(f_res))
        ann_f = (t_exp[idx_f], f_res[idx_f], f"F_max={f_res[idx_f]:.2f}")
    else:
        ann_f = None
    _plot_single(
        fig_dir / "force_resultant_curve.png",
        t_exp,
        {"F_resultant": f_res},
        "合力曲线",
        "t (s)",
        "Force (N)",
        annotate=ann_f,
    )

    m_res = _safe_numeric_col(df_exp, "M_resultant")
    if len(m_res) > 0 and np.any(np.isfinite(m_res)):
        idx_m = int(np.nanargmax(m_res))
        ann_m = (t_exp[idx_m], m_res[idx_m], f"M_max={m_res[idx_m]:.2f}")
    else:
        ann_m = None
    _plot_single(
        fig_dir / "torque_resultant_curve.png",
        t_exp,
        {"M_resultant": m_res},
        "合力矩曲线",
        "t (s)",
        "Torque (Nm)",
        annotate=ann_m,
    )

    _plot_single(
        fig_dir / "tcp_position_curve.png",
        t_exp,
        {
            "Act_X": _safe_numeric_col(df_exp, "Act_X"),
            "Act_Y": _safe_numeric_col(df_exp, "Act_Y"),
            "Act_Z": _safe_numeric_col(df_exp, "Act_Z"),
        },
        "TCP 位置曲线",
        "t (s)",
        "Position (m)",
    )
    _plot_single(
        fig_dir / "joint_current_curve.png",
        t_ur,
        {c: _safe_numeric_col(df_ur, c) for c in UR_CURRENT_COLS},
        "关节电流曲线",
        "t (s)",
        "Current (A)",
    )
    _plot_single(
        fig_dir / "energy_curve.png",
        t_exp,
        {"cumulative_energy": cumulative_energy},
        "累计能量曲线",
        "t (s)",
        "Energy (N*m)",
    )
    _plot_single(
        fig_dir / "smoothness_curve.png",
        t_force_rate,
        {"force_rate": force_rate},
        "力变化率曲线",
        "t (s)",
        "dF/dt (N/s)",
    )


def _safe_float(value: object) -> float:
    try:
        out = float(value)
    except Exception:
        return np.nan
    if math.isinf(out):
        return np.nan
    return out


def _anomaly_text(
    shock_count: float,
    smoothness_force: float,
    ft_fresh_ratio: float,
    ur_fresh_ratio: float,
) -> str:
    reasons = []
    if np.isfinite(shock_count) and shock_count > 20:
        reasons.append("力突变次数较高")
    if np.isfinite(smoothness_force) and smoothness_force > 50:
        reasons.append("力变化率偏大")
    if np.isfinite(ft_fresh_ratio) and ft_fresh_ratio < 0.2:
        reasons.append("FT fresh 比例过低")
    if np.isfinite(ur_fresh_ratio) and ur_fresh_ratio < 0.2:
        reasons.append("UR fresh 比例过低")
    if reasons:
        return "可能存在异常：" + "；".join(reasons)
    return "未见明显异常趋势（仅基于当前指标）"


def process_experiment(
    experiment_dir: Path,
    csv_path: Path,
    mass_g_cli: Optional[float] = None,
    force_threshold: float = 10.0,
    smooth_window: int = 5,
    min_segment_rows: int = 10,
) -> ProcessArtifacts:
    df_raw = load_csv(csv_path)
    check_required_columns(df_raw)
    sample_count_total = len(df_raw)

    df_time, time_source = resolve_time(df_raw)
    df_exp_raw, used_label, label_warning = extract_experiment_segment(df_time, min_rows=min_segment_rows)

    numeric_cols = list(set(df_time.columns) & set(REQUIRED_COLUMNS + ["Time", "ur_fresh", "ft_fresh"] + UR_TCP_SPEED_COLS))
    df_exp = _to_numeric(df_exp_raw, numeric_cols + UR_CURRENT_COLS + UR_POSITION_COLS + FT_COLS)

    df_ft, df_ur, ft_warning, ur_warning = fresh_filter(df_exp, min_rows=min_segment_rows)
    df_ft = _to_numeric(df_ft, numeric_cols + UR_CURRENT_COLS + UR_POSITION_COLS + FT_COLS)
    df_ur = _to_numeric(df_ur, numeric_cols + UR_CURRENT_COLS + UR_POSITION_COLS + FT_COLS)

    baseline_values, baseline_method, baseline_warning = compute_baseline(df_time, df_exp, min_rows=min_segment_rows)
    df_exp = apply_ft_correction(df_exp, baseline_values, smooth_window)
    df_ft = apply_ft_correction(df_ft, baseline_values, smooth_window)

    t_exp = _safe_numeric_col(df_exp, "t")
    duration = float(np.nanmax(t_exp) - np.nanmin(t_exp)) if len(t_exp) > 1 else 0.0

    fx_stats = _stats(df_ft["F_resultant"])
    mx_stats = _stats(df_ft["M_resultant"])

    x_ur = _safe_numeric_col(df_ur, "Act_X")
    y_ur = _safe_numeric_col(df_ur, "Act_Y")
    z_ur = _safe_numeric_col(df_ur, "Act_Z")
    ds_ur = _path_ds(x_ur, y_ur, z_ur)
    path_length = float(np.nansum(ds_ur)) if len(ds_ur) > 0 else np.nan

    x_exp = _safe_numeric_col(df_exp, "Act_X")
    y_exp = _safe_numeric_col(df_exp, "Act_Y")
    z_exp = _safe_numeric_col(df_exp, "Act_Z")
    ds_exp = _path_ds(x_exp, y_exp, z_exp)
    f_exp = _safe_numeric_col(df_exp, "F_resultant")
    e_steps = f_exp * ds_exp if len(f_exp) == len(ds_exp) else np.array([], dtype=float)
    if len(e_steps) > 0:
        e_steps = np.where(np.isfinite(e_steps), e_steps, 0.0)
        E_force = float(np.sum(e_steps))
        cumulative_energy = np.cumsum(e_steps)
    else:
        E_force = np.nan
        cumulative_energy = np.array([], dtype=float)

    manual = parse_manual_record(experiment_dir)
    mass_g = _safe_float(mass_g_cli) if mass_g_cli is not None else _safe_float(manual.get("mass_g", np.nan))
    if np.isfinite(mass_g) and mass_g > 0 and np.isfinite(E_force):
        E_per_mass = E_force / mass_g
    else:
        E_per_mass = np.nan

    i_sum = np.zeros(len(df_ur), dtype=float)
    for c in UR_CURRENT_COLS:
        i_sum += np.abs(_safe_numeric_col(df_ur, c))
    I_max, I_mean, I_std, I_rms = _stats(pd.Series(i_sum))

    if all(c in df_ur.columns for c in UR_TCP_SPEED_COLS):
        dX = _safe_numeric_col(df_ur, "Act_dX")
        dY = _safe_numeric_col(df_ur, "Act_dY")
        dZ = _safe_numeric_col(df_ur, "Act_dZ")
        tcp_speed = np.sqrt(dX**2 + dY**2 + dZ**2)
        tcp_speed_max = float(np.nanmax(tcp_speed)) if np.any(np.isfinite(tcp_speed)) else np.nan
        tcp_speed_mean = float(np.nanmean(tcp_speed)) if np.any(np.isfinite(tcp_speed)) else np.nan
    else:
        tcp_speed_max = np.nan
        tcp_speed_mean = np.nan

    t_ft = _safe_numeric_col(df_ft, "t")
    f_ft = _safe_numeric_col(df_ft, "F_resultant")
    t_force_rate, force_rate = _compute_force_rate(t_ft, f_ft)
    smoothness_force = float(np.nanmean(force_rate)) if len(force_rate) > 0 and np.any(np.isfinite(force_rate)) else np.nan

    if len(f_ft) >= 2:
        dF = np.abs(np.diff(f_ft))
        shock_count = float(np.nansum(dF > float(force_threshold)))
    else:
        shock_count = np.nan

    sample_count_exp = len(df_exp)
    ft_fresh_ratio = (
        float(np.nanmean(pd.to_numeric(df_exp["ft_fresh"], errors="coerce").to_numpy(dtype=float) == 1))
        if "ft_fresh" in df_exp.columns
        else np.nan
    )
    ur_fresh_ratio = (
        float(np.nanmean(pd.to_numeric(df_exp["ur_fresh"], errors="coerce").to_numpy(dtype=float) == 1))
        if "ur_fresh" in df_exp.columns
        else np.nan
    )

    warnings = []
    if label_warning:
        warnings.append(label_warning)
    if ft_warning:
        warnings.append(ft_warning)
    if ur_warning:
        warnings.append(ur_warning)
    if baseline_warning:
        warnings.append(baseline_warning)
    if not np.isfinite(mass_g):
        warnings.append("未提供 mass_g，E_per_mass 为 NaN。")
    warning_text = " | ".join(warnings)

    metrics = {
        "experiment_dir": str(experiment_dir),
        "experiment_id": manual.get("experiment_id", experiment_dir.name) or experiment_dir.name,
        "mass_g": mass_g,
        "d_mm": _safe_float(manual.get("d_mm", np.nan)),
        "theta_deg": _safe_float(manual.get("theta_deg", np.nan)),
        "vc_mps": _safe_float(manual.get("vc_mps", np.nan)),
        "vl_mps": _safe_float(manual.get("vl_mps", np.nan)),
        "sample_count_total": int(sample_count_total),
        "sample_count_exp": int(sample_count_exp),
        "duration": duration,
        "ft_fresh_ratio": ft_fresh_ratio,
        "ur_fresh_ratio": ur_fresh_ratio,
        "F_max": fx_stats[0],
        "F_mean": fx_stats[1],
        "F_std": fx_stats[2],
        "F_rms": fx_stats[3],
        "M_max": mx_stats[0],
        "M_mean": mx_stats[1],
        "M_std": mx_stats[2],
        "M_rms": mx_stats[3],
        "path_length": path_length,
        "E_force": E_force,
        "E_per_mass": E_per_mass,
        "I_max": I_max,
        "I_mean": I_mean,
        "I_std": I_std,
        "I_rms": I_rms,
        "smoothness_force": smoothness_force,
        "shock_count": shock_count,
        "tcp_speed_max": tcp_speed_max,
        "tcp_speed_mean": tcp_speed_mean,
        "baseline_method": baseline_method,
        "warning": warning_text,
    }

    figures_dir = experiment_dir / "figures"
    create_figures(
        figures_dir,
        df_exp=df_exp,
        df_ur=df_ur,
        t_force_rate=t_force_rate,
        force_rate=force_rate,
        cumulative_energy=cumulative_energy,
    )

    metrics_df = pd.DataFrame([metrics], columns=PROCESSED_METRIC_COLUMNS)
    metrics_df.to_csv(experiment_dir / "processed_metrics.csv", index=False, encoding="utf-8")

    anomaly = _anomaly_text(
        shock_count=metrics["shock_count"],
        smoothness_force=metrics["smoothness_force"],
        ft_fresh_ratio=metrics["ft_fresh_ratio"],
        ur_fresh_ratio=metrics["ur_fresh_ratio"],
    )
    summary_lines = [
        "# 实验处理总结",
        f"实验目录: {experiment_dir}",
        f"数据文件: {csv_path}",
        f"时间来源: {time_source}",
        f"是否使用 Label=1 实验段: {'是' if used_label else '否（已回退全段）'}",
        f"零点修正方法: {baseline_method}",
        f"样本数量: 总计 {sample_count_total} 行, 实验段 {sample_count_exp} 行",
        f"实验段持续时间: {duration:.3f} s" if np.isfinite(duration) else "实验段持续时间: NaN",
        "",
        "指标解释:",
        f"- 最大合力 F_max={metrics['F_max']:.4f} N（反映铲泥最大冲击/阻力）" if np.isfinite(metrics["F_max"]) else "- 最大合力 F_max=NaN",
        f"- 最大力矩 M_max={metrics['M_max']:.4f} Nm（反映偏载/扭转载荷峰值）" if np.isfinite(metrics["M_max"]) else "- 最大力矩 M_max=NaN",
        f"- 末端能量估计 E_force={metrics['E_force']:.4f} N*m（基于末端力与位移的近似功）" if np.isfinite(metrics["E_force"]) else "- 末端能量估计 E_force=NaN",
        f"- 平滑性 smoothness_force={metrics['smoothness_force']:.4f} N/s（越小越平稳）" if np.isfinite(metrics["smoothness_force"]) else "- 平滑性 smoothness_force=NaN",
        f"- 力突变次数 shock_count={metrics['shock_count']:.0f}（越大越不稳定）" if np.isfinite(metrics["shock_count"]) else "- 力突变次数 shock_count=NaN",
        "",
        anomaly,
    ]
    if warning_text:
        summary_lines.append(f"警告信息: {warning_text}")
    if manual.get("note"):
        summary_lines.append(f"人工记录备注: {manual['note']}")

    (experiment_dir / "processed_summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return ProcessArtifacts(
        metrics=metrics,
        df_exp=df_exp,
        df_ur=df_ur,
        df_ft=df_ft,
        force_rate=force_rate,
        t_force_rate=t_force_rate,
        cumulative_energy=cumulative_energy,
    )
