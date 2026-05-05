#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.transforms import blended_transform_factory


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = ROOT / "data"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "analysis"
DEFAULT_SUMMARY_MD = DEFAULT_OUTPUT_ROOT / "all_sessions_motion_smoothness_summary.md"
WEIGHT_OUTPUT_ROOT = ROOT / "data" / "analysis" / "output"
CSV_NAME = "ur10_ft300_realtime_data.csv"
TIME_FIELD = "Time"
JOINT_POSITION_FIELDS = [f"Act_q{i}" for i in range(6)]
JOINT_TARGET_FIELDS = [f"Tgt_q{i}" for i in range(6)]
JOINT_VELOCITY_FIELDS = [f"Act_qd{i}" for i in range(6)]
JOINT_CURRENT_FIELDS = [f"Act_I{i}" for i in range(6)]
TCP_POSE_FIELDS = ["Act_X", "Act_Y", "Act_Z", "Act_RX", "Act_RY", "Act_RZ"]
TCP_TWIST_FIELDS = ["Act_dX", "Act_dY", "Act_dZ", "Act_dRX", "Act_dRY", "Act_dRZ"]
WRENCH_FIELDS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
JOINT_LABELS = [f"J{i}" for i in range(6)]
TCP_POSE_LABELS = ["X", "Y", "Z", "RX", "RY", "RZ"]
TCP_TWIST_LABELS = ["dX", "dY", "dZ", "dRX", "dRY", "dRZ"]
WRENCH_LABELS = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
OLD_OUTPUT_STEMS = [
    "joint_position_trend",
    "joint_velocity_trend",
    "velocity_wrench_correlation",
    "tcp_pose_velocity_analysis",
    "multi_modal_coupling_overview",
]
NEW_OUTPUT_STEMS = ["main_figure", "supplementary_figure"]
CHINESE_FONT_PATH = Path("/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf")
CHINESE_FONT_NAME = "AR PL SungtiL GB"
PALETTE = {
    "joint": "#48688E",
    "target": "#D17B60",
    "tcp": "#628A74",
    "force": "#7A4E77",
    "moment": "#946B44",
    "neutral": "#6B6B6B",
    "heat_pos": "#D66F52",
    "heat_neg": "#4E6E99",
    "stage_contact": "#F7D8A8",
    "stage_loading": "#F3B46A",
    "stage_retreat": "#B8D6E6",
    "stage_weighing": "#CBE7C5",
}
STAGE_ORDER = ["contact", "loading", "retreat", "weighing"]
STAGE_LABELS = {
    "contact": "接触",
    "loading": "装载",
    "retreat": "回撤",
    "weighing": "称重",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch analyze motion smoothness, coupling, and stage segmentation.")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    parser.add_argument("--rolling-window", type=int, default=41)
    return parser.parse_args()


def apply_publication_style(font_size: int = 12, axes_linewidth: float = 1.7) -> None:
    if CHINESE_FONT_PATH.exists():
        font_manager.fontManager.addfont(str(CHINESE_FONT_PATH))
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [CHINESE_FONT_NAME, "DejaVu Sans", "Arial"]
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.size"] = font_size
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.linewidth"] = axes_linewidth
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["axes.unicode_minus"] = False


def add_panel_label(ax: plt.Axes, label: str, x: float = -0.08, y: float = 1.02) -> None:
    ax.text(x, y, label, transform=ax.transAxes, fontsize=12, fontweight="bold", ha="left", va="bottom")


def to_float(value: str | None) -> float:
    if value in ("", "nan", "NaN", "None", None):
        return math.nan
    return float(value)


def finite_or_nanmean(values: np.ndarray) -> float:
    return float(np.nanmean(values)) if np.isfinite(values).any() else math.nan


def finite_or_nanstd(values: np.ndarray) -> float:
    return float(np.nanstd(values)) if np.isfinite(values).any() else math.nan


def finite_or_nanmax(values: np.ndarray) -> float:
    return float(np.nanmax(values)) if np.isfinite(values).any() else math.nan


def finite_or_nanmin(values: np.ndarray) -> float:
    return float(np.nanmin(values)) if np.isfinite(values).any() else math.nan


def rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    if values.size == 0:
        return values
    window = max(1, min(window, values.size))
    valid = np.isfinite(values)
    filled = np.where(valid, values, 0.0)
    kernel = np.ones(window, dtype=float)
    summed = np.convolve(filled, kernel, mode="same")
    counts = np.convolve(valid.astype(float), kernel, mode="same")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = summed / counts
    out[counts == 0] = np.nan
    return out


def robust_scale(values: np.ndarray) -> np.ndarray:
    mask = np.isfinite(values)
    out = np.full(values.shape, np.nan, dtype=float)
    if mask.sum() == 0:
        return out
    valid = values[mask]
    lo = np.percentile(valid, 5)
    hi = np.percentile(valid, 95)
    if hi - lo < 1e-9:
        out[mask] = 0.0
        return out
    out[mask] = np.clip((valid - lo) / (hi - lo), 0.0, 1.0)
    return out


def pairwise_corr(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return math.nan
    xv = x[mask]
    yv = y[mask]
    if np.nanstd(xv) < 1e-12 or np.nanstd(yv) < 1e-12:
        return math.nan
    return float(np.corrcoef(xv, yv)[0, 1])


def compute_matrix_corr(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    corr = np.full((left.shape[0], right.shape[0]), np.nan, dtype=float)
    for i in range(left.shape[0]):
        for j in range(right.shape[0]):
            corr[i, j] = pairwise_corr(left[i], right[j])
    return corr


def extract_strongest_pairs(corr: np.ndarray) -> list[tuple[int, int, float]]:
    pairs: list[tuple[int, int, float]] = []
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            if math.isfinite(corr[i, j]):
                pairs.append((i, j, float(corr[i, j])))
    pairs.sort(key=lambda item: abs(item[2]), reverse=True)
    return pairs


def find_session_dirs(data_root: Path) -> list[Path]:
    return [path for path in sorted(data_root.iterdir()) if path.is_dir() and (path / CSV_NAME).exists()]


def load_session_data(csv_path: Path) -> dict[str, np.ndarray]:
    required = [TIME_FIELD] + JOINT_POSITION_FIELDS + JOINT_TARGET_FIELDS + JOINT_VELOCITY_FIELDS
    required += JOINT_CURRENT_FIELDS + TCP_POSE_FIELDS + TCP_TWIST_FIELDS + WRENCH_FIELDS
    cols: dict[str, list[float]] = {field: [] for field in required}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for field in required:
                cols[field].append(to_float(row.get(field)))
    return {field: np.array(values, dtype=float) for field, values in cols.items()}


def export_figure(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def cleanup_old_outputs(output_dir: Path) -> None:
    for stem in OLD_OUTPUT_STEMS:
        for suffix in (".png", ".svg"):
            path = output_dir / f"{stem}{suffix}"
            if path.exists():
                path.unlink()


def compute_tracking_rmse(act_q: np.ndarray, tgt_q: np.ndarray) -> list[float]:
    out: list[float] = []
    for idx in range(6):
        err = act_q[idx] - tgt_q[idx]
        mask = np.isfinite(err)
        out.append(float(np.sqrt(np.mean(err[mask] ** 2))) if mask.sum() else math.nan)
    return out


def compute_velocity_metrics(time: np.ndarray, velocity: np.ndarray) -> list[dict[str, float]]:
    dt = np.diff(time)
    metrics: list[dict[str, float]] = []
    for idx in range(6):
        series = velocity[idx]
        dv = np.diff(series)
        valid = np.isfinite(dt) & np.isfinite(dv) & (np.abs(dt) > 1e-12)
        diff_values = dv[valid]
        jerk = dv[valid] / dt[valid] if valid.any() else np.array([], dtype=float)
        metrics.append(
            {
                "mean": finite_or_nanmean(series),
                "std": finite_or_nanstd(series),
                "ptp": finite_or_nanmax(series) - finite_or_nanmin(series),
                "diff_std": finite_or_nanstd(diff_values),
                "jerk_abs_max": float(np.nanmax(np.abs(jerk))) if jerk.size else math.nan,
            }
        )
    return metrics


def load_weight_stage_indices(session_name: str) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    stable_path = WEIGHT_OUTPUT_ROOT / session_name / "stable_segments.csv"
    if not stable_path.exists():
        return None, None
    final_segment = None
    ref_segment = None
    with stable_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("is_final_measurement_segment") == "1":
                final_segment = (int(float(row["start_sample_index"])), int(float(row["end_sample_index"])))
            if row.get("is_reference_segment") == "1":
                ref_segment = (int(float(row["start_sample_index"])), int(float(row["end_sample_index"])))
    return final_segment, ref_segment


def summarize_window(values: np.ndarray, start: int, end: int) -> tuple[float, float]:
    if end < start:
        return math.nan, math.nan
    segment = values[start : end + 1]
    return finite_or_nanmean(segment), finite_or_nanstd(segment)


def detect_stages(
    session_name: str,
    qd_norm: np.ndarray,
    twist_norm: np.ndarray,
    force_mag: np.ndarray,
    force_smooth: np.ndarray,
) -> dict[str, dict[str, object]]:
    n = len(qd_norm)
    final_segment, ref_segment = load_weight_stage_indices(session_name)
    motion_thr = max(np.percentile(qd_norm[np.isfinite(qd_norm)], 35) if np.isfinite(qd_norm).any() else 0.0, 0.02)
    twist_thr = max(np.percentile(twist_norm[np.isfinite(twist_norm)], 35) if np.isfinite(twist_norm).any() else 0.0, 0.01)
    moving_mask = ((np.nan_to_num(qd_norm) > motion_thr) | (np.nan_to_num(twist_norm) > twist_thr))

    stages: dict[str, dict[str, object]] = {
        name: {"present": False, "start": None, "end": None, "confidence": "low", "reason": ""} for name in STAGE_ORDER
    }

    if final_segment is not None:
        weigh_start, weigh_end = final_segment
        stages["weighing"] = {
            "present": True,
            "start": weigh_start,
            "end": weigh_end,
            "confidence": "high",
            "reason": "复用已有称重分析中的最终稳态段。",
        }
    else:
        tail_len = max(40, n // 12)
        weigh_start = max(0, n - tail_len)
        weigh_end = n - 1
        stages["weighing"] = {
            "present": True,
            "start": weigh_start,
            "end": weigh_end,
            "confidence": "medium",
            "reason": "未找到已有称重稳态，退化为末尾低运动稳态窗口。",
        }

    pre_end = max(0, stages["weighing"]["start"] - 1)
    pre_indices = np.arange(pre_end + 1)
    active_indices = pre_indices[moving_mask[: pre_end + 1]]
    if active_indices.size == 0:
        stages["contact"]["reason"] = "未检测到称重前的显著运动段。"
        stages["loading"]["reason"] = "未检测到称重前的显著运动段。"
        stages["retreat"]["reason"] = "未检测到称重前的显著运动段。"
        return stages

    active_start = int(active_indices[0])
    peak_idx = int(np.nanargmax(force_smooth[: pre_end + 1])) if np.isfinite(force_smooth[: pre_end + 1]).any() else active_start
    baseline_slice = force_smooth[: max(active_start, 20)]
    baseline_force = finite_or_nanmean(baseline_slice) if baseline_slice.size else finite_or_nanmean(force_smooth[:20])
    peak_force = float(force_smooth[peak_idx]) if math.isfinite(force_smooth[peak_idx]) else float(np.nanmax(force_smooth[: pre_end + 1]))
    rise_level = baseline_force + 0.4 * (peak_force - baseline_force) if math.isfinite(baseline_force) and math.isfinite(peak_force) else math.nan

    contact_end = None
    if math.isfinite(rise_level):
        for idx in range(active_start, pre_end + 1):
            if math.isfinite(force_smooth[idx]) and force_smooth[idx] >= rise_level:
                contact_end = idx
                break
    if contact_end is None:
        contact_end = min(pre_end, active_start + max(30, n // 30))

    min_stage_len = max(15, n // 120)
    if contact_end - active_start + 1 >= min_stage_len:
        stages["contact"] = {
            "present": True,
            "start": active_start,
            "end": contact_end,
            "confidence": "medium" if peak_idx > contact_end else "low",
            "reason": "依据早期运动启动与载荷显著上升确定接触段。",
        }
    else:
        stages["contact"]["reason"] = "接触段长度过短，未单独成段。"

    loading_start = (contact_end + 1) if stages["contact"]["present"] else active_start
    loading_end = peak_idx
    if loading_end - loading_start + 1 >= min_stage_len and loading_end < pre_end - min_stage_len:
        stages["loading"] = {
            "present": True,
            "start": loading_start,
            "end": loading_end,
            "confidence": "medium",
            "reason": "依据载荷持续增高并达到称重前峰值确定装载段。",
        }
    else:
        stages["loading"]["reason"] = "装载峰值区段不够独立，未稳定识别。"

    retreat_start = max(loading_end + 1, loading_start if not stages["loading"]["present"] else loading_end + 1)
    retreat_end = pre_end
    if ref_segment is not None:
        # Keep retreat spanning up to final weighing start, but reference window improves confidence.
        ref_start, ref_end = ref_segment
        if ref_start < retreat_end:
            retreat_start = min(retreat_start, max(loading_end + 1, ref_start - max(40, n // 80)))
    force_drop = peak_force - finite_or_nanmean(force_smooth[max(retreat_start, pre_end - max(60, n // 20)) : pre_end + 1])
    if retreat_end - retreat_start + 1 >= min_stage_len and (not math.isnan(force_drop)) and force_drop > 1.0:
        confidence = "high" if ref_segment is not None else "medium"
        reason = "依据称重前持续运动与载荷回落趋势确定回撤段。"
        if ref_segment is not None:
            reason += " 结合已有参考稳态窗口提高可信度。"
        stages["retreat"] = {
            "present": True,
            "start": retreat_start,
            "end": retreat_end,
            "confidence": confidence,
            "reason": reason,
        }
    else:
        stages["retreat"]["reason"] = "称重前回撤趋势不够清晰，允许缺失。"

    return stages


def stage_color(stage_name: str) -> str:
    return PALETTE[f"stage_{stage_name}"]


def add_stage_bands(ax: plt.Axes, stages: dict[str, dict[str, object]], y_text: float = 0.98) -> None:
    trans = blended_transform_factory(ax.transData, ax.transAxes)
    for stage_name in STAGE_ORDER:
        stage = stages[stage_name]
        if not stage["present"]:
            continue
        start = int(stage["start"])
        end = int(stage["end"])
        ax.axvspan(start, end, color=stage_color(stage_name), alpha=0.22, lw=0)
        ax.text(
            (start + end) / 2.0,
            y_text,
            STAGE_LABELS[stage_name],
            transform=trans,
            ha="center",
            va="top",
            fontsize=10,
            color="black",
        )


def plot_main_figure(
    sample_index: np.ndarray,
    act_q: np.ndarray,
    tgt_q: np.ndarray,
    velocity: np.ndarray,
    tcp_twist: np.ndarray,
    qd_norm: np.ndarray,
    twist_norm: np.ndarray,
    force_smooth: np.ndarray,
    joint_wrench_corr: np.ndarray,
    tcp_wrench_corr: np.ndarray,
    stages: dict[str, dict[str, object]],
    output_dir: Path,
) -> None:
    fig = plt.figure(figsize=(16.0, 10.6), constrained_layout=True)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.1, 1.0, 1.15], width_ratios=[1.25, 1.0], hspace=0.18, wspace=0.18)

    ax_a = fig.add_subplot(gs[0, :])
    ax_a.plot(sample_index, robust_scale(qd_norm), color=PALETTE["joint"], lw=1.8, label="关节运动强度")
    ax_a.plot(sample_index, robust_scale(twist_norm), color=PALETTE["tcp"], lw=1.8, label="TCP 运动强度")
    ax_a.plot(sample_index, robust_scale(force_smooth), color=PALETTE["force"], lw=1.8, label="末端力幅值")
    add_stage_bands(ax_a, stages)
    ax_a.set_ylabel("归一化幅值")
    ax_a.set_xlabel("样本序号")
    ax_a.legend(loc="upper right", ncol=3)
    add_panel_label(ax_a, "a")

    ax_b = fig.add_subplot(gs[1, 0], sharex=ax_a)
    error_norm = np.vstack([np.abs(act_q[idx] - tgt_q[idx]) for idx in range(6)])
    for idx in range(6):
        ax_b.plot(sample_index, rolling_mean(error_norm[idx], 31), lw=1.1, label=f"J{idx}")
    add_stage_bands(ax_b, stages)
    ax_b.set_ylabel("跟踪误差 / rad")
    ax_b.set_xlabel("样本序号")
    ax_b.legend(loc="upper right", ncol=3)
    add_panel_label(ax_b, "b")

    ax_c = fig.add_subplot(gs[1, 1], sharex=ax_a)
    for idx in range(6):
        ax_c.plot(sample_index, rolling_mean(velocity[idx], 31), lw=1.05, label=f"qd{idx}")
    add_stage_bands(ax_c, stages)
    ax_c.set_ylabel("关节速度 / rad s$^{-1}$")
    ax_c.set_xlabel("样本序号")
    ax_c.legend(loc="upper right", ncol=3)
    add_panel_label(ax_c, "c")

    ax_d = fig.add_subplot(gs[2, 0])
    im1 = ax_d.imshow(joint_wrench_corr, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax_d.set_xticks(range(6), WRENCH_LABELS)
    ax_d.set_yticks(range(6), [f"qd{i}" for i in range(6)])
    ax_d.set_xlabel("末端六维载荷")
    ax_d.set_ylabel("关节速度分量")
    for i in range(6):
        for j in range(6):
            value = joint_wrench_corr[i, j]
            ax_d.text(j, i, "NA" if not math.isfinite(value) else f"{value:.2f}", ha="center", va="center", fontsize=8.5)
    fig.colorbar(im1, ax=ax_d, fraction=0.046, pad=0.03)
    add_panel_label(ax_d, "d")

    ax_e = fig.add_subplot(gs[2, 1])
    im2 = ax_e.imshow(tcp_wrench_corr, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax_e.set_xticks(range(6), WRENCH_LABELS)
    ax_e.set_yticks(range(6), TCP_TWIST_LABELS)
    ax_e.set_xlabel("末端六维载荷")
    ax_e.set_ylabel("TCP 速度分量")
    for i in range(6):
        for j in range(6):
            value = tcp_wrench_corr[i, j]
            ax_e.text(j, i, "NA" if not math.isfinite(value) else f"{value:.2f}", ha="center", va="center", fontsize=8.5)
    fig.colorbar(im2, ax=ax_e, fraction=0.046, pad=0.03)
    add_panel_label(ax_e, "e")

    export_figure(fig, output_dir / "main_figure")


def plot_supplementary_figure(
    sample_index: np.ndarray,
    tcp_pose: np.ndarray,
    tcp_twist: np.ndarray,
    joint_tcp_corr: np.ndarray,
    qd_norm: np.ndarray,
    twist_norm: np.ndarray,
    force_mag: np.ndarray,
    stages: dict[str, dict[str, object]],
    output_dir: Path,
) -> None:
    fig = plt.figure(figsize=(15.2, 10.0), constrained_layout=True)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 1.0], width_ratios=[1.12, 1.0], hspace=0.18, wspace=0.18)

    ax_a = fig.add_subplot(gs[0, 0])
    for idx, label in enumerate(TCP_POSE_LABELS[:3]):
        ax_a.plot(sample_index, tcp_pose[idx], lw=1.15, label=label)
    add_stage_bands(ax_a, stages)
    ax_a.set_ylabel("TCP 平移")
    ax_a.set_xlabel("样本序号")
    ax_a.legend(loc="upper right", ncol=3)
    add_panel_label(ax_a, "a")

    ax_b = fig.add_subplot(gs[1, 0], sharex=ax_a)
    for idx, label in enumerate(TCP_POSE_LABELS[3:], start=3):
        ax_b.plot(sample_index, tcp_pose[idx], lw=1.15, label=label)
    add_stage_bands(ax_b, stages)
    ax_b.set_ylabel("TCP 姿态")
    ax_b.set_xlabel("样本序号")
    ax_b.legend(loc="upper right", ncol=3)
    add_panel_label(ax_b, "b")

    ax_c = fig.add_subplot(gs[2, 0], sharex=ax_a)
    for idx, label in enumerate(TCP_TWIST_LABELS):
        ax_c.plot(sample_index, rolling_mean(tcp_twist[idx], 31), lw=1.0, label=label)
    add_stage_bands(ax_c, stages)
    ax_c.set_ylabel("TCP 速度")
    ax_c.set_xlabel("样本序号")
    ax_c.legend(loc="upper right", ncol=3)
    add_panel_label(ax_c, "c")

    ax_d = fig.add_subplot(gs[0:2, 1])
    im = ax_d.imshow(joint_tcp_corr, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax_d.set_xticks(range(6), TCP_TWIST_LABELS)
    ax_d.set_yticks(range(6), [f"qd{i}" for i in range(6)])
    ax_d.set_xlabel("TCP 速度分量")
    ax_d.set_ylabel("关节速度分量")
    for i in range(6):
        for j in range(6):
            value = joint_tcp_corr[i, j]
            ax_d.text(j, i, "NA" if not math.isfinite(value) else f"{value:.2f}", ha="center", va="center", fontsize=8.5)
    fig.colorbar(im, ax=ax_d, fraction=0.046, pad=0.03)
    add_panel_label(ax_d, "d")

    ax_e = fig.add_subplot(gs[2, 1])
    stats_labels = []
    qd_stage_values = []
    twist_stage_values = []
    force_stage_values = []
    for stage_name in STAGE_ORDER:
        stage = stages[stage_name]
        if not stage["present"]:
            continue
        start = int(stage["start"])
        end = int(stage["end"])
        stats_labels.append(STAGE_LABELS[stage_name])
        qd_stage_values.append(finite_or_nanmean(qd_norm[start : end + 1]))
        twist_stage_values.append(finite_or_nanmean(twist_norm[start : end + 1]))
        force_stage_values.append(finite_or_nanmean(force_mag[start : end + 1]))
    x = np.arange(len(stats_labels))
    width = 0.24
    if len(stats_labels) > 0:
        ax_e.bar(x - width, robust_scale(np.array(qd_stage_values)), width=width, color=PALETTE["joint"], label="关节运动")
        ax_e.bar(x, robust_scale(np.array(twist_stage_values)), width=width, color=PALETTE["tcp"], label="TCP 运动")
        ax_e.bar(x + width, robust_scale(np.array(force_stage_values)), width=width, color=PALETTE["force"], label="力幅值")
        ax_e.set_xticks(x, stats_labels)
        ax_e.legend(loc="upper right", ncol=3)
    ax_e.set_ylabel("阶段均值（归一化）")
    add_panel_label(ax_e, "e")

    export_figure(fig, output_dir / "supplementary_figure")


def stage_reasonableness(
    stages: dict[str, dict[str, object]],
    qd_norm: np.ndarray,
    twist_norm: np.ndarray,
    force_smooth: np.ndarray,
) -> list[str]:
    notes: list[str] = []
    for stage_name in STAGE_ORDER:
        stage = stages[stage_name]
        if not stage["present"]:
            notes.append(f"- `{STAGE_LABELS[stage_name]}`：未稳定识别，允许缺失，建议人工复核。")
            continue
        start = int(stage["start"])
        end = int(stage["end"])
        motion_mean = finite_or_nanmean(qd_norm[start : end + 1])
        twist_mean = finite_or_nanmean(twist_norm[start : end + 1])
        force_mean = finite_or_nanmean(force_smooth[start : end + 1])
        notes.append(
            f"- `{STAGE_LABELS[stage_name]}`：样本 `{start} -> {end}`，"
            f"关节运动均值 `{motion_mean:.4f}`，TCP 运动均值 `{twist_mean:.4f}`，力幅值均值 `{force_mean:.4f}`，"
            f"可信度 `{stage['confidence']}`。{stage['reason']}"
        )
    return notes


def assess_data_reasonableness(
    tracking_rmse: list[float],
    velocity_metrics: list[dict[str, float]],
    stages: dict[str, dict[str, object]],
    strongest_joint_pairs: list[tuple[int, int, float]],
    strongest_tcp_pairs: list[tuple[int, int, float]],
) -> list[str]:
    notes: list[str] = []
    rmse_max = float(np.nanmax(np.array(tracking_rmse)))
    if rmse_max < 0.002:
        notes.append(f"- 关节跟踪整体稳定，最大 RMSE 为 `{rmse_max:.6f}`。")
    else:
        notes.append(f"- 关节跟踪存在可见偏差，最大 RMSE 为 `{rmse_max:.6f}`，建议结合原始控制策略复核。")

    diff_values = np.array([metric["diff_std"] for metric in velocity_metrics], dtype=float)
    max_joint = int(np.nanargmax(diff_values))
    notes.append(f"- `J{max_joint}` 的局部速度波动最强，差分标准差为 `{diff_values[max_joint]:.6f}`。")

    if strongest_joint_pairs:
        pair = strongest_joint_pairs[0]
        notes.append(
            f"- 关节-载荷主耦合为 `Act_qd{pair[0]}` 与 `{WRENCH_LABELS[pair[1]]}`，`r={pair[2]:.4f}`。"
        )
    if strongest_tcp_pairs:
        pair = strongest_tcp_pairs[0]
        notes.append(f"- TCP-载荷主耦合为 `{TCP_TWIST_LABELS[pair[0]]}` 与 `{WRENCH_LABELS[pair[1]]}`，`r={pair[2]:.4f}`。")

    missing = [STAGE_LABELS[name] for name in STAGE_ORDER if not stages[name]["present"]]
    if missing:
        notes.append(f"- 阶段识别存在缺失：`{', '.join(missing)}`。该结果仍可用，但建议后期人工微调。")
    else:
        notes.append("- 四类阶段均已识别，分段结构完整。")
    return notes


def write_session_summary(
    session_name: str,
    output_dir: Path,
    row_count: int,
    tracking_rmse: list[float],
    velocity_metrics: list[dict[str, float]],
    strongest_joint_pairs: list[tuple[int, int, float]],
    strongest_tcp_pairs: list[tuple[int, int, float]],
    stages: dict[str, dict[str, object]],
    qd_norm: np.ndarray,
    twist_norm: np.ndarray,
    force_smooth: np.ndarray,
) -> dict[str, object]:
    lines = [
        f"# {session_name} 多数据耦合分析报告",
        "",
        "## 1. 数据含义",
        "",
        "- `Act_q0..Act_q5`：六个关节的实际关节角。",
        "- `Tgt_q0..Tgt_q5`：六个关节的目标角度，用于评估跟踪误差。",
        "- `Act_qd0..Act_qd5`：六个关节的实际角速度，是平滑性和阶段切换的主运动信号。",
        "- `Act_X/Y/Z` 与 `Act_RX/RY/RZ`：TCP 位置与姿态，用于描述末端空间状态。",
        "- `Act_dX/dY/dZ` 与 `Act_dRX/dRY/dRZ`：TCP 线速度与角速度，用于描述末端空间运动强度。",
        "- `Fx/Fy/Fz/Mx/My/Mz`：末端六维载荷，用于描述接触、装载、回撤和称重过程中的响应。",
        "",
        "## 2. 数据合理性判断",
        "",
    ]
    lines.extend(assess_data_reasonableness(tracking_rmse, velocity_metrics, stages, strongest_joint_pairs, strongest_tcp_pairs))
    lines.extend(
        [
            "",
            "## 3. 阶段分段结果",
            "",
            "| Stage | Status | Sample Range | Confidence |",
            "| --- | --- | --- | --- |",
        ]
    )
    for stage_name in STAGE_ORDER:
        stage = stages[stage_name]
        status = "identified" if stage["present"] else "missing"
        sample_range = (
            f"{int(stage['start'])} -> {int(stage['end'])}" if stage["present"] else "N/A"
        )
        lines.append(f"| {STAGE_LABELS[stage_name]} | {status} | {sample_range} | {stage['confidence']} |")
    lines.extend(["", *stage_reasonableness(stages, qd_norm, twist_norm, force_smooth)])

    current_peaks = [metric["diff_std"] for metric in velocity_metrics]
    dominant_joint = int(np.nanargmax(np.array(current_peaks)))
    lines.extend(
        [
            "",
            "## 4. 平滑性与耦合摘要",
            "",
            f"- 样本总数：`{row_count}`",
            f"- 最大关节跟踪 RMSE：`{float(np.nanmax(np.array(tracking_rmse))):.6f}`",
            f"- 局部波动最强关节：`J{dominant_joint}`，其 `Diff SD={current_peaks[dominant_joint]:.6f}`。",
            "",
            "| Rank | 关节-载荷耦合 | Pearson r |",
            "| --- | --- | ---: |",
        ]
    )
    for rank, (joint_idx, wrench_idx, corr_value) in enumerate(strongest_joint_pairs[:6], start=1):
        lines.append(f"| {rank} | `Act_qd{joint_idx}` vs `{WRENCH_LABELS[wrench_idx]}` | {corr_value:.4f} |")

    lines.extend(
        [
            "",
            "| Rank | TCP-载荷耦合 | Pearson r |",
            "| --- | --- | ---: |",
        ]
    )
    for rank, (tcp_idx, wrench_idx, corr_value) in enumerate(strongest_tcp_pairs[:6], start=1):
        lines.append(f"| {rank} | `{TCP_TWIST_LABELS[tcp_idx]}` vs `{WRENCH_LABELS[wrench_idx]}` | {corr_value:.4f} |")

    lines.extend(
        [
            "",
            "## 5. 输出文件",
            "",
            "- `main_figure.png / .svg`：主图",
            "- `supplementary_figure.png / .svg`：补充图",
        ]
    )

    (output_dir / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    status_text = ",".join(
        f"{STAGE_LABELS[name]}:{'yes' if stages[name]['present'] else 'no'}" for name in STAGE_ORDER
    )
    completeness = "四阶段完整" if all(stages[name]["present"] for name in STAGE_ORDER) else "存在缺失阶段"
    strongest_joint = strongest_joint_pairs[0] if strongest_joint_pairs else None
    strongest_tcp = strongest_tcp_pairs[0] if strongest_tcp_pairs else None
    if strongest_joint is not None and strongest_tcp is not None:
        headline = (
            f"{completeness}；J{int(np.nanargmax(np.array(current_peaks)))} 波动最强；"
            f"关节主耦合 Act_qd{strongest_joint[0]}-{WRENCH_LABELS[strongest_joint[1]]}={strongest_joint[2]:.3f}；"
            f"TCP 主耦合 {TCP_TWIST_LABELS[strongest_tcp[0]]}-{WRENCH_LABELS[strongest_tcp[1]]}={strongest_tcp[2]:.3f}"
        )
    else:
        headline = completeness

    return {
        "session_name": session_name,
        "stage_status": status_text,
        "headline": headline,
        "output_dir": str(output_dir.relative_to(ROOT)),
    }


def write_overview_markdown(results: list[dict[str, object]], failures: list[tuple[str, str]], summary_md: Path) -> None:
    lines = [
        "# Data 目录批量多数据耦合分析汇总",
        "",
        "## 1. 会话概览",
        "",
        "| Session | 阶段识别状态 | 合理性摘要 | Output |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result['session_name']} | {result['stage_status']} | {result['headline']} | `{result['output_dir']}` |"
        )
    if failures:
        lines.extend(
            [
                "",
                "## 2. 失败会话",
                "",
                "| Session | Error |",
                "| --- | --- |",
            ]
        )
        for session_name, error in failures:
            lines.append(f"| {session_name} | {error} |")
    notes_section = "## 3. 说明" if failures else "## 2. 说明"
    lines.extend(
        [
            "",
            notes_section,
            "",
            "- 图面不显示会话目录名、绝对时间和 strongest-pair 说明文本。",
            "- 主图与补充图统一采用样本序号横轴。",
            "- 若某阶段边界不清晰，允许缺失并在报告中显式说明。",
            "- 中文字体采用 `AR PL SungtiL GB + DejaVu Sans + Arial`。",
        ]
    )
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_session(session_dir: Path, output_root: Path, rolling_window: int) -> dict[str, object]:
    session_name = session_dir.name
    output_dir = output_root / session_name
    output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_old_outputs(output_dir)

    data = load_session_data(session_dir / CSV_NAME)
    time = data[TIME_FIELD]
    if time.size == 0 or not np.isfinite(time).any():
        raise RuntimeError("Time column has no finite samples.")

    mask = np.isfinite(time)
    time = time[mask]
    sample_index = np.arange(mask.sum(), dtype=int)
    row_count = int(mask.sum())
    act_q = np.vstack([data[field][mask] for field in JOINT_POSITION_FIELDS])
    tgt_q = np.vstack([data[field][mask] for field in JOINT_TARGET_FIELDS])
    velocity = np.vstack([data[field][mask] for field in JOINT_VELOCITY_FIELDS])
    current = np.vstack([data[field][mask] for field in JOINT_CURRENT_FIELDS])
    tcp_pose = np.vstack([data[field][mask] for field in TCP_POSE_FIELDS])
    tcp_twist = np.vstack([data[field][mask] for field in TCP_TWIST_FIELDS])
    wrench = np.vstack([data[field][mask] for field in WRENCH_FIELDS])

    qd_norm = np.linalg.norm(np.nan_to_num(velocity), axis=0)
    twist_norm = np.linalg.norm(np.nan_to_num(tcp_twist), axis=0)
    force_mag = np.linalg.norm(np.nan_to_num(wrench[:3], copy=True) if wrench.shape[0] >= 3 else np.nan_to_num(wrench), axis=0)
    force_smooth = rolling_mean(force_mag, rolling_window)

    tracking_rmse = compute_tracking_rmse(act_q, tgt_q)
    velocity_metrics = compute_velocity_metrics(time, velocity)
    joint_wrench_corr = compute_matrix_corr(velocity, wrench)
    tcp_wrench_corr = compute_matrix_corr(tcp_twist, wrench)
    joint_tcp_corr = compute_matrix_corr(velocity, tcp_twist)
    strongest_joint_pairs = extract_strongest_pairs(joint_wrench_corr)
    strongest_tcp_pairs = extract_strongest_pairs(tcp_wrench_corr)
    stages = detect_stages(session_name, qd_norm, twist_norm, force_mag, force_smooth)

    plot_main_figure(
        sample_index=sample_index,
        act_q=act_q,
        tgt_q=tgt_q,
        velocity=velocity,
        tcp_twist=tcp_twist,
        qd_norm=qd_norm,
        twist_norm=twist_norm,
        force_smooth=force_smooth,
        joint_wrench_corr=joint_wrench_corr,
        tcp_wrench_corr=tcp_wrench_corr,
        stages=stages,
        output_dir=output_dir,
    )
    plot_supplementary_figure(
        sample_index=sample_index,
        tcp_pose=tcp_pose,
        tcp_twist=tcp_twist,
        joint_tcp_corr=joint_tcp_corr,
        qd_norm=qd_norm,
        twist_norm=twist_norm,
        force_mag=force_mag,
        stages=stages,
        output_dir=output_dir,
    )

    return write_session_summary(
        session_name=session_name,
        output_dir=output_dir,
        row_count=row_count,
        tracking_rmse=tracking_rmse,
        velocity_metrics=velocity_metrics,
        strongest_joint_pairs=strongest_joint_pairs,
        strongest_tcp_pairs=strongest_tcp_pairs,
        stages=stages,
        qd_norm=qd_norm,
        twist_norm=twist_norm,
        force_smooth=force_smooth,
    )


def main() -> int:
    args = parse_args()
    apply_publication_style()
    session_dirs = find_session_dirs(args.data_root.resolve())
    if not session_dirs:
        raise RuntimeError(f"No session directories with {CSV_NAME} found under {args.data_root}")

    results: list[dict[str, object]] = []
    failures: list[tuple[str, str]] = []
    print(f"Found {len(session_dirs)} session folders under {args.data_root.resolve()}")
    for session_dir in session_dirs:
        try:
            result = analyze_session(session_dir=session_dir, output_root=args.output_root.resolve(), rolling_window=args.rolling_window)
            results.append(result)
            print(f"{result['session_name']}: stages={result['stage_status']}")
        except Exception as exc:  # pragma: no cover
            failures.append((session_dir.name, str(exc)))
            print(f"{session_dir.name}: FAILED - {exc}")

    write_overview_markdown(results, failures, args.summary_md.resolve())
    print(f"Overview markdown written to: {args.summary_md.resolve()}")
    print(f"Successful analyses: {len(results)} / {len(session_dirs)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
