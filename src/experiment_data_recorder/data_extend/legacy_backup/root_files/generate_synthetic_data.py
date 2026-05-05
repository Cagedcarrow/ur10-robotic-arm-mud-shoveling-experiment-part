#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
ANALYSIS_OUTPUT_ROOT = DATA_ROOT / "analysis" / "output"
OUTPUT_ROOT = ROOT / "data_extend"
BASE_DATA_PATH = OUTPUT_ROOT / "base_data_clean.csv"
SYNTHETIC_DATA_PATH = OUTPUT_ROOT / "synthetic_shovel_data_100.csv"
COMBINED_DATA_PATH = OUTPUT_ROOT / "combined_data_with_flag.csv"
README_PATH = OUTPUT_ROOT / "README.md"
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
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


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


def find_direct_design_records(files: list[Path]) -> tuple[pd.DataFrame, list[str]]:
    records: list[pd.DataFrame] = []
    notes: list[str] = []
    for path in files:
        try:
            df = read_table(path)
        except Exception as exc:  # pragma: no cover - robust scanning
            notes.append(f"跳过 `{path}`：读取失败（{exc}）。")
            continue
        normalized = {normalize_header(col): col for col in df.columns}
        matched: dict[str, str] = {}
        for canonical, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                key = normalize_header(alias)
                if key in normalized:
                    matched[canonical] = normalized[key]
                    break
        if {"penetration_depth", "entry_angle", "scooped_mass"} <= matched.keys():
            subset = pd.DataFrame({field: df[col] for field, col in matched.items()})
            subset["source_file"] = str(path.relative_to(ROOT))
            records.append(subset)
            notes.append(f"在 `{path.relative_to(ROOT)}` 中识别到直接设计字段：{', '.join(sorted(matched))}。")
    if not records:
        notes.append("未在原始 data 目录中发现可直接作为 speed/depth/angle/mass 设计表的统一字段表。")
        return pd.DataFrame(), notes
    return pd.concat(records, ignore_index=True), notes


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


def minmax_to_range(values: np.ndarray, target_min: float = 0.2, target_max: float = 1.0) -> np.ndarray:
    if np.nanmax(values) - np.nanmin(values) < 1e-12:
        return np.full_like(values, (target_min + target_max) / 2.0)
    scaled = (values - np.nanmin(values)) / (np.nanmax(values) - np.nanmin(values))
    return target_min + (target_max - target_min) * scaled


def build_real_base_data() -> tuple[pd.DataFrame, list[str]]:
    notes: list[str] = []
    session_dirs = find_session_dirs()
    if len(session_dirs) != len(GROUP_SETTINGS):
        raise RuntimeError(f"Expected {len(GROUP_SETTINGS)} session folders, found {len(session_dirs)} under {DATA_ROOT}.")

    mass_map = load_session_mass_map()
    missing_mass = [session.name for session in session_dirs if session.name not in mass_map]
    if missing_mass:
        raise RuntimeError(f"Missing weight analysis outputs for sessions: {missing_mass}")

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
                "session_name": session_dir.name,
                "group": group_id,
                "penetration_depth": depth,
                "entry_angle": angle,
                "speed_setting": round(float(speed_setting_values[idx]), 6),
                "speed_setting_source": "derived_proxy_from_Act_qd_and_TCP_velocity",
                "speed_proxy_joint_activity": round(features.qd_activity_mean, 6),
                "speed_proxy_tcp_linear_activity": round(features.tcp_linear_activity_mean, 6),
                "speed_proxy_tcp_angular_activity": round(features.tcp_angular_activity_mean, 6),
                "scooped_mass": round(float(mass_map[session_dir.name]), 6),
                "data_source": "real_experiment",
                "is_synthetic": 0,
            }
        )
    notes.append("8 个真实实验会话已按时间顺序映射到用户给出的 8 组 depth/angle 逻辑设置。")
    notes.append("speed_setting 由关节速度活动强度与 TCP 线速度活动强度推算得到，并归一化到 0.2~1.0。")
    return pd.DataFrame(rows), notes


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
    base = (
        peak_mass
        - 920.0 * (speed_setting - speed_opt) ** 2
        - 1.10 * (penetration_depth - depth_opt) ** 2
        - 0.26 * (entry_angle - angle_opt) ** 2
        + 11.5 * (speed_setting - speed_opt) * (penetration_depth - depth_opt)
        + 4.2 * (speed_setting - speed_opt) * (entry_angle - angle_opt)
        + 0.065 * (penetration_depth - depth_opt) * (entry_angle - angle_opt)
    )
    return base


def generate_synthetic_dataset(base_df: pd.DataFrame, n_samples: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    depth_min = float(base_df["penetration_depth"].min())
    depth_max = float(base_df["penetration_depth"].max())
    angle_min = 20.0
    angle_max = 60.0
    speed_min = 0.2
    speed_max = 1.0
    depth_opt = float(np.clip(np.mean(base_df["penetration_depth"].unique()), 30.0, 35.0))
    peak_mass = max(380.0, float(base_df["scooped_mass"].max()) * 0.82)

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

    repeated_real = base_df.sample(n=n_local, replace=True, random_state=RNG_SEED).reset_index(drop=True)
    local_speed = np.clip(repeated_real["speed_setting"].to_numpy(dtype=float) + rng.normal(0.0, 0.08, n_local), speed_min, speed_max)
    local_depth = np.clip(repeated_real["penetration_depth"].to_numpy(dtype=float) + rng.normal(0.0, 2.2, n_local), depth_min, depth_max)
    local_angle = np.clip(repeated_real["entry_angle"].to_numpy(dtype=float) + rng.normal(0.0, 4.5, n_local), angle_min, angle_max)
    local_samples = np.column_stack([local_speed, local_depth, local_angle])

    all_samples = np.vstack([global_samples, local_samples])
    speed_setting = all_samples[:, 0]
    penetration_depth = all_samples[:, 1]
    entry_angle = all_samples[:, 2]
    deterministic_mass = quadratic_mass_model(speed_setting, penetration_depth, entry_angle, peak_mass=peak_mass, depth_opt=depth_opt)
    noise = rng.normal(0.0, max(14.0, peak_mass * 0.05), n_samples)
    scooped_mass = np.clip(deterministic_mass + noise, 0.0, None)

    synthetic_df = pd.DataFrame(
        {
            "session_name": [f"synthetic_{idx:03d}" for idx in range(1, n_samples + 1)],
            "group": np.nan,
            "penetration_depth": np.round(penetration_depth, 6),
            "entry_angle": np.round(entry_angle, 6),
            "speed_setting": np.round(speed_setting, 6),
            "speed_setting_source": "synthetic_design_variable",
            "speed_proxy_joint_activity": np.nan,
            "speed_proxy_tcp_linear_activity": np.nan,
            "speed_proxy_tcp_angular_activity": np.nan,
            "scooped_mass": np.round(scooped_mass, 6),
            "data_source": "synthetic",
            "is_synthetic": 1,
        }
    )
    return synthetic_df


def write_placeholder_readme(scan_notes: list[str], base_df: pd.DataFrame) -> None:
    lines = [
        "# data_extend",
        "",
        "该目录用于保存基于原始 `data/` 会话提炼得到的真实实验基础表、明确标记的 synthetic 扩展样本，以及后续响应面回归分析结果。",
        "",
        "## 当前数据状态",
        "",
        f"- 真实实验基础样本数：`{len(base_df)}`",
        "- synthetic 扩展样本将在运行 `generate_synthetic_data.py` 后写入。",
        "",
        "## 原始数据字段扫描说明",
        "",
    ]
    lines.extend([f"- {note}" for note in scan_notes])
    lines.extend(
        [
            "",
            "## 依赖",
            "",
            "```bash",
            "pip install pandas numpy matplotlib scikit-learn statsmodels openpyxl",
            "```",
            "",
            "最终 README 会在完成建模与寻优后由 `optimize_response_surface.py` 更新为完整版本。",
        ]
    )
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not DATA_ROOT.exists():
        raise RuntimeError(f"Missing data directory: {DATA_ROOT}")

    ensure_dirs()
    tabular_files = scan_tabular_files(DATA_ROOT)
    direct_df, scan_notes = find_direct_design_records(tabular_files)
    base_df, base_notes = build_real_base_data()
    scan_notes.extend(base_notes)
    if direct_df.empty:
        scan_notes.append("真实基础表由 8 个 session 级样本构成，scooped_mass 使用现有重量分析结果。")
    else:
        scan_notes.append(f"额外识别到 {len(direct_df)} 行直接设计字段记录，但当前主分析仍以 session 级 8 个真实样本为基础。")

    synthetic_df = generate_synthetic_dataset(base_df, n_samples=100)
    combined_df = pd.concat([base_df, synthetic_df], ignore_index=True)

    base_df.to_csv(BASE_DATA_PATH, index=False, encoding="utf-8")
    synthetic_df.to_csv(SYNTHETIC_DATA_PATH, index=False, encoding="utf-8")
    combined_df.to_csv(COMBINED_DATA_PATH, index=False, encoding="utf-8")
    write_placeholder_readme(scan_notes, base_df)

    summary = {
        "real_experiment_count": int(len(base_df)),
        "synthetic_count": int(len(synthetic_df)),
        "tabular_files_scanned": int(len(tabular_files)),
        "base_data_clean_path": str(BASE_DATA_PATH.relative_to(ROOT)),
        "synthetic_data_path": str(SYNTHETIC_DATA_PATH.relative_to(ROOT)),
        "combined_data_path": str(COMBINED_DATA_PATH.relative_to(ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        "说明：speed_setting 为由真实运动数据推算的代理变量；synthetic_shovel_data_100.csv 为合成扩展数据，不能视为真实实验。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
