#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_DIR = ROOT / "data" / "2026-05-01_19-57-41"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "analysis" / "output"
DEFAULT_MODEL_FILE = Path("/root/ur10_ws/src/ur_base_xarco_model/assembly_xacro/assembly/assembly.urdf.xacro")
CSV_NAME = "ur10_ft300_realtime_data.csv"
JOINT_FIELDS = [f"Tgt_q{i}" for i in range(6)]
FORCE_FIELDS = ["Fx", "Fy", "Fz"]
POSE_FIELDS = ["Act_X", "Act_Y", "Act_Z", "Act_RX", "Act_RY", "Act_RZ"]
GRAVITY = 9.80665
DEFAULT_JOINT_THRESHOLD = 5e-4
DEFAULT_MIN_STABLE_SAMPLES = 50
DEFAULT_ROLLING_WINDOW = 35
DEFAULT_WEIGHT_AXIS_MODE = "base_z"
DEFAULT_REFERENCE_MODE = "low_load_candidate"
DEFAULT_TCP_FRAME = "sensor_shovel_shovel_tcp"
DEFAULT_SENSOR_FRAME = "sensor_shovel"
DEFAULT_REFERENCE_LOOKBACK_S = 4.0
DEFAULT_REFERENCE_WINDOW_SAMPLES = 60
DEFAULT_REFERENCE_MIN_GAP_S = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze FT300 shovel data with gravity-axis projection and robust reference selection."
    )
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR)
    parser.add_argument("--joint-threshold", type=float, default=DEFAULT_JOINT_THRESHOLD)
    parser.add_argument("--min-stable-samples", type=int, default=DEFAULT_MIN_STABLE_SAMPLES)
    parser.add_argument("--rolling-window", type=int, default=DEFAULT_ROLLING_WINDOW)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--weight-axis-mode", choices=["base_z", "magnitude"], default=DEFAULT_WEIGHT_AXIS_MODE)
    parser.add_argument(
        "--reference-mode",
        choices=["low_load_candidate", "pre_final_stable"],
        default=DEFAULT_REFERENCE_MODE,
    )
    parser.add_argument("--model-file", type=Path, default=DEFAULT_MODEL_FILE)
    parser.add_argument("--tcp-frame-name", default=DEFAULT_TCP_FRAME)
    parser.add_argument("--sensor-frame-name", default=DEFAULT_SENSOR_FRAME)
    parser.add_argument("--reference-lookback-s", type=float, default=DEFAULT_REFERENCE_LOOKBACK_S)
    parser.add_argument("--reference-window-samples", type=int, default=DEFAULT_REFERENCE_WINDOW_SAMPLES)
    parser.add_argument("--reference-min-gap-s", type=float, default=DEFAULT_REFERENCE_MIN_GAP_S)
    return parser.parse_args()


def to_float(value: str | None) -> float:
    if value in ("", "nan", "NaN", "None", None):
        return math.nan
    return float(value)


def is_finite_number(value: Any) -> bool:
    return math.isfinite(float(value))


def finite_mean(values: list[float]) -> float:
    valid = [value for value in values if math.isfinite(value)]
    if not valid:
        return math.nan
    return float(np.mean(valid))


def finite_std(values: list[float]) -> float:
    valid = [value for value in values if math.isfinite(value)]
    if len(valid) <= 1:
        return 0.0 if valid else math.nan
    return float(np.std(valid))


def rpy_to_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def rotvec_to_matrix(rotvec: np.ndarray) -> np.ndarray:
    theta = float(np.linalg.norm(rotvec))
    if theta < 1e-12:
        return np.eye(3)
    axis = rotvec / theta
    skew = np.array(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ]
    )
    return np.eye(3) + math.sin(theta) * skew + (1.0 - math.cos(theta)) * (skew @ skew)


def extract_fixed_joint_rpy(model_text: str, parent_link: str, child_link: str) -> tuple[float, float, float]:
    joint_pattern = re.compile(r"<joint\s+name=\"[^\"]+\"[^>]*type=\"fixed\"[^>]*>(.*?)</joint>", re.DOTALL)
    parent_pattern = re.compile(r"<parent\s+link=\"([^\"]+)\"\s*/?>")
    child_pattern = re.compile(r"<child\s+link=\"([^\"]+)\"\s*/?>")
    origin_pattern = re.compile(r"<origin[^>]*rpy=\"([^\"]+)\"")

    for block in joint_pattern.findall(model_text):
        parent_match = parent_pattern.search(block)
        child_match = child_pattern.search(block)
        if not parent_match or not child_match:
            continue
        if parent_match.group(1) != parent_link or child_match.group(1) != child_link:
            continue
        origin_match = origin_pattern.search(block)
        if not origin_match:
            return (0.0, 0.0, 0.0)
        return tuple(float(value) for value in origin_match.group(1).split())
    raise RuntimeError(f"Could not find fixed joint from '{parent_link}' to '{child_link}' in model file.")


def load_model_rotation(model_file: Path, tcp_frame_name: str, sensor_frame_name: str) -> np.ndarray:
    model_text = model_file.read_text(encoding="utf-8")
    sensor_to_tcp_rpy = extract_fixed_joint_rpy(model_text, sensor_frame_name, tcp_frame_name)
    rotation_sensor_to_tcp = rpy_to_matrix(*sensor_to_tcp_rpy)
    return rotation_sensor_to_tcp.T


def load_rows(csv_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row_idx, row in enumerate(csv.DictReader(handle)):
            forces = [to_float(row[field]) for field in FORCE_FIELDS]
            if not all(math.isfinite(value) for value in forces):
                continue

            parsed: dict[str, object] = {
                "row_index": row_idx,
                "epoch_time": to_float(row["epoch_time"]),
                "Time": to_float(row["Time"]),
                "Fx": forces[0],
                "Fy": forces[1],
                "Fz": forces[2],
                "Mx": to_float(row["Mx"]),
                "My": to_float(row["My"]),
                "Mz": to_float(row["Mz"]),
                "ur_fresh": int(float(row.get("ur_fresh", "0"))),
                "ft_fresh": int(float(row.get("ft_fresh", "0"))),
            }
            for field in JOINT_FIELDS + POSE_FIELDS:
                parsed[field] = to_float(row[field])
            rows.append(parsed)
    return rows


def compute_force_features(rows: list[dict[str, object]], rotation_tcp_to_sensor: np.ndarray) -> None:
    for row in rows:
        force_sensor = np.array([float(row[field]) for field in FORCE_FIELDS], dtype=float)
        row["force_magnitude"] = float(np.linalg.norm(force_sensor))
        if not all(is_finite_number(row[field]) for field in ("Act_RX", "Act_RY", "Act_RZ")):
            row["force_base_x"] = math.nan
            row["force_base_y"] = math.nan
            row["force_base_z"] = math.nan
            continue
        rotation_base_tcp = rotvec_to_matrix(
            np.array([float(row["Act_RX"]), float(row["Act_RY"]), float(row["Act_RZ"])], dtype=float)
        )
        rotation_base_sensor = rotation_base_tcp @ rotation_tcp_to_sensor
        force_base = rotation_base_sensor @ force_sensor
        row["force_base_x"] = float(force_base[0])
        row["force_base_y"] = float(force_base[1])
        row["force_base_z"] = float(force_base[2])


def detect_stable_segments(
    rows: list[dict[str, object]],
    joint_threshold: float,
    min_stable_samples: int,
) -> tuple[list[bool], list[tuple[int, int]]]:
    if not rows:
        return [], []

    stable_flags = [False] * len(rows)
    stable_flags[0] = True
    for idx in range(1, len(rows)):
        if not all(is_finite_number(rows[idx][field]) and is_finite_number(rows[idx - 1][field]) for field in JOINT_FIELDS):
            stable_flags[idx] = False
            continue
        stable_flags[idx] = all(
            abs(float(rows[idx][field]) - float(rows[idx - 1][field])) <= joint_threshold for field in JOINT_FIELDS
        )

    segments: list[tuple[int, int]] = []
    idx = 0
    while idx < len(stable_flags):
        if not stable_flags[idx]:
            idx += 1
            continue
        start_idx = idx
        idx += 1
        while idx < len(stable_flags) and stable_flags[idx]:
            idx += 1
        end_idx = idx - 1
        if end_idx - start_idx + 1 >= min_stable_samples:
            segments.append((start_idx, end_idx))
        else:
            for reject_idx in range(start_idx, end_idx + 1):
                stable_flags[reject_idx] = False
    return stable_flags, segments


def summarize_segment_rows(segment_rows: list[dict[str, object]]) -> dict[str, float]:
    return {
        "avg_fx": finite_mean([float(row["Fx"]) for row in segment_rows]),
        "avg_fy": finite_mean([float(row["Fy"]) for row in segment_rows]),
        "avg_fz": finite_mean([float(row["Fz"]) for row in segment_rows]),
        "avg_mx": finite_mean([float(row["Mx"]) for row in segment_rows]),
        "avg_my": finite_mean([float(row["My"]) for row in segment_rows]),
        "avg_mz": finite_mean([float(row["Mz"]) for row in segment_rows]),
        "avg_force_magnitude": finite_mean([float(row["force_magnitude"]) for row in segment_rows]),
        "avg_force_base_x": finite_mean([float(row["force_base_x"]) for row in segment_rows]),
        "avg_force_base_y": finite_mean([float(row["force_base_y"]) for row in segment_rows]),
        "avg_force_base_z": finite_mean([float(row["force_base_z"]) for row in segment_rows]),
        "std_force_base_z": finite_std([float(row["force_base_z"]) for row in segment_rows]),
    }


def summarize_segments(rows: list[dict[str, object]], segments: list[tuple[int, int]]) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for segment_id, (start_idx, end_idx) in enumerate(segments):
        segment_rows = rows[start_idx : end_idx + 1]
        start_row = segment_rows[0]
        end_row = segment_rows[-1]
        metrics = summarize_segment_rows(segment_rows)
        tgt_mean = np.array([finite_mean([float(row[field]) for row in segment_rows]) for field in JOINT_FIELDS], dtype=float)
        summary: dict[str, object] = {
            "segment_id": segment_id,
            "segment_label": f"S{segment_id}",
            "segment_type": "stable_segment",
            "start_sample_index": start_idx,
            "end_sample_index": end_idx,
            "start_row_index": int(start_row["row_index"]),
            "end_row_index": int(end_row["row_index"]),
            "start_epoch_time": float(start_row["epoch_time"]),
            "end_epoch_time": float(end_row["epoch_time"]),
            "start_time": float(start_row["Time"]),
            "end_time": float(end_row["Time"]),
            "sample_count": len(segment_rows),
            "duration_s": float(end_row["epoch_time"]) - float(start_row["epoch_time"]),
            "mean_tgt_q_vector": tgt_mean,
            "pose_distance_to_final": math.nan,
            "reference_score": math.nan,
            "reference_rejected_reason": "",
            "is_reference_segment": False,
            "is_final_measurement_segment": False,
            "is_window_reference": False,
            "estimated_mass_g_from_base_z": math.nan,
            "delta_force_base_z_to_reference": math.nan,
            "delta_force_magnitude_to_reference": math.nan,
            **metrics,
        }
        summaries.append(summary)
    return summaries


def build_reference_window_summary(
    rows: list[dict[str, object]],
    start_idx: int,
    end_idx: int,
) -> dict[str, object]:
    window_rows = rows[start_idx : end_idx + 1]
    start_row = window_rows[0]
    end_row = window_rows[-1]
    metrics = summarize_segment_rows(window_rows)
    tgt_mean = np.array([finite_mean([float(row[field]) for row in window_rows]) for field in JOINT_FIELDS], dtype=float)
    return {
        "segment_id": "window_reference",
        "segment_label": "W_REF",
        "segment_type": "window_reference",
        "start_sample_index": start_idx,
        "end_sample_index": end_idx,
        "start_row_index": int(start_row["row_index"]),
        "end_row_index": int(end_row["row_index"]),
        "start_epoch_time": float(start_row["epoch_time"]),
        "end_epoch_time": float(end_row["epoch_time"]),
        "start_time": float(start_row["Time"]),
        "end_time": float(end_row["Time"]),
        "sample_count": len(window_rows),
        "duration_s": float(end_row["epoch_time"]) - float(start_row["epoch_time"]),
        "mean_tgt_q_vector": tgt_mean,
        "pose_distance_to_final": math.nan,
        "reference_score": math.nan,
        "reference_rejected_reason": "",
        "is_reference_segment": True,
        "is_final_measurement_segment": False,
        "is_window_reference": True,
        "estimated_mass_g_from_base_z": 0.0,
        "delta_force_base_z_to_reference": 0.0,
        "delta_force_magnitude_to_reference": 0.0,
        **metrics,
    }


def get_final_segment_index(segment_summaries: list[dict[str, object]]) -> int:
    for idx in range(len(segment_summaries) - 1, -1, -1):
        if is_finite_number(segment_summaries[idx]["avg_force_base_z"]):
            return idx
    raise RuntimeError("No stable segment has finite projected force values.")


def score_stable_reference_candidate(
    summary: dict[str, object],
    final_summary: dict[str, object],
) -> tuple[bool, float, str]:
    if not is_finite_number(summary["avg_force_base_z"]):
        return False, math.inf, "non_finite_base_z"

    pose_dist = float(summary["pose_distance_to_final"])
    base_z_gap = abs(float(summary["avg_force_base_z"]) - float(final_summary["avg_force_base_z"]))
    mag_gap = abs(float(summary["avg_force_magnitude"]) - float(final_summary["avg_force_magnitude"]))
    time_gap = max(0.0, float(final_summary["start_time"]) - float(summary["end_time"]))
    std_base_z = float(summary["std_force_base_z"])

    if base_z_gap > 12.0 and pose_dist > 0.45:
        return False, math.inf, "high_load_pose_mismatch"
    if mag_gap > 12.0 and pose_dist > 0.45:
        return False, math.inf, "force_magnitude_mismatch"
    if time_gap > 8.0:
        return False, math.inf, "too_far_from_final"

    score = pose_dist * 3.0 + base_z_gap * 0.35 + mag_gap * 0.2 + time_gap * 0.08 + std_base_z * 0.8
    return True, score, ""


def search_reference_window(
    rows: list[dict[str, object]],
    final_summary: dict[str, object],
    lookback_s: float,
    window_samples: int,
    min_gap_s: float,
) -> dict[str, object] | None:
    final_start_idx = int(final_summary["start_sample_index"])
    final_start_time = float(final_summary["start_time"])
    final_tgt = np.array(final_summary["mean_tgt_q_vector"], dtype=float)
    final_base_z = float(final_summary["avg_force_base_z"])
    final_mag = float(final_summary["avg_force_magnitude"])

    candidate_rows = [
        idx
        for idx, row in enumerate(rows[:final_start_idx])
        if is_finite_number(row["Time"]) and final_start_time - float(row["Time"]) <= lookback_s
    ]
    if len(candidate_rows) < window_samples:
        return None

    search_start_idx = candidate_rows[0]
    search_end_idx = candidate_rows[-1] - window_samples + 1
    best: dict[str, object] | None = None
    best_score = math.inf

    for start_idx in range(search_start_idx, search_end_idx + 1):
        end_idx = start_idx + window_samples - 1
        window_rows = rows[start_idx : end_idx + 1]
        if any(not is_finite_number(row["force_base_z"]) for row in window_rows):
            continue
        mean_bz = finite_mean([float(row["force_base_z"]) for row in window_rows])
        std_bz = finite_std([float(row["force_base_z"]) for row in window_rows])
        mean_mag = finite_mean([float(row["force_magnitude"]) for row in window_rows])
        tgt_mean = np.array([finite_mean([float(row[field]) for row in window_rows]) for field in JOINT_FIELDS], dtype=float)
        pose_dist = float(np.linalg.norm(tgt_mean - final_tgt))
        time_gap = max(0.0, final_start_time - float(window_rows[-1]["Time"]))
        base_z_gap = abs(mean_bz - final_base_z)
        mag_gap = abs(mean_mag - final_mag)

        if time_gap < min_gap_s:
            continue
        if pose_dist > 0.9:
            continue
        if std_bz > 2.0:
            continue
        if time_gap > lookback_s:
            continue

        score = pose_dist * 2.5 + base_z_gap * 0.25 + mag_gap * 0.25 + time_gap * 0.1 + std_bz * 1.0
        if score < best_score:
            best_score = score
            best = build_reference_window_summary(rows, start_idx, end_idx)
            best["pose_distance_to_final"] = pose_dist
            best["reference_score"] = score
            best["reference_rejected_reason"] = ""

    return best


def select_reference_and_final(
    rows: list[dict[str, object]],
    segment_summaries: list[dict[str, object]],
    args: argparse.Namespace,
) -> tuple[int, dict[str, object], str, str]:
    final_idx = get_final_segment_index(segment_summaries)
    final_summary = segment_summaries[final_idx]
    final_tgt = np.array(final_summary["mean_tgt_q_vector"], dtype=float)

    accepted_stable_candidates: list[tuple[float, int]] = []
    for idx, summary in enumerate(segment_summaries[:final_idx]):
        pose_dist = float(np.linalg.norm(np.array(summary["mean_tgt_q_vector"]) - final_tgt))
        summary["pose_distance_to_final"] = pose_dist
        accepted, score, reason = score_stable_reference_candidate(summary, final_summary)
        summary["reference_score"] = score if accepted else math.nan
        summary["reference_rejected_reason"] = reason
        if accepted:
            accepted_stable_candidates.append((score, idx))

    if args.reference_mode == "pre_final_stable" and accepted_stable_candidates:
        chosen_idx = accepted_stable_candidates[-1][1]
        segment_summaries[chosen_idx]["is_reference_segment"] = True
        final_summary["is_final_measurement_segment"] = True
        return final_idx, segment_summaries[chosen_idx], "stable_segment", "low"

    reference_window = None
    if args.reference_mode == "low_load_candidate":
        reference_window = search_reference_window(
            rows,
            final_summary,
            args.reference_lookback_s,
            args.reference_window_samples,
            args.reference_min_gap_s,
        )

    best_stable = min(accepted_stable_candidates, default=(math.inf, -1))

    if reference_window is not None and reference_window["reference_score"] <= best_stable[0]:
        final_summary["is_final_measurement_segment"] = True
        risk = "low" if float(reference_window["pose_distance_to_final"]) < 0.5 else "medium"
        return final_idx, reference_window, "window", risk

    if best_stable[1] >= 0:
        chosen_idx = best_stable[1]
        segment_summaries[chosen_idx]["is_reference_segment"] = True
        final_summary["is_final_measurement_segment"] = True
        risk = "low" if float(segment_summaries[chosen_idx]["pose_distance_to_final"]) < 0.5 else "medium"
        return final_idx, segment_summaries[chosen_idx], "stable_segment", risk

    if reference_window is not None:
        final_summary["is_final_measurement_segment"] = True
        return final_idx, reference_window, "window", "medium"

    fallback_idx = max(0, final_idx - 1)
    segment_summaries[fallback_idx]["is_reference_segment"] = True
    segment_summaries[fallback_idx]["reference_rejected_reason"] = "fallback_no_low_load_candidate"
    final_summary["is_final_measurement_segment"] = True
    return final_idx, segment_summaries[fallback_idx], "stable_segment", "high"


def estimate_weight(
    segment_summaries: list[dict[str, object]],
    reference_summary: dict[str, object],
    final_idx: int,
    weight_axis_mode: str,
) -> None:
    final_tgt = np.array(segment_summaries[final_idx]["mean_tgt_q_vector"], dtype=float)
    reference_base_z = float(reference_summary["avg_force_base_z"])
    reference_magnitude = float(reference_summary["avg_force_magnitude"])

    if not is_finite_number(reference_summary["pose_distance_to_final"]):
        reference_summary["pose_distance_to_final"] = float(
            np.linalg.norm(np.array(reference_summary["mean_tgt_q_vector"]) - final_tgt)
        )

    for summary in segment_summaries:
        if not is_finite_number(summary["pose_distance_to_final"]):
            summary["pose_distance_to_final"] = float(np.linalg.norm(np.array(summary["mean_tgt_q_vector"]) - final_tgt))
        delta_base_z = float(summary["avg_force_base_z"]) - reference_base_z
        delta_magnitude = float(summary["avg_force_magnitude"]) - reference_magnitude
        summary["delta_force_base_z_to_reference"] = delta_base_z
        summary["delta_force_magnitude_to_reference"] = delta_magnitude
        summary["estimated_mass_g_from_base_z"] = (
            abs(delta_base_z) / GRAVITY * 1000.0 if weight_axis_mode == "base_z" else delta_magnitude / GRAVITY * 1000.0
        )

    reference_summary["delta_force_base_z_to_reference"] = 0.0
    reference_summary["delta_force_magnitude_to_reference"] = 0.0
    reference_summary["estimated_mass_g_from_base_z"] = 0.0


def mark_reference_rows(
    rows: list[dict[str, object]],
    reference_summary: dict[str, object],
    final_summary: dict[str, object],
) -> None:
    for row in rows:
        row["is_candidate_reference"] = 0
        row["is_reference_segment"] = 0
        row["is_final_measurement_window"] = 0

    ref_start = int(reference_summary["start_sample_index"])
    ref_end = int(reference_summary["end_sample_index"])
    final_start = int(final_summary["start_sample_index"])
    final_end = int(final_summary["end_sample_index"])
    for idx in range(ref_start, ref_end + 1):
        rows[idx]["is_candidate_reference"] = 1
        rows[idx]["is_reference_segment"] = 1
    for idx in range(final_start, final_end + 1):
        rows[idx]["is_final_measurement_window"] = 1


def rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) == 0:
        return values
    window = max(1, min(window, len(values)))
    kernel = np.ones(window, dtype=float) / float(window)
    padded = np.pad(values, (window // 2, window - 1 - window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def plot_results(
    rows: list[dict[str, object]],
    segment_summaries: list[dict[str, object]],
    reference_summary: dict[str, object],
    final_idx: int,
    output_path: Path,
    rolling_window: int,
) -> None:
    time_axis = np.array([float(row["epoch_time"]) - float(rows[0]["epoch_time"]) for row in rows], dtype=float)
    fx = np.array([float(row["Fx"]) for row in rows], dtype=float)
    fy = np.array([float(row["Fy"]) for row in rows], dtype=float)
    fz = np.array([float(row["Fz"]) for row in rows], dtype=float)
    base_z = np.array([float(row["force_base_z"]) if is_finite_number(row["force_base_z"]) else math.nan for row in rows], dtype=float)
    final_summary = segment_summaries[final_idx]
    ref_start = float(reference_summary["start_epoch_time"]) - float(rows[0]["epoch_time"])
    ref_end = float(reference_summary["end_epoch_time"]) - float(rows[0]["epoch_time"])
    final_start = float(final_summary["start_epoch_time"]) - float(rows[0]["epoch_time"])
    final_end = float(final_summary["end_epoch_time"]) - float(rows[0]["epoch_time"])

    fig, axes = plt.subplots(3, 1, figsize=(12.0, 9.5), sharex=True)

    axes[0].plot(time_axis, fx, lw=1.0, label="Fx")
    axes[0].plot(time_axis, fy, lw=1.0, label="Fy")
    axes[0].plot(time_axis, fz, lw=1.0, label="Fz")
    axes[0].set_ylabel("Force (N)")
    axes[0].set_title("Raw FT300 force channels")
    axes[0].grid(alpha=0.25)
    axes[0].legend(loc="upper right", ncol=3)

    axes[1].plot(time_axis, base_z, lw=1.0, alpha=0.4, color="#3F6C8E", label="Base-frame Fz")
    valid_mask = np.isfinite(base_z)
    if valid_mask.any():
        axes[1].plot(
            time_axis[valid_mask],
            rolling_mean(base_z[valid_mask], rolling_window),
            lw=2.0,
            color="#D4835B",
            label=f"Base-frame Fz rolling mean ({rolling_window})",
        )
    axes[1].axvspan(ref_start, ref_end, color="#C9E7C2", alpha=0.25, label="Reference")
    axes[1].axvspan(final_start, final_end, color="#F2C5B8", alpha=0.25, label="Final")
    axes[1].set_ylabel("Base-frame Fz (N)")
    axes[1].set_title("Projected gravity-axis force")
    axes[1].grid(alpha=0.25)
    axes[1].legend(loc="upper right")

    plot_summaries = list(segment_summaries)
    if reference_summary.get("segment_type") == "window_reference":
        plot_summaries = [reference_summary] + plot_summaries
    labels = [str(summary["segment_label"]) for summary in plot_summaries]
    base_z_values = [float(summary["avg_force_base_z"]) for summary in plot_summaries]
    mass_values = [float(summary["estimated_mass_g_from_base_z"]) for summary in plot_summaries]
    colors = []
    for summary in plot_summaries:
        if bool(summary["is_reference_segment"]):
            colors.append("#2E9E44")
        elif bool(summary["is_final_measurement_segment"]):
            colors.append("#A63D40")
        else:
            colors.append("#8FA6BF")
    bars = axes[2].bar(labels, base_z_values, color=colors, label="Avg base-frame Fz")
    axes[2].set_ylabel("Avg base-frame Fz (N)")
    axes[2].set_title("Reference vs final comparison")
    axes[2].grid(axis="y", alpha=0.25)
    twin = axes[2].twinx()
    twin.plot(labels, mass_values, color="#343434", marker="o", lw=1.5, label="Estimated mass")
    twin.set_ylabel("Estimated mass (g)")
    for bar, summary in zip(bars, plot_summaries):
        axes[2].text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{float(summary['avg_force_base_z']):.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    handles_left, labels_left = axes[2].get_legend_handles_labels()
    handles_right, labels_right = twin.get_legend_handles_labels()
    axes[2].legend(handles_left + handles_right, labels_left + labels_right, loc="upper left")
    axes[2].set_xlabel("Time since first valid FT sample (s)")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def summaries_for_csv(segment_summaries: list[dict[str, object]], reference_summary: dict[str, object]) -> list[dict[str, object]]:
    rows = list(segment_summaries)
    if reference_summary.get("segment_type") == "window_reference":
        rows = rows + [reference_summary]
    return rows


def write_outputs(
    rows: list[dict[str, object]],
    segment_summaries: list[dict[str, object]],
    reference_summary: dict[str, object],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timeseries_path = output_dir / "force_timeseries.csv"
    segments_path = output_dir / "stable_segments.csv"

    with timeseries_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_index",
                "source_row_index",
                "epoch_time",
                "Time",
                *JOINT_FIELDS,
                *POSE_FIELDS,
                "Fx",
                "Fy",
                "Fz",
                "Mx",
                "My",
                "Mz",
                "force_magnitude",
                "force_base_x",
                "force_base_y",
                "force_base_z",
                "ur_fresh",
                "ft_fresh",
                "is_candidate_reference",
                "is_reference_segment",
                "is_final_measurement_window",
            ]
        )
        for sample_index, row in enumerate(rows):
            writer.writerow(
                [
                    sample_index,
                    int(row["row_index"]),
                    float(row["epoch_time"]),
                    float(row["Time"]),
                    *[float(row[field]) for field in JOINT_FIELDS],
                    *[float(row[field]) for field in POSE_FIELDS],
                    float(row["Fx"]),
                    float(row["Fy"]),
                    float(row["Fz"]),
                    float(row["Mx"]),
                    float(row["My"]),
                    float(row["Mz"]),
                    float(row["force_magnitude"]),
                    float(row["force_base_x"]) if is_finite_number(row["force_base_x"]) else math.nan,
                    float(row["force_base_y"]) if is_finite_number(row["force_base_y"]) else math.nan,
                    float(row["force_base_z"]) if is_finite_number(row["force_base_z"]) else math.nan,
                    int(row["ur_fresh"]),
                    int(row["ft_fresh"]),
                    int(row["is_candidate_reference"]),
                    int(row["is_reference_segment"]),
                    int(row["is_final_measurement_window"]),
                ]
            )

    with segments_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "segment_id",
                "segment_label",
                "segment_type",
                "start_sample_index",
                "end_sample_index",
                "start_row_index",
                "end_row_index",
                "start_epoch_time",
                "end_epoch_time",
                "start_time",
                "end_time",
                "sample_count",
                "duration_s",
                "avg_fx",
                "avg_fy",
                "avg_fz",
                "avg_mx",
                "avg_my",
                "avg_mz",
                "avg_force_magnitude",
                "avg_force_base_x",
                "avg_force_base_y",
                "avg_force_base_z",
                "std_force_base_z",
                "pose_distance_to_final",
                "reference_score",
                "reference_rejected_reason",
                "is_reference_segment",
                "is_final_measurement_segment",
                "is_window_reference",
                "delta_force_base_z_to_reference",
                "delta_force_magnitude_to_reference",
                "estimated_mass_g_from_base_z",
            ]
        )
        for summary in summaries_for_csv(segment_summaries, reference_summary):
            writer.writerow(
                [
                    summary["segment_id"],
                    summary["segment_label"],
                    summary["segment_type"],
                    int(summary["start_sample_index"]),
                    int(summary["end_sample_index"]),
                    int(summary["start_row_index"]),
                    int(summary["end_row_index"]),
                    float(summary["start_epoch_time"]),
                    float(summary["end_epoch_time"]),
                    float(summary["start_time"]),
                    float(summary["end_time"]),
                    int(summary["sample_count"]),
                    float(summary["duration_s"]),
                    float(summary["avg_fx"]),
                    float(summary["avg_fy"]),
                    float(summary["avg_fz"]),
                    float(summary["avg_mx"]),
                    float(summary["avg_my"]),
                    float(summary["avg_mz"]),
                    float(summary["avg_force_magnitude"]),
                    float(summary["avg_force_base_x"]) if is_finite_number(summary["avg_force_base_x"]) else math.nan,
                    float(summary["avg_force_base_y"]) if is_finite_number(summary["avg_force_base_y"]) else math.nan,
                    float(summary["avg_force_base_z"]) if is_finite_number(summary["avg_force_base_z"]) else math.nan,
                    float(summary["std_force_base_z"]) if is_finite_number(summary["std_force_base_z"]) else math.nan,
                    float(summary["pose_distance_to_final"]) if is_finite_number(summary["pose_distance_to_final"]) else math.nan,
                    float(summary["reference_score"]) if is_finite_number(summary["reference_score"]) else math.nan,
                    str(summary["reference_rejected_reason"]),
                    int(bool(summary["is_reference_segment"])),
                    int(bool(summary["is_final_measurement_segment"])),
                    int(bool(summary["is_window_reference"])),
                    float(summary["delta_force_base_z_to_reference"]) if is_finite_number(summary["delta_force_base_z_to_reference"]) else math.nan,
                    float(summary["delta_force_magnitude_to_reference"]) if is_finite_number(summary["delta_force_magnitude_to_reference"]) else math.nan,
                    float(summary["estimated_mass_g_from_base_z"]) if is_finite_number(summary["estimated_mass_g_from_base_z"]) else math.nan,
                ]
            )

    return timeseries_path, segments_path


def print_summary(
    session_dir: Path,
    output_dir: Path,
    reference_summary: dict[str, object],
    final_summary: dict[str, object],
    weight_axis_mode: str,
    reference_type: str,
    risk_level: str,
) -> None:
    warning = " WARNING" if risk_level == "high" else ""
    print(f"Session directory: {session_dir}")
    print(f"Output directory: {output_dir}")
    print(
        "Reference segment (0 g): "
        f"{reference_summary['segment_label']} type={reference_type} "
        f"Time={float(reference_summary['start_time']):.3f}s -> {float(reference_summary['end_time']):.3f}s, "
        f"Avg base-frame Fz={float(reference_summary['avg_force_base_z']):.3f} N, "
        f"Avg |F|={float(reference_summary['avg_force_magnitude']):.3f} N, "
        f"PoseDist={float(reference_summary['pose_distance_to_final']):.3f}"
    )
    print(
        "Final measurement segment: "
        f"{final_summary['segment_label']} "
        f"Time={float(final_summary['start_time']):.3f}s -> {float(final_summary['end_time']):.3f}s, "
        f"Avg base-frame Fz={float(final_summary['avg_force_base_z']):.3f} N, "
        f"Avg |F|={float(final_summary['avg_force_magnitude']):.3f} N"
    )
    print(
        "Weight result: "
        f"delta_base_z={float(final_summary['delta_force_base_z_to_reference']):.3f} N, "
        f"delta_|F|={float(final_summary['delta_force_magnitude_to_reference']):.3f} N, "
        f"mass={float(final_summary['estimated_mass_g_from_base_z']):.2f} g "
        f"(mode={weight_axis_mode}, risk={risk_level}){warning}"
    )


def analyze_session(args: argparse.Namespace, print_console_summary: bool = True) -> dict[str, object]:
    session_dir = args.session_dir.resolve()
    csv_path = session_dir / CSV_NAME
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    if not args.model_file.exists():
        raise FileNotFoundError(f"Model file not found: {args.model_file}")

    output_dir = args.output_dir.resolve() if args.output_dir else (DEFAULT_OUTPUT_ROOT / session_dir.name)
    rotation_tcp_to_sensor = load_model_rotation(args.model_file.resolve(), args.tcp_frame_name, args.sensor_frame_name)
    rows = load_rows(csv_path)
    if not rows:
        raise RuntimeError("No valid FT300 samples found after filtering NaN force rows.")

    compute_force_features(rows, rotation_tcp_to_sensor)
    _, segments = detect_stable_segments(rows, args.joint_threshold, args.min_stable_samples)
    if len(segments) < 2:
        raise RuntimeError("Need at least two stable segments. Try lowering --min-stable-samples or adjusting --joint-threshold.")

    segment_summaries = summarize_segments(rows, segments)
    final_idx, reference_summary, reference_type, risk_level = select_reference_and_final(rows, segment_summaries, args)
    estimate_weight(segment_summaries, reference_summary, final_idx, args.weight_axis_mode)
    mark_reference_rows(rows, reference_summary, segment_summaries[final_idx])
    write_outputs(rows, segment_summaries, reference_summary, output_dir)
    plot_results(rows, segment_summaries, reference_summary, final_idx, output_dir / "force_analysis.png", args.rolling_window)

    final_summary = segment_summaries[final_idx]
    if print_console_summary:
        print_summary(
            session_dir,
            output_dir,
            reference_summary,
            final_summary,
            args.weight_axis_mode,
            reference_type,
            risk_level,
        )

    return {
        "session_dir": session_dir,
        "output_dir": output_dir,
        "segment_count": len(segment_summaries),
        "reference_segment_id": reference_summary["segment_label"],
        "reference_type": reference_type,
        "reference_start_time": float(reference_summary["start_time"]),
        "reference_end_time": float(reference_summary["end_time"]),
        "reference_force_base_z": float(reference_summary["avg_force_base_z"]),
        "reference_force_magnitude": float(reference_summary["avg_force_magnitude"]),
        "reference_pose_distance": float(reference_summary["pose_distance_to_final"]),
        "reference_score": float(reference_summary["reference_score"]) if is_finite_number(reference_summary["reference_score"]) else math.nan,
        "final_segment_id": final_summary["segment_label"],
        "final_start_time": float(final_summary["start_time"]),
        "final_end_time": float(final_summary["end_time"]),
        "final_force_base_z": float(final_summary["avg_force_base_z"]),
        "final_force_magnitude": float(final_summary["avg_force_magnitude"]),
        "delta_force_base_z": float(final_summary["delta_force_base_z_to_reference"]),
        "delta_force_magnitude": float(final_summary["delta_force_magnitude_to_reference"]),
        "estimated_mass_g": float(final_summary["estimated_mass_g_from_base_z"]),
        "weight_axis_mode": args.weight_axis_mode,
        "risk_level": risk_level,
        "stable_segments_csv": output_dir / "stable_segments.csv",
        "force_timeseries_csv": output_dir / "force_timeseries.csv",
        "force_analysis_png": output_dir / "force_analysis.png",
    }


def main() -> int:
    args = parse_args()
    analyze_session(args, print_console_summary=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
