#!/usr/bin/env python3
from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
from typing import List

def _normalize_positive(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().sum() == 0:
        return pd.Series([0.5] * len(s), index=s.index, dtype=float)
    s_filled = s.fillna(s.median())
    s_min = float(s_filled.min())
    s_max = float(s_filled.max())
    if np.isclose(s_max, s_min):
        return pd.Series([0.5] * len(s), index=s.index, dtype=float)
    return (s_filled - s_min) / (s_max - s_min)


def _normalize_negative(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().sum() == 0:
        return pd.Series([0.5] * len(s), index=s.index, dtype=float)
    s_filled = s.fillna(s.median())
    s_min = float(s_filled.min())
    s_max = float(s_filled.max())
    if np.isclose(s_max, s_min):
        return pd.Series([0.5] * len(s), index=s.index, dtype=float)
    return (s_max - s_filled) / (s_max - s_min)


def _save_compare_figures(df: pd.DataFrame, fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    labels = df["experiment_id"].fillna(df["experiment_dir"].map(lambda x: Path(str(x)).name)).astype(str)

    mass = pd.to_numeric(df["mass_g"], errors="coerce")
    fmax = pd.to_numeric(df["F_max"], errors="coerce")
    plt.figure(figsize=(6, 5))
    plt.scatter(mass, fmax)
    plt.title("mass vs F_max")
    plt.xlabel("mass_g")
    plt.ylabel("F_max")
    plt.grid(True, alpha=0.3)
    plt.savefig(fig_dir / "mass_vs_force.png", dpi=200, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.bar(labels, fmax)
    plt.xticks(rotation=30, ha="right")
    plt.title("F_max comparison")
    plt.ylabel("F_max")
    plt.grid(True, axis="y", alpha=0.3)
    plt.savefig(fig_dir / "fmax_bar.png", dpi=200, bbox_inches="tight")
    plt.close()

    energy = pd.to_numeric(df["E_force"], errors="coerce")
    plt.figure(figsize=(10, 4))
    plt.bar(labels, energy)
    plt.xticks(rotation=30, ha="right")
    plt.title("E_force comparison")
    plt.ylabel("E_force")
    plt.grid(True, axis="y", alpha=0.3)
    plt.savefig(fig_dir / "energy_bar.png", dpi=200, bbox_inches="tight")
    plt.close()

    score = pd.to_numeric(df["Q_score"], errors="coerce")
    plt.figure(figsize=(10, 4))
    plt.bar(labels, score)
    plt.xticks(rotation=30, ha="right")
    plt.title("Q_score comparison")
    plt.ylabel("Q_score")
    plt.grid(True, axis="y", alpha=0.3)
    plt.savefig(fig_dir / "score_bar.png", dpi=200, bbox_inches="tight")
    plt.close()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_root = root / "data"
    results_dir = root / "results"
    results_fig_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_fig_dir.mkdir(parents=True, exist_ok=True)
    error_file = results_dir / "processing_errors.txt"

    csv_list = sorted(data_root.glob("*/ur10_ft300_realtime_data.csv"))
    if not csv_list:
        msg = "未发现可处理的 ur10_ft300_realtime_data.csv，请完成实验采集后运行 batch_process_all.py。"
        print(msg)
        error_file.write_text(msg + "\n", encoding="utf-8")
        return 0

    global np, pd, plt, PROCESSED_METRIC_COLUMNS, process_experiment
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        from metrics_utils import PROCESSED_METRIC_COLUMNS, process_experiment
    except ImportError as exc:
        print(f"依赖导入失败: {exc}")
        print("请执行: pip install numpy pandas scipy matplotlib openpyxl")
        return 2

    ok_rows: List[dict] = []
    errors: List[str] = []

    for csv_path in csv_list:
        exp_dir = csv_path.parent
        try:
            artifact = process_experiment(experiment_dir=exp_dir, csv_path=csv_path)
            ok_rows.append(artifact.metrics)
            print(f"[OK] {exp_dir}")
        except Exception as exc:
            err = f"[{datetime.now().isoformat(timespec='seconds')}] {exp_dir}: {exc}"
            errors.append(err)
            tb = traceback.format_exc()
            errors.append(tb)
            print(f"[ERROR] {exp_dir}: {exc}")
            continue

    if errors:
        error_file.write_text("\n".join(errors) + "\n", encoding="utf-8")
    elif error_file.exists():
        error_file.write_text("无错误。\n", encoding="utf-8")

    if not ok_rows:
        msg = "未发现可处理的 ur10_ft300_realtime_data.csv，请完成实验采集后运行 batch_process_all.py。"
        print(msg)
        return 0

    df = pd.DataFrame(ok_rows)
    for col in PROCESSED_METRIC_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    df = df[PROCESSED_METRIC_COLUMNS]

    df["mass_score"] = _normalize_positive(df["mass_g"])
    df["F_score"] = _normalize_negative(df["F_max"])
    df["E_score"] = _normalize_negative(df["E_force"])
    df["S_score"] = _normalize_negative(df["smoothness_force"])
    df["I_score"] = _normalize_negative(df["I_mean"])
    df["Q_score"] = (
        0.35 * df["mass_score"]
        + 0.20 * df["F_score"]
        + 0.20 * df["E_score"]
        + 0.15 * df["S_score"]
        + 0.10 * df["I_score"]
    )
    df["rank"] = df["Q_score"].rank(ascending=False, method="min").astype(int)
    df = df.sort_values("rank", ascending=True).reset_index(drop=True)

    summary_csv = results_dir / "summary_metrics.csv"
    summary_xlsx = results_dir / "summary_metrics.xlsx"
    df.to_csv(summary_csv, index=False, encoding="utf-8")
    try:
        df.to_excel(summary_xlsx, index=False)
    except Exception as exc:
        errors.append(f"xlsx 写入失败: {exc}")
        error_file.write_text("\n".join(errors) + "\n", encoding="utf-8")

    _save_compare_figures(df, results_fig_dir)
    print(f"[OK] 汇总完成: {summary_csv}")
    print(f"[OK] 汇总完成: {summary_xlsx}")
    print(f"[OK] 对比图目录: {results_fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
