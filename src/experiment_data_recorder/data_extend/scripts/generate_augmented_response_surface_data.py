#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_EXTEND_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
ANALYSIS_OUTPUT_ROOT = DATA_ROOT / "analysis" / "output"

REAL_DATA_PATH = DATA_EXTEND_ROOT / "real_experiment_clean.csv"
AUGMENTED_DATA_PATH = DATA_EXTEND_ROOT / "response_surface_augmented_100.csv"
COMBINED_DATA_PATH = DATA_EXTEND_ROOT / "combined_modeling_dataset.csv"
MODEL_OUTPUT_DIR = DATA_EXTEND_ROOT / "model_outputs"
RNG_SEED = 20260505

GROUP_SETTINGS = [
    (1, 20.0, 20.0),
    (2, 20.0, 20.0),
    (3, 30.0, 40.0),
    (4, 30.0, 40.0),
    (5, 40.0, 60.0),
    (6, 40.0, 60.0),
    (7, 40.0, 60.0),
    (8, 40.0, 60.0),
]

FIELD_ALIASES = {
    "group": ["group", "组别"],
    "speed_setting": ["speed", "velocity", "speed_setting", "机器臂速度", "速度"],
    "penetration_depth": ["depth", "penetration_depth", "shovel_depth", "铲子下潜深度", "下潜深度"],
    "entry_angle": ["angle", "entry_angle", "cutting_angle", "切入角度", "切入角"],
    "scooped_mass": ["mass", "scooped_mass", "weight", "mud_mass", "铲泥重量", "铲泥质量"],
}


@dataclass
class SessionSpeedFeatures:
    session_name: str
    qd_activity_mean: float
    tcp_linear_activity_mean: float
    tcp_angular_activity_mean: float


def ensure_dirs() -> None:
    DATA_EXTEND_ROOT.mkdir(parents=True, exist_ok=True)
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_header(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def scan_tabular_files(data_root: Path) -> list[Path]:
    return sorted(
        path
        for path in data_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xls"}
    )


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def scan_direct_design_tables(files: list[Path]) -> dict[str, object]:
    matched_files: list[str] = []
    matched_rows = 0
    for path in files:
        try:
            df = read_table(path)
        except Exception:
            continue
        normalized = {normalize_header(col): col for col in df.columns}
        matched: dict[str, str] = {}
        for canonical, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                if normalize_header(alias) in normalized:
                    matched[canonical] = normalized[normalize_header(alias)]
                    break
        if {"penetration_depth", "entry_angle", "scooped_mass"} <= matched.keys():
            matched_files.append(str(path.relative_to(PROJECT_ROOT)))
            matched_rows += len(df)
    return {
        "tabular_files_scanned": len(files),
        "matched_direct_design_file_count": len(matched_files),
        "matched_direct_design_rows": matched_rows,
        "matched_files": matched_files,
    }


def find_session_dirs() -> list[Path]:
    return sorted(path for path in DATA_ROOT.iterdir() if path.is_dir() and (path / "ur10_ft300_realtime_data.csv").exists())


def compute_session_speed_features(session_dir: Path) -> SessionSpeedFeatures:
    df = pd.read_csv(session_dir / "ur10_ft300_realtime_data.csv")
    qd_cols = [f"Act_qd{i}" for i in range(6)]
    linear_cols = ["Act_dX", "Act_dY", "Act_dZ"]
    angular_cols = ["Act_dRX", "Act_dRY", "Act_dRZ"]

    qd_norm = np.linalg.norm(np.nan_to_num(df[qd_cols].to_numpy(dtype=float)), axis=1)
    tcp_linear = np.linalg.norm(np.nan_to_num(df[linear_cols].to_numpy(dtype=float)), axis=1)
    tcp_angular = np.linalg.norm(np.nan_to_num(df[angular_cols].to_numpy(dtype=float)), axis=1)

    qd_thr = np.percentile(qd_norm, 35)
    tcp_thr = np.percentile(tcp_linear, 35)
    active_mask = (qd_norm > qd_thr) | (tcp_linear > tcp_thr)
    if not np.any(active_mask):
        active_mask = np.ones_like(qd_norm, dtype=bool)

    return SessionSpeedFeatures(
        session_name=session_dir.name,
        qd_activity_mean=float(np.mean(qd_norm[active_mask])),
        tcp_linear_activity_mean=float(np.mean(tcp_linear[active_mask])),
        tcp_angular_activity_mean=float(np.mean(tcp_angular[active_mask])),
    )


def load_session_mass_map() -> dict[str, float]:
    mass_map: dict[str, float] = {}
    for stable_csv in sorted(ANALYSIS_OUTPUT_ROOT.glob("*/stable_segments.csv")):
        df = pd.read_csv(stable_csv)
        final_rows = df[df["is_final_measurement_segment"] == 1]
        if final_rows.empty:
            continue
        mass_map[stable_csv.parent.name] = float(final_rows.iloc[-1]["estimated_mass_g_from_base_z"])
    return mass_map


def minmax_to_range(values: np.ndarray, target_min: float, target_max: float) -> np.ndarray:
    if np.nanmax(values) - np.nanmin(values) < 1e-12:
        return np.full_like(values, (target_min + target_max) / 2.0, dtype=float)
    scaled = (values - np.nanmin(values)) / (np.nanmax(values) - np.nanmin(values))
    return target_min + (target_max - target_min) * scaled


def build_real_experiment_table() -> pd.DataFrame:
    session_dirs = find_session_dirs()
    if len(session_dirs) != len(GROUP_SETTINGS):
        raise RuntimeError(f"Expected {len(GROUP_SETTINGS)} sessions under {DATA_ROOT}, found {len(session_dirs)}.")

    mass_map = load_session_mass_map()
    missing_mass = [session_dir.name for session_dir in session_dirs if session_dir.name not in mass_map]
    if missing_mass:
        raise RuntimeError(f"Missing weight-analysis outputs for sessions: {missing_mass}")

    speed_features = [compute_session_speed_features(session_dir) for session_dir in session_dirs]
    qd_values = np.array([item.qd_activity_mean for item in speed_features], dtype=float)
    tcp_linear_values = np.array([item.tcp_linear_activity_mean for item in speed_features], dtype=float)
    qd_scaled = minmax_to_range(qd_values, 0.0, 1.0)
    tcp_scaled = minmax_to_range(tcp_linear_values, 0.0, 1.0)
    combined_proxy = 0.75 * qd_scaled + 0.25 * tcp_scaled
    speed_setting_values = minmax_to_range(combined_proxy, 0.2, 1.0)

    rows = []
    for idx, session_dir in enumerate(session_dirs):
        group_id, depth, angle = GROUP_SETTINGS[idx]
        features = speed_features[idx]
        rows.append(
            {
                "record_id": f"real_{idx + 1:03d}",
                "session_name": session_dir.name,
                "group": group_id,
                "speed_setting": round(float(speed_setting_values[idx]), 6),
                "penetration_depth": depth,
                "entry_angle": angle,
                "scooped_mass": round(float(mass_map[session_dir.name]), 6),
                "speed_setting_source": "derived_proxy_from_Act_qd_and_TCP_velocity",
                "speed_proxy_joint_activity": round(features.qd_activity_mean, 6),
                "speed_proxy_tcp_linear_activity": round(features.tcp_linear_activity_mean, 6),
                "speed_proxy_tcp_angular_activity": round(features.tcp_angular_activity_mean, 6),
                "data_role": "real_experiment",
                "source_description": "measured from original experiment",
                "is_measured": 1,
            }
        )
    return pd.DataFrame(rows)


def latin_hypercube(n: int, dims: int, rng: np.random.Generator) -> np.ndarray:
    sample = np.zeros((n, dims), dtype=float)
    for dim in range(dims):
        perm = rng.permutation(n)
        sample[:, dim] = (perm + rng.random(n)) / n
    return sample


def quadratic_mass_model(
    speed_setting: np.ndarray,
    penetration_depth: np.ndarray,
    entry_angle: np.ndarray,
    peak_mass: float,
    depth_opt: float,
    speed_opt: float = 0.55,
    angle_opt: float = 35.0,
) -> np.ndarray:
    return (
        peak_mass
        - 920.0 * (speed_setting - speed_opt) ** 2
        - 1.10 * (penetration_depth - depth_opt) ** 2
        - 0.26 * (entry_angle - angle_opt) ** 2
        + 11.5 * (speed_setting - speed_opt) * (penetration_depth - depth_opt)
        + 4.2 * (speed_setting - speed_opt) * (entry_angle - angle_opt)
        + 0.065 * (penetration_depth - depth_opt) * (entry_angle - angle_opt)
    )


def generate_augmented_dataset(real_df: pd.DataFrame, n_samples: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    depth_min = float(real_df["penetration_depth"].min())
    depth_max = float(real_df["penetration_depth"].max())
    angle_min = 20.0
    angle_max = 60.0
    speed_min = 0.2
    speed_max = 1.0
    depth_opt = 30.0
    peak_mass = max(380.0, float(real_df["scooped_mass"].max()) * 0.82)

    n_global = 60
    n_local = n_samples - n_global

    lhs = latin_hypercube(n_global, 3, rng)
    global_samples = np.column_stack(
        [
            speed_min + (speed_max - speed_min) * lhs[:, 0],
            depth_min + (depth_max - depth_min) * lhs[:, 1],
            angle_min + (angle_max - angle_min) * lhs[:, 2],
        ]
    )

    repeated_real = real_df.sample(n=n_local, replace=True, random_state=RNG_SEED).reset_index(drop=True)
    local_speed = np.clip(repeated_real["speed_setting"].to_numpy(dtype=float) + rng.normal(0.0, 0.08, n_local), speed_min, speed_max)
    local_depth = np.clip(repeated_real["penetration_depth"].to_numpy(dtype=float) + rng.normal(0.0, 2.2, n_local), depth_min, depth_max)
    local_angle = np.clip(repeated_real["entry_angle"].to_numpy(dtype=float) + rng.normal(0.0, 4.5, n_local), angle_min, angle_max)
    local_samples = np.column_stack([local_speed, local_depth, local_angle])

    samples = np.vstack([global_samples, local_samples])
    speed_setting = samples[:, 0]
    penetration_depth = samples[:, 1]
    entry_angle = samples[:, 2]

    deterministic_mass = quadratic_mass_model(speed_setting, penetration_depth, entry_angle, peak_mass=peak_mass, depth_opt=depth_opt)
    noise = rng.normal(0.0, max(14.0, peak_mass * 0.05), n_samples)
    scooped_mass = np.clip(deterministic_mass + noise, 0.0, None)

    rows = []
    for idx in range(n_samples):
        rows.append(
            {
                "record_id": f"aug_{idx + 1:03d}",
                "session_name": f"synthetic_session_{idx + 1:03d}",
                "group": np.nan,
                "speed_setting": round(float(speed_setting[idx]), 6),
                "penetration_depth": round(float(penetration_depth[idx]), 6),
                "entry_angle": round(float(entry_angle[idx]), 6),
                "scooped_mass": round(float(scooped_mass[idx]), 6),
                "speed_setting_source": "response_surface_augmented_design_variable",
                "speed_proxy_joint_activity": np.nan,
                "speed_proxy_tcp_linear_activity": np.nan,
                "speed_proxy_tcp_angular_activity": np.nan,
                "data_role": "response_surface_augmented",
                "source_description": "generated from quadratic response surface assumption",
                "is_measured": 0,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    if not DATA_ROOT.exists():
        raise RuntimeError(f"Missing data directory: {DATA_ROOT}")

    ensure_dirs()
    scan_info = scan_direct_design_tables(scan_tabular_files(DATA_ROOT))
    real_df = build_real_experiment_table()
    augmented_df = generate_augmented_dataset(real_df, n_samples=100)
    combined_df = pd.concat([real_df, augmented_df], ignore_index=True)

    real_df.to_csv(REAL_DATA_PATH, index=False, encoding="utf-8")
    augmented_df.to_csv(AUGMENTED_DATA_PATH, index=False, encoding="utf-8")
    combined_df.to_csv(COMBINED_DATA_PATH, index=False, encoding="utf-8")

    summary = {
        "real_experiment_count": int(len(real_df)),
        "response_surface_augmented_count": int(len(augmented_df)),
        "combined_modeling_count": int(len(combined_df)),
        "tabular_files_scanned": int(scan_info["tabular_files_scanned"]),
        "matched_direct_design_file_count": int(scan_info["matched_direct_design_file_count"]),
        "matched_direct_design_rows": int(scan_info["matched_direct_design_rows"]),
        "real_experiment_clean_path": str(REAL_DATA_PATH.relative_to(PROJECT_ROOT)),
        "response_surface_augmented_path": str(AUGMENTED_DATA_PATH.relative_to(PROJECT_ROOT)),
        "combined_modeling_dataset_path": str(COMBINED_DATA_PATH.relative_to(PROJECT_ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("说明：speed_setting 为由真实运动数据推导的代理变量；response_surface_augmented_100.csv 为响应面增强样本，不是直接实验测量数据。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
