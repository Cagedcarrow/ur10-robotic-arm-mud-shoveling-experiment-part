#!/usr/bin/env python3
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import pandas as pd


DATA_EXTEND_ROOT = Path(__file__).resolve().parents[1]
OPTIMUM_PATH = DATA_EXTEND_ROOT / "model_outputs" / "predicted_optimum.json"
OUTPUT_PATH = DATA_EXTEND_ROOT / "future_real_experiment_design.csv"


def build_future_design() -> pd.DataFrame:
    angle_levels = [30.0, 32.5, 35.0, 37.5, 40.0]
    depth_levels = [25.0, 30.0, 35.0]
    speed_levels = [0.4, 0.55, 0.7]
    center_point = (0.55, 30.0, 35.0)

    rows = []
    experiment_index = 1
    for speed_setting, penetration_depth, entry_angle in product(speed_levels, depth_levels, angle_levels):
        rows.append(
            {
                "experiment_id": f"FUTURE_{experiment_index:03d}",
                "speed_setting": speed_setting,
                "penetration_depth": penetration_depth,
                "entry_angle": entry_angle,
                "measured_scooped_mass": pd.NA,
                "measured_energy": pd.NA,
                "measured_torque_mean": pd.NA,
                "measured_torque_peak": pd.NA,
                "notes": "future_real_experiment_candidate",
            }
        )
        experiment_index += 1

    for repeat_idx in range(3):
        rows.append(
            {
                "experiment_id": f"FUTURE_{experiment_index:03d}",
                "speed_setting": center_point[0],
                "penetration_depth": center_point[1],
                "entry_angle": center_point[2],
                "measured_scooped_mass": pd.NA,
                "measured_energy": pd.NA,
                "measured_torque_mean": pd.NA,
                "measured_torque_peak": pd.NA,
                "notes": "center_point_repeat",
            }
        )
        experiment_index += 1

    return pd.DataFrame(rows)


def main() -> int:
    if OPTIMUM_PATH.exists():
        optimum = json.loads(OPTIMUM_PATH.read_text(encoding="utf-8"))
    else:
        optimum = None

    design_df = build_future_design()
    design_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    summary = {
        "future_real_experiment_design_count": int(len(design_df)),
        "center_point_repeat_count": int((design_df["notes"] == "center_point_repeat").sum()),
        "output_path": str(OUTPUT_PATH),
    }
    if optimum is not None:
        summary["predicted_optimum_reference"] = {
            "optimal_entry_angle": optimum["optimal_entry_angle"],
            "optimal_penetration_depth": optimum["optimal_penetration_depth"],
            "optimal_speed_setting": optimum["optimal_speed_setting"],
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
