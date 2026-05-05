from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "2026-05-01_19-57-41"
OUTPUT_DIR = ROOT / "test_skills" / "output"

PALETTE_NMI_PASTEL = {
    "baseline_dark": "#484878",
    "baseline_mid": "#7884B4",
    "baseline_soft": "#B4C0E4",
    "ours_tiny": "#E4E4F0",
    "ours_base": "#E4CCD8",
    "ours_large": "#F0C0CC",
    "delta_up": "#2E9E44",
    "delta_down": "#E53935",
    "neutral_dark": "#606060",
}


def apply_publication_style(font_size: int = 15, axes_linewidth: float = 2.0) -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.size"] = font_size
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.linewidth"] = axes_linewidth
    plt.rcParams["legend.frameon"] = False


def add_panel_label(ax, label: str, x: float = -0.08, y: float = 1.02) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=14,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str) -> float:
    if value in ("", "nan", "NaN", "None"):
        return math.nan
    return float(value)


def rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) == 0:
        return values
    window = max(1, min(window, len(values)))
    kernel = np.ones(window) / window
    padded = np.pad(values, (window // 2, window - 1 - window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def export_figure(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_robot_force_figure(rows: list[dict[str, str]]) -> None:
    valid_rows = [row for row in rows if math.isfinite(to_float(row["Fx"]))]
    t0 = float(valid_rows[0]["epoch_time"])
    time_s = np.array([float(row["epoch_time"]) - t0 for row in valid_rows])
    fx = np.array([to_float(row["Fx"]) for row in valid_rows])
    fy = np.array([to_float(row["Fy"]) for row in valid_rows])
    fz = np.array([to_float(row["Fz"]) for row in valid_rows])
    mz = np.array([to_float(row["Mz"]) for row in valid_rows])
    act_z = np.array([to_float(row["Act_Z"]) for row in valid_rows]) * 1000.0
    robot_current = np.array([to_float(row["Robot_Current"]) for row in valid_rows])
    robot_current_delta = robot_current - np.mean(robot_current)
    force_mag = np.sqrt(fx**2 + fy**2 + fz**2)

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 8.2), sharex=True)

    axes[0].plot(time_s, fx, color=PALETTE_NMI_PASTEL["baseline_dark"], lw=1.8, label="Fx")
    axes[0].plot(time_s, fy, color=PALETTE_NMI_PASTEL["baseline_mid"], lw=1.8, label="Fy")
    axes[0].plot(time_s, fz, color=PALETTE_NMI_PASTEL["ours_base"], lw=1.8, label="Fz")
    axes[0].set_ylabel("Force (N)")
    axes[0].legend(loc="upper right", ncol=3)
    axes[0].set_title("UR10 + FT300 force profile")
    add_panel_label(axes[0], "a")

    axes[1].plot(
        time_s,
        rolling_mean(force_mag, 35),
        color=PALETTE_NMI_PASTEL["ours_large"],
        lw=2.5,
        label="|F| rolling mean",
    )
    axes[1].plot(
        time_s,
        rolling_mean(np.abs(mz), 35),
        color=PALETTE_NMI_PASTEL["neutral_dark"],
        lw=1.8,
        label="|Mz| rolling mean",
    )
    axes[1].set_ylabel("Magnitude")
    axes[1].legend(loc="upper right")
    add_panel_label(axes[1], "b")

    axes[2].plot(time_s, act_z, color=PALETTE_NMI_PASTEL["baseline_soft"], lw=2.0, label="TCP Z")
    axes[2].set_ylabel("TCP Z (mm)")
    axes[2].set_xlabel("Time since first valid FT sample (s)")
    twin = axes[2].twinx()
    twin.plot(
        time_s,
        rolling_mean(robot_current_delta, 45),
        color=PALETTE_NMI_PASTEL["delta_up"],
        lw=1.8,
        label="Robot current delta",
    )
    twin.set_ylabel("Current delta (A)")
    twin.ticklabel_format(axis="y", style="plain", useOffset=False)
    lines, labels = axes[2].get_legend_handles_labels()
    lines2, labels2 = twin.get_legend_handles_labels()
    axes[2].legend(lines + lines2, labels + labels2, loc="upper right")
    add_panel_label(axes[2], "c")

    fig.tight_layout()
    export_figure(fig, "figure_01_robot_force_profile")


def build_camera_figure(rows: list[dict[str, str]]) -> None:
    frame_id = np.array([float(row["frame_id"]) for row in rows])
    fps = np.array([to_float(row["fps"]) for row in rows])
    depth_mean = np.array([to_float(row["depth_mean"]) for row in rows])
    depth_std = np.array([to_float(row["depth_std"]) for row in rows])
    depth_min = np.array([to_float(row["depth_min"]) for row in rows])
    depth_max = np.array([to_float(row["depth_max"]) for row in rows])
    depth_max_clipped = np.minimum(depth_max, np.percentile(depth_max, 95))

    fig, axes = plt.subplots(2, 1, figsize=(9.0, 6.8), sharex=True)

    axes[0].plot(frame_id, fps, color=PALETTE_NMI_PASTEL["baseline_dark"], lw=1.6, alpha=0.55)
    axes[0].plot(
        frame_id,
        rolling_mean(fps, 7),
        color=PALETTE_NMI_PASTEL["ours_base"],
        lw=2.8,
        label="FPS rolling mean",
    )
    axes[0].axhline(30.0, color=PALETTE_NMI_PASTEL["neutral_dark"], ls="--", lw=1.2, label="Target 30 FPS")
    axes[0].set_ylabel("FPS")
    axes[0].legend(loc="lower left")
    axes[0].set_title("Camera throughput and depth stability")
    add_panel_label(axes[0], "a")

    axes[1].fill_between(
        frame_id,
        depth_mean - depth_std,
        depth_mean + depth_std,
        color=PALETTE_NMI_PASTEL["ours_tiny"],
        alpha=0.9,
        label="mean ± std",
    )
    axes[1].plot(frame_id, depth_mean, color=PALETTE_NMI_PASTEL["baseline_mid"], lw=2.2, label="Depth mean")
    axes[1].plot(frame_id, depth_min, color=PALETTE_NMI_PASTEL["delta_up"], lw=1.0, alpha=0.7, label="Depth min")
    axes[1].plot(
        frame_id,
        depth_max_clipped,
        color=PALETTE_NMI_PASTEL["delta_down"],
        lw=1.0,
        alpha=0.7,
        label="Depth max (p95 clipped)",
    )
    axes[1].set_ylabel("Depth (mm)")
    axes[1].set_xlabel("Frame ID")
    axes[1].legend(loc="upper right", ncol=2)
    add_panel_label(axes[1], "b")

    fig.tight_layout()
    export_figure(fig, "figure_02_camera_depth_profile")


def build_summary_figure(
    robot_rows: list[dict[str, str]],
    camera_rows: list[dict[str, str]],
    camera_config: dict[str, object],
    camera_intrinsics: dict[str, object],
) -> None:
    valid_robot = [row for row in robot_rows if math.isfinite(to_float(row["Fx"]))]
    sample = np.linspace(0, len(valid_robot) - 1, min(450, len(valid_robot))).astype(int)

    feature_names = ["Fx", "Fy", "Fz", "Mz", "Act_Z", "Robot_Current"]
    feature_matrix = np.array(
        [[to_float(valid_robot[i][name]) for name in feature_names] for i in sample],
        dtype=float,
    )
    corr = np.corrcoef(feature_matrix.T)

    force_stats = {
        "Fx": np.mean(np.abs(feature_matrix[:, 0])),
        "Fy": np.mean(np.abs(feature_matrix[:, 1])),
        "Fz": np.mean(np.abs(feature_matrix[:, 2])),
        "Mz": np.mean(np.abs(feature_matrix[:, 3])),
    }
    fps = np.array([to_float(row["fps"]) for row in camera_rows])
    depth_mean = np.array([to_float(row["depth_mean"]) for row in camera_rows])

    fig = plt.figure(figsize=(11.2, 7.4), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.15], height_ratios=[1.0, 1.0], wspace=0.28, hspace=0.3)

    ax_bar = fig.add_subplot(gs[0, 0])
    labels = list(force_stats.keys())
    values = [force_stats[key] for key in labels]
    colors = [
        PALETTE_NMI_PASTEL["baseline_dark"],
        PALETTE_NMI_PASTEL["baseline_mid"],
        PALETTE_NMI_PASTEL["ours_base"],
        PALETTE_NMI_PASTEL["neutral_dark"],
    ]
    bars = ax_bar.bar(labels, values, color=colors, edgecolor="black", linewidth=1.0)
    ax_bar.set_ylabel("Mean absolute value")
    ax_bar.set_title("Robot channel summary")
    for bar, value in zip(bars, values):
        ax_bar.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    add_panel_label(ax_bar, "a")

    ax_heat = fig.add_subplot(gs[:, 1])
    im = ax_heat.imshow(corr, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    ax_heat.set_xticks(range(len(feature_names)), feature_names, rotation=35, ha="right")
    ax_heat.set_yticks(range(len(feature_names)), feature_names)
    ax_heat.set_title("Cross-sensor correlation heatmap")
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            color = "white" if abs(corr[i, j]) > 0.45 else "black"
            ax_heat.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", color=color, fontsize=9)
    fig.colorbar(im, ax=ax_heat, fraction=0.046, pad=0.04)
    add_panel_label(ax_heat, "b")

    ax_text = fig.add_subplot(gs[1, 0])
    ax_text.axis("off")
    summary_lines = [
        "Session snapshot",
        f"Robot samples: {len(robot_rows)}",
        f"Camera frames: {len(camera_rows)}",
        f"Camera FPS target: {camera_config['fps']}",
        f"Depth resolution: {camera_config['depth_resolution'][0]} x {camera_config['depth_resolution'][1]}",
        f"Color resolution: {camera_config['color_resolution'][0]} x {camera_config['color_resolution'][1]}",
        f"Intrinsics fx/fy: {camera_intrinsics['fx']:.1f} / {camera_intrinsics['fy']:.1f}",
        f"Observed FPS mean: {np.mean(fps):.2f}",
        f"Observed depth mean: {np.mean(depth_mean):.1f} mm",
    ]
    ax_text.text(
        0.0,
        1.0,
        "\n".join(summary_lines),
        va="top",
        ha="left",
        fontsize=12,
        linespacing=1.5,
        bbox={"facecolor": "#F7F4F8", "edgecolor": "#D8D8D8", "boxstyle": "round,pad=0.6"},
    )
    add_panel_label(ax_text, "c", x=-0.02, y=1.02)

    export_figure(fig, "figure_03_session_summary")


def main() -> None:
    apply_publication_style()
    robot_rows = load_csv_rows(DATA_DIR / "ur10_ft300_realtime_data.csv")
    camera_rows = load_csv_rows(DATA_DIR / "camera_meta.csv")
    with (DATA_DIR / "camera_config.json").open() as handle:
        camera_config = json.load(handle)
    with (DATA_DIR / "camera_intrinsics.json").open() as handle:
        camera_intrinsics = json.load(handle)

    build_robot_force_figure(robot_rows)
    build_camera_figure(camera_rows)
    build_summary_figure(robot_rows, camera_rows, camera_config, camera_intrinsics)

    generated = sorted(path.name for path in OUTPUT_DIR.iterdir() if path.is_file())
    print("Generated files:")
    for name in generated:
        print(name)


if __name__ == "__main__":
    main()
